"""Finance Transaction Routes"""

import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.dependencies.cooperative_scope import resolve_cooperative_scope
from app.models.models import (
    AdminAuditLog,
    Cooperative,
    PaymentWebhookEvent,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.schemas.schemas import (
    DuesCollectRequest,
    DuesCollectResponse,
    PaymentLinkRequest,
    PaymentLinkResponse,
    PaymentWebhookEventResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionStatusUpdate,
)
from app.services.auth_service import (
    enforce_cooperative_scope,
    get_current_user,
    require_roles,
)
from app.services.communications_service import CommunicationsService
from app.services.moolre_service import MoolreService

router = APIRouter(prefix="/transactions", tags=["transactions"])
CUSTOMER_ACTION_TTL = timedelta(minutes=15)
INITIATING_ACTION_TTL = timedelta(minutes=2)
PROCESSING_ACTION_TTL = timedelta(minutes=2)
logger = logging.getLogger(__name__)


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

    if tx.status == TransactionStatus.completed:
        status = "completed"
    elif tx.status == TransactionStatus.failed:
        status = "failed"
    elif outcome == "verification_required":
        status = "verification_required"
    elif (
        outcome in ("initiating", "processing_otp", "push_sent")
        or result.get("success")
        or verification_required
    ):
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
        customer_action=tx.customer_action,
        action_expires_at=tx.action_expires_at,
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
    initiation_channel: str = "ussd",
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
            initiation_channel=initiation_channel,
            customer_action="initiating",
            action_expires_at=datetime.utcnow() + INITIATING_ACTION_TTL,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
    else:
        if tx.transaction_type != TransactionType.dues:
            raise HTTPException(status_code=409, detail="Payment reference type mismatch")
        if tx.status != TransactionStatus.pending:
            raise HTTPException(status_code=409, detail="Payment is no longer pending")
        if abs(float(tx.amount) - float(amount)) >= 0.01:
            raise HTTPException(status_code=409, detail="Payment amount mismatch")

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
        # A timeout may happen after Moolre accepted the request. Preserve the
        # reference for reconciliation instead of allowing a duplicate charge.
        raise

    db.expire_all()
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.moolre_reference == external_ref,
            Transaction.farmer_id == farmer.id,
        )
        .with_for_update()
        .one()
    )
    if tx.status in (TransactionStatus.completed, TransactionStatus.failed):
        return _dues_collect_response(
            tx,
            {
                "outcome": tx.status.value,
                "message": f"Payment already {tx.status.value}.",
            },
        )

    if result.get("moolre_reference") and result["moolre_reference"] != external_ref:
        ref_val = str(result["moolre_reference"]).lower()
        if ref_val not in ("all", "phoneno", "externalref", "senderid"):
            tx.moolre_reference = result["moolre_reference"]

    verification_required = result.get("verification_required", False) or result.get("outcome") == "verification_required"
    if verification_required:
        tx.customer_action = "otp"
        tx.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    elif result.get("success") or result.get("outcome") == "push_sent":
        tx.customer_action = "approval"
        tx.action_expires_at = datetime.utcnow() + CUSTOMER_ACTION_TTL
    else:
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None
    db.commit()

    result = {**result, "verification_required": verification_required}

    return _dues_collect_response(tx, result)


def expire_customer_actions(
    db: Session,
    *,
    farmer_id: int | None = None,
    cooperative_id: int | None = None,
) -> int:
    """Mark elapsed customer actions failed while retaining an expired label."""
    now = datetime.utcnow()
    query = db.query(Transaction).filter(
        Transaction.status == TransactionStatus.pending,
        Transaction.customer_action.in_(("otp", "approval")),
        Transaction.action_expires_at.is_not(None),
        Transaction.action_expires_at <= now,
    )
    if farmer_id is not None:
        query = query.filter(Transaction.farmer_id == farmer_id)
    if cooperative_id is not None:
        query = query.join(Farmer, Transaction.farmer_id == Farmer.id).filter(
            Farmer.cooperative_id == cooperative_id
        )
    expired = query.with_for_update().all()
    for tx in expired:
        tx.status = TransactionStatus.failed
        tx.customer_action = "expired"
    if expired:
        db.commit()
    return len(expired)


def pending_customer_actions(
    *,
    farmer: Farmer,
    db: Session,
) -> list[Transaction]:
    """Return unexpired payment actions owned by a phone-resolved membership."""
    expire_customer_actions(db, farmer_id=farmer.id)
    return (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == farmer.id,
            Transaction.status == TransactionStatus.pending,
            Transaction.customer_action.in_(("otp", "processing_otp", "approval")),
            Transaction.action_expires_at > datetime.utcnow(),
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )


async def resume_dues_customer_action(
    *,
    transaction: Transaction,
    farmer: Farmer,
    otp_code: str,
    db: Session,
) -> DuesCollectResponse:
    """Resume an OTP-gated dues request from the payer's phone channel."""
    now = datetime.utcnow()
    claimed = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction.id,
            Transaction.farmer_id == farmer.id,
            Transaction.transaction_type == TransactionType.dues,
            Transaction.status == TransactionStatus.pending,
            Transaction.customer_action == "otp",
            Transaction.action_expires_at > now,
        )
        .update(
            {
                Transaction.customer_action: "processing_otp",
                Transaction.action_expires_at: now + PROCESSING_ACTION_TTL,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if claimed != 1:
        raise HTTPException(
            status_code=409,
            detail="Payment verification is already processing or unavailable",
        )
    transaction = (
        db.query(Transaction).filter(Transaction.id == transaction.id).one()
    )
    return await _run_dues_collect(
        farmer=farmer,
        amount=transaction.amount,
        channel=transaction.channel or "13",
        description=transaction.description,
        external_ref=transaction.moolre_reference,
        otp_code=otp_code,
        db=db,
        initiation_channel=transaction.initiation_channel,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Create a manual transaction record."""
    farmer = db.query(Farmer).filter(Farmer.id == transaction_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)

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
    expire_customer_actions(db, cooperative_id=scoped_coop_id)
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
    query = db.query(PaymentWebhookEvent)
    if current_user is not None:
        query = (
            query.join(Transaction, PaymentWebhookEvent.transaction_id == Transaction.id)
            .join(Farmer, Transaction.farmer_id == Farmer.id)
            .filter(Farmer.cooperative_id == current_user.cooperative_id)
        )
    return (
        query
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
        enforce_cooperative_scope(current_user, farmer.cooperative_id)

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
    farmer = db.query(Farmer).filter(Farmer.id == tx.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Transaction not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    return tx


@router.get("/{transaction_id}/receipt")
def get_transaction_receipt(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx or not tx.farmer:
        raise HTTPException(status_code=404, detail="Transaction not found")
    enforce_cooperative_scope(current_user, tx.farmer.cooperative_id)
    webhook_events = (
        db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.transaction_id == tx.id)
        .order_by(PaymentWebhookEvent.received_at)
        .all()
    )
    return {
        "receipt_number": f"AGO-TX-{tx.id:08d}",
        "transaction": TransactionResponse.model_validate(tx),
        "provider_events": [
            {
                "event_type": event.event_type,
                "signature_valid": event.signature_valid,
                "processed": event.processed,
                "message": event.message,
                "received_at": event.received_at,
            }
            for event in webhook_events
        ],
    }


@router.post("/{transaction_id}/reconcile")
async def reconcile_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx or not tx.farmer:
        raise HTTPException(status_code=404, detail="Transaction not found")
    enforce_cooperative_scope(current_user, tx.farmer.cooperative_id)
    if not tx.moolre_reference and not tx.moolre_transfer_ref:
        raise HTTPException(status_code=409, detail="Transaction has no provider reference")

    cooperative_id = tx.farmer.cooperative_id
    transaction_type = tx.transaction_type
    moolre_reference = tx.moolre_reference
    moolre_transfer_ref = tx.moolre_transfer_ref
    cooperative = db.query(Cooperative).filter(
        Cooperative.id == cooperative_id
    ).first()
    moolre = MoolreService()
    if transaction_type == TransactionType.payout and moolre_transfer_ref:
        result = await moolre.transfer_status(
            reference=moolre_transfer_ref,
            account_number=moolre.resolve_account_number(None),
            id_type="2",
        )
    else:
        result = await moolre.payment_status(
            external_ref=moolre_reference,
            account_number=moolre.resolve_account_number(
                cooperative.moolre_account_number if cooperative else None
            ),
        )
    provider_status = result.get("status", "pending")
    db.expire_all()
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .with_for_update()
        .one()
    )
    previous_status = tx.status
    if tx.status == TransactionStatus.completed:
        pass
    elif provider_status == "completed":
        tx.status = TransactionStatus.completed
    elif tx.status == TransactionStatus.pending and provider_status == "failed":
        tx.status = TransactionStatus.failed
    if tx.status in (TransactionStatus.completed, TransactionStatus.failed):
        tx.customer_action = "none"
        tx.action_expires_at = None
    if current_user:
        db.add(
            AdminAuditLog(
                cooperative_id=cooperative_id,
                actor_id=str(current_user.id),
                action="payment.reconciled",
                resource_type="transaction",
                resource_id=str(tx.id),
                details=(
                    f"provider_status={provider_status};"
                    f"previous_status={previous_status.value};"
                    f"applied_status={tx.status.value}"
                ),
            )
        )
    db.commit()
    db.refresh(tx)
    return {
        "transaction": TransactionResponse.model_validate(tx),
        "provider_status": provider_status,
        "reference": tx.moolre_transfer_ref or tx.moolre_reference,
    }


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_transaction_status(
    transaction_id: int,
    update: TransactionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
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
    farmer = db.query(Farmer).filter(Farmer.id == tx.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Transaction not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)
    tx.status = update.status
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# Dues collection via Moolre USSD push
# ---------------------------------------------------------------------------


@router.post("/dues/collect", response_model=DuesCollectResponse)
async def collect_dues(
    request: DuesCollectRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """
    Send one dues request to the member's phone.

    Staff never submit the member's OTP. If Moolre requires verification, the
    member resumes this transaction from their own USSD session.
    """
    expire_customer_actions(db, farmer_id=request.farmer_id)
    farmer = (
        db.query(Farmer)
        .filter(Farmer.id == request.farmer_id)
        .with_for_update()
        .first()
    )
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)

    existing = (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == farmer.id,
            Transaction.transaction_type == TransactionType.dues,
            Transaction.status == TransactionStatus.pending,
            Transaction.initiation_channel == "dashboard",
            Transaction.customer_action.in_(
                ("none", "initiating", "otp", "processing_otp", "approval")
            ),
        )
        .order_by(Transaction.created_at.desc())
        .first()
    )
    if existing:
        if abs(float(existing.amount) - float(request.amount)) >= 0.01:
            raise HTTPException(
                status_code=409,
                detail="This member already has a pending dues request.",
            )
        if existing.customer_action == "none":
            # Retire transactions created by the pre-initiating-state version.
            existing.status = TransactionStatus.failed
            db.commit()
            existing = None
        elif existing.customer_action in ("initiating", "processing_otp"):
            if (
                existing.action_expires_at
                and existing.action_expires_at <= datetime.utcnow()
            ):
                try:
                    provider = await MoolreService().payment_status(
                        external_ref=existing.moolre_reference,
                        account_number=_cooperative_account(farmer, db),
                    )
                except Exception as exc:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "The existing payment request could not be reconciled. "
                            "Try again shortly."
                        ),
                    ) from exc
                db.expire_all()
                existing = (
                    db.query(Transaction)
                    .filter(Transaction.id == existing.id)
                    .with_for_update()
                    .one()
                )
                provider_status = provider.get("status", "pending")
                if provider_status == "completed":
                    existing.status = TransactionStatus.completed
                    existing.customer_action = "none"
                    existing.action_expires_at = None
                elif provider_status == "failed":
                    existing.status = TransactionStatus.failed
                    existing.customer_action = "none"
                    existing.action_expires_at = None
                    existing = None
                else:
                    existing.action_expires_at = (
                        datetime.utcnow() + INITIATING_ACTION_TTL
                    )
                db.commit()
            if existing is not None:
                return _dues_collect_response(
                    existing,
                    {
                        "outcome": (
                            "completed"
                            if existing.status == TransactionStatus.completed
                            else existing.customer_action
                        ),
                        "message": (
                            "Payment completed."
                            if existing.status == TransactionStatus.completed
                            else "The existing payment request is still being reconciled."
                        ),
                    },
                )
        if existing is not None:
            outcome = (
                "verification_required"
                if existing.customer_action == "otp"
                else (
                    "processing_otp"
                    if existing.customer_action == "processing_otp"
                    else "push_sent"
                )
            )
            return _dues_collect_response(
                existing,
                {
                    "outcome": outcome,
                    "verification_required": existing.customer_action == "otp",
                    "message": "The existing payment request is still awaiting the member.",
                },
            )

    ext_ref = str(uuid.uuid4())
    result = await _run_dues_collect(
        farmer=farmer,
        amount=request.amount,
        channel=request.channel,
        description=request.description,
        external_ref=ext_ref,
        otp_code=None,
        db=db,
        initiation_channel="dashboard",
    )
    if result.customer_action == "otp":
        try:
            await CommunicationsService().send_payment_action_required(
                farmer=farmer,
                amount=request.amount,
                reference=result.moolre_reference or ext_ref,
                db=db,
                sent_by=str(current_user.id) if current_user else None,
            )
        except Exception as exc:
            # The pending action remains visible in USSD even if SMS delivery
            # fails; Moolre already sends the OTP to the payer phone.
            logger.warning(
                "Could not send payment-action SMS for transaction %s: %s",
                result.transaction_id,
                exc,
            )
    return result


@router.post("/payment-link", response_model=PaymentLinkResponse)
async def create_payment_link(
    request: PaymentLinkRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Generate a hosted Moolre payment page for a farmer."""
    farmer = db.query(Farmer).filter(Farmer.id == request.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    enforce_cooperative_scope(current_user, farmer.cooperative_id)

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
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
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
async def get_wallet_balance(
    current_user: User | None = Depends(require_roles("admin", "finance_officer")),
):
    """Check cooperative Moolre wallet balance."""
    moolre = MoolreService()
    return await moolre.account_status()
