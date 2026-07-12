"""Finance Transaction Routes"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import Cooperative, Farmer, PaymentWebhookEvent, Transaction, TransactionStatus, TransactionType, User
from app.services.auth_service import get_current_user
from app.schemas.schemas import (
    DuesCollectRequest,
    DuesCollectResponse,
    DuesCollectVerifyRequest,
    PaymentLinkRequest,
    PaymentLinkResponse,
    PaymentWebhookEventResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionStatusUpdate,
)
from app.services.moolre_service import MoolreService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _cooperative_account(farmer: Farmer, db: Session) -> str | None:
    cooperative = db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    return cooperative.moolre_account_number if cooperative else None


def _dues_collect_response(tx: Transaction, result: dict) -> DuesCollectResponse:
    verification_required = result.get("verification_required", False)
    outcome = result.get("outcome")
    if outcome is None:
        if verification_required:
            outcome = "verification_required"
        elif result.get("success"):
            outcome = "push_sent"
        else:
            outcome = "failed"

    if outcome == "verification_required":
        status = "verification_required"
    elif outcome == "push_sent" or result.get("success") or verification_required:
        status = "pending"
    else:
        status = "failed"

    return DuesCollectResponse(
        transaction_id=tx.id,
        moolre_reference=tx.moolre_reference,
        status=status,
        message=result.get("message")
        or ("Payment request sent" if result.get("success") else "Moolre request failed"),
        verification_required=verification_required,
        outcome=outcome,
        moolre_code=result.get("moolre_code"),
    )


async def _run_dues_collect(
    *,
    farmer: Farmer,
    amount: float,
    channel: str,
    description: str | None,
    external_ref: str,
    otp_code: str | None,
    db: Session,
) -> DuesCollectResponse:
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.moolre_reference == external_ref,
            Transaction.farmer_id == farmer.id,
        )
        .first()
    )
    if not tx:
        tx = Transaction(
            farmer_id=farmer.id,
            transaction_type=TransactionType.dues,
            amount=amount,
            currency="GHS",
            status=TransactionStatus.pending,
            moolre_reference=external_ref,
            payer_phone=farmer.phone,
            channel=channel,
            description=description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

    moolre = MoolreService()
    coop_account = _cooperative_account(farmer, db)
    try:
        result = await moolre.initiate_payment(
            payer_phone=farmer.phone,
            amount=amount,
            currency="GHS",
            channel=channel,
            external_ref=external_ref,
            otpcode=otp_code,
            reference=description or "Cooperative dues",
            account_number=coop_account,
        )
    except Exception:
        tx.status = TransactionStatus.failed
        db.commit()
        raise

    if result.get("moolre_reference") and result["moolre_reference"] != external_ref:
        ref_val = str(result["moolre_reference"]).lower()
        if ref_val not in ("all", "phoneno", "externalref", "senderid"):
            tx.moolre_reference = result["moolre_reference"]
            db.commit()

    if not result.get("success") and not result.get("verification_required") and result.get("outcome") != "verification_required":
        tx.status = TransactionStatus.failed
        db.commit()

    verification_required = result.get("verification_required", False) or result.get("outcome") == "verification_required"
    result = {**result, "verification_required": verification_required}

    return _dues_collect_response(tx, result)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(transaction_in: TransactionCreate, db: Session = Depends(get_db)):
    """Create a manual transaction record."""
    farmer = db.query(Farmer).filter(Farmer.id == transaction_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    tx = Transaction(**transaction_in.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    farmer_id: int | None = None,
    status: TransactionStatus | None = None,
    transaction_type: TransactionType | None = None,
    cooperative_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List transactions with optional filters."""
    settings = get_settings()
    scoped_coop_id = resolve_cooperative_scope(
        current_user=current_user,
        cooperative_id=cooperative_id,
        settings=settings,
    )
    query = db.query(Transaction).join(Farmer, Transaction.farmer_id == Farmer.id).filter(
        Farmer.cooperative_id == scoped_coop_id
    )
    if farmer_id is not None:
        query = query.filter(Transaction.farmer_id == farmer_id)
    if status is not None:
        query = query.filter(Transaction.status == status)
    if transaction_type is not None:
        query = query.filter(Transaction.transaction_type == transaction_type)
    return query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/webhook-events", response_model=list[PaymentWebhookEventResponse])
def list_webhook_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Audit log of incoming Moolre payment webhooks."""
    settings = get_settings()
    if settings.auth_enabled:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
    else:
        raise HTTPException(status_code=404, detail="Not found")
    return (
        db.query(PaymentWebhookEvent)
        .order_by(PaymentWebhookEvent.received_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/farmer/{farmer_id}", response_model=list[TransactionResponse])
def get_farmer_transactions(
    farmer_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get all transactions for a specific farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    settings = get_settings()
    if settings.auth_enabled:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if current_user.cooperative_id and farmer.cooperative_id != current_user.cooperative_id:
            raise HTTPException(status_code=403, detail="Farmer not in your cooperative")

    return (
        db.query(Transaction)
        .filter(Transaction.farmer_id == farmer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get a transaction by ID."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_transaction_status(
    transaction_id: int,
    update: TransactionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Update non-payment transaction status (admin only; cannot force completed)."""
    settings = get_settings()
    if settings.auth_enabled and current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if settings.app_env.lower() in ("production", "prod"):
        raise HTTPException(status_code=404, detail="Not found")

    if update.status == TransactionStatus.completed:
        raise HTTPException(
            status_code=403,
            detail="Cannot mark completed manually — use Moolre webhook confirmation",
        )

    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.status = update.status
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# Dues collection via Moolre USSD push
# ---------------------------------------------------------------------------


@router.post("/dues/collect", response_model=DuesCollectResponse)
async def collect_dues(request: DuesCollectRequest, db: Session = Depends(get_db)):
    """
    Initiate cooperative dues collection via Moolre USSD payment push.
    Supports OTP verification retry if `external_ref` and `otp_code` are provided.
    Creates a pending Transaction record and fires the Moolre payment request.
    The webhook will later update the status to 'completed' or 'failed'.
    """
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = request.external_ref or str(uuid.uuid4())
    return await _run_dues_collect(
        farmer=farmer,
        amount=request.amount,
        channel=request.channel,
        description=request.description,
        external_ref=ext_ref,
        otp_code=request.otp_code,
        db=db,
    )


@router.post("/dues/collect/verify", response_model=DuesCollectResponse)
async def verify_dues_collect(request: DuesCollectVerifyRequest, db: Session = Depends(get_db)):
    """Retry a dues collection after OTP verification."""
    tx = db.query(Transaction).filter(Transaction.id == request.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.status != TransactionStatus.pending:
        raise HTTPException(status_code=409, detail="Transaction is not pending verification")

    farmer = db.query(Farmer).filter(Farmer.id == tx.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    return await _run_dues_collect(
        farmer=farmer,
        amount=tx.amount,
        channel=tx.channel or "13",
        description=tx.description,
        external_ref=tx.moolre_reference or str(uuid.uuid4()),
        otp_code=request.otp_code,
        db=db,
    )


@router.post("/payment-link", response_model=PaymentLinkResponse)
async def create_payment_link(request: PaymentLinkRequest, db: Session = Depends(get_db)):
    """Generate a hosted Moolre payment page for a farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = str(uuid.uuid4())
    tx = Transaction(
        farmer_id=farmer.id,
        transaction_type=TransactionType.dues,
        amount=request.amount,
        currency=request.currency,
        status=TransactionStatus.pending,
        moolre_reference=ext_ref,
        payer_phone=farmer.phone,
        description=request.description,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    moolre = MoolreService()
    try:
        result = await moolre.generate_payment_link(
            amount=request.amount,
            email=request.email,
            currency=request.currency,
            external_ref=ext_ref,
            metadata={"farmer_id": farmer.id, "transaction_id": tx.id},
        )
    except Exception:
        tx.status = TransactionStatus.failed
        db.commit()
        raise

    if not result.get("success"):
        tx.status = TransactionStatus.failed
        db.commit()

    return PaymentLinkResponse(
        success=result.get("success", False),
        payment_url=result.get("payment_url"),
        reference=result.get("reference", ext_ref),
        transaction_id=tx.id,
    )


# ---------------------------------------------------------------------------
# Moolre sync — list transactions from Moolre account
# ---------------------------------------------------------------------------


@router.get("/moolre/account-transactions")
async def list_moolre_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
):
    """
    Proxy to Moolre List Transactions API for the cooperative wallet.
    Returns raw Moolre transaction data for the finance dashboard.
    """
    moolre = MoolreService()
    return await moolre.list_transactions(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/moolre/wallet-balance")
async def get_wallet_balance():
    """Check cooperative Moolre wallet balance."""
    moolre = MoolreService()
    return await moolre.account_status()
