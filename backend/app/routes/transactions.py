"""Finance Transaction Routes"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import Farmer, PaymentWebhookEvent, Transaction, TransactionStatus, TransactionType
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
    skip: int = 0,
    limit: int = Query(default=100, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    """List transactions with optional filters."""
    query = db.query(Transaction)
    if farmer_id is not None:
        query = query.filter(Transaction.farmer_id == farmer_id)
    if status is not None:
        query = query.filter(Transaction.status == status)
    if transaction_type is not None:
        query = query.filter(Transaction.transaction_type == transaction_type)
    return query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/webhook-events", response_model=list[PaymentWebhookEventResponse])
def list_webhook_events(
    limit: int = Query(default=50, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    """Recent payment webhook audit events for finance reconciliation."""
    return (
        db.query(PaymentWebhookEvent)
        .order_by(PaymentWebhookEvent.received_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/farmer/{farmer_id}", response_model=list[TransactionResponse])
def get_farmer_transactions(farmer_id: int, db: Session = Depends(get_db)):
    """Get all transactions for a specific farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return (
        db.query(Transaction)
        .filter(Transaction.farmer_id == farmer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
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
):
    """Update the status of a transaction."""
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


def _dues_collect_response(tx: Transaction, result: dict) -> DuesCollectResponse:
    """Map a Moolre initiate_payment result to an API response."""
    outcome = result.get("outcome", "failed")
    if outcome == "verification_required":
        status = "verification_required"
        default_message = "SMS verification required. Submit OTP via /transactions/dues/collect/verify."
    elif outcome == "push_sent":
        status = "pending"
        default_message = "Payment request sent. Awaiting farmer approval on phone."
    else:
        status = "failed"
        default_message = "Moolre request failed"

    return DuesCollectResponse(
        transaction_id=tx.id,
        moolre_reference=tx.moolre_reference,
        status=status,
        message=result.get("message") or default_message,
        moolre_code=result.get("moolre_code"),
        outcome=outcome,
    )


@router.post("/dues/collect", response_model=DuesCollectResponse)
async def collect_dues(request: DuesCollectRequest, db: Session = Depends(get_db)):
    """
    Initiate cooperative dues collection via Moolre USSD payment push.
    Creates a pending Transaction record and fires the Moolre payment request.

    On first use of a sandbox payer phone, Moolre may return TP14 (SMS OTP required).
    Call POST /transactions/dues/collect/verify with the returned transaction_id and OTP.
    The webhook will later update the status to 'completed' or 'failed'.
    """
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = str(uuid.uuid4())

    tx = Transaction(
        farmer_id=farmer.id,
        transaction_type=TransactionType.dues,
        amount=request.amount,
        currency="GHS",
        status=TransactionStatus.pending,
        moolre_reference=ext_ref,
        payer_phone=farmer.phone,
        channel=request.channel,
        description=request.description,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    moolre = MoolreService()
    result = await moolre.initiate_payment(
        payer_phone=farmer.phone,
        amount=request.amount,
        currency="GHS",
        channel=request.channel,
        external_ref=ext_ref,
        reference=request.description or "Cooperative dues",
    )

    if result.get("moolre_reference") and result["moolre_reference"] != ext_ref:
        tx.moolre_reference = result["moolre_reference"]
        db.commit()

    return _dues_collect_response(tx, result)


@router.post("/dues/collect/verify", response_model=DuesCollectResponse)
async def verify_dues_collect(request: DuesCollectVerifyRequest, db: Session = Depends(get_db)):
    """
    Retry a dues payment push with the OTP sent to the payer by Moolre (TP14 flow).
    Reuses the same externalref from the original collect call.
    """
    tx = db.query(Transaction).filter(Transaction.id == request.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.transaction_type != TransactionType.dues:
        raise HTTPException(status_code=400, detail="Transaction is not a dues collection")
    if tx.status != TransactionStatus.pending:
        raise HTTPException(status_code=409, detail="Transaction is not pending OTP verification")
    if not tx.moolre_reference:
        raise HTTPException(status_code=400, detail="Transaction has no Moolre reference")
    if not tx.payer_phone:
        raise HTTPException(status_code=400, detail="Transaction has no payer phone")

    moolre = MoolreService()
    result = await moolre.initiate_payment(
        payer_phone=tx.payer_phone,
        amount=tx.amount,
        currency=tx.currency or "GHS",
        channel=tx.channel or "13",
        external_ref=tx.moolre_reference,
        reference=tx.description or "Cooperative dues",
        otp_code=request.otp_code,
    )

    if result.get("moolre_reference") and result["moolre_reference"] != tx.moolre_reference:
        tx.moolre_reference = result["moolre_reference"]
        db.commit()

    return _dues_collect_response(tx, result)


# ---------------------------------------------------------------------------
# Moolre sync — list transactions from Moolre account
# ---------------------------------------------------------------------------


@router.get("/moolre/account-transactions")
async def list_moolre_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=50, le=MAX_PAGE_SIZE),
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


@router.post("/payment-link", response_model=PaymentLinkResponse)
async def create_payment_link(request: PaymentLinkRequest, db: Session = Depends(get_db)):
    """Generate a hosted Moolre payment page for cooperative dues or loan repayment."""
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    ext_ref = str(uuid.uuid4())
    tx = Transaction(
        farmer_id=farmer.id,
        transaction_type=TransactionType.dues,
        amount=request.amount,
        currency="GHS",
        status=TransactionStatus.pending,
        moolre_reference=ext_ref,
        payer_phone=farmer.phone,
        channel="13",
        description=request.description or "Cooperative payment",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    moolre = MoolreService()
    result = await moolre.generate_payment_link(
        amount=request.amount,
        email=request.email,
        external_ref=ext_ref,
        callback_url=request.callback_url,
        redirect_url=request.redirect_url,
        metadata={"farmer_id": farmer.id, "transaction_id": tx.id},
    )

    if result.get("reference") and result["reference"] != ext_ref:
        tx.moolre_reference = result["reference"]
        db.commit()

    success = bool(result.get("success"))
    return PaymentLinkResponse(
        transaction_id=tx.id,
        moolre_reference=tx.moolre_reference or ext_ref,
        payment_url=result.get("payment_url"),
        success=success,
        message="Payment link generated" if success else "Moolre payment link request failed",
    )
