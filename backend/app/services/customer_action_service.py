"""Customer action domain service — extracted from routes/transactions.py."""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    Cooperative,
    CooperativeMembership as Farmer,
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas.schemas import DuesCollectResponse
from app.services.providers.factory import get_payment_provider

CUSTOMER_ACTION_TTL = timedelta(minutes=15)
INITIATING_ACTION_TTL = timedelta(minutes=2)
PROCESSING_ACTION_TTL = timedelta(minutes=2)
logger = logging.getLogger(__name__)


async def reconcile_stale_customer_actions(
    db: Session,
    *,
    farmer_id: int | None = None,
    cooperative_id: int | None = None,
) -> dict[int, str]:
    """Reconcile expired ambiguous payment actions with the provider.

    Webhooks remain the primary completion path. This recovery path only
    transitions a payment from provider-confirmed terminal status. Pending
    provider results retain the action and extend its short retry window;
    provider failures leave local state unchanged.
    """
    now = datetime.utcnow()
    query = (
        db.query(
            Transaction.id,
            Transaction.moolre_reference,
            Transaction.customer_action,
            Transaction.amount,
            Farmer.cooperative_id,
            Cooperative.moolre_account_number,
        )
        .join(Farmer, Transaction.farmer_id == Farmer.id)
        .join(Cooperative, Farmer.cooperative_id == Cooperative.id)
        .filter(
            Transaction.status == TransactionStatus.pending,
            Transaction.customer_action.in_(("initiating", "processing_otp")),
            Transaction.action_expires_at.is_not(None),
            Transaction.action_expires_at <= now,
        )
    )
    if farmer_id is not None:
        query = query.filter(Transaction.farmer_id == farmer_id)
    if cooperative_id is not None:
        query = query.filter(Farmer.cooperative_id == cooperative_id)

    stale_actions = query.order_by(Transaction.id).all()
    if not stale_actions:
        return {}

    provider = get_payment_provider()
    outcomes: dict[int, str] = {}
    for action in stale_actions:
        if not action.moolre_reference:
            logger.warning(
                "Cannot reconcile stale transaction %s without a provider reference",
                action.id,
            )
            outcomes[action.id] = "error"
            continue
        try:
            result = await provider.payment_status(
                external_ref=action.moolre_reference,
                account_number=provider.resolve_account_number(
                    action.moolre_account_number
                ),
            )
        except Exception:
            logger.exception(
                "Provider status lookup failed for stale transaction %s",
                action.id,
            )
            outcomes[action.id] = "error"
            continue

        provider_status = result.get("status", "pending")
        provider_amount = result.get("amount")
        if (
            provider_status == "completed"
            and provider_amount is not None
            and abs(float(provider_amount) - float(action.amount)) >= 0.01
        ):
            logger.error(
                "Provider amount mismatch for stale transaction %s: "
                "expected=%s received=%s",
                action.id,
                action.amount,
                provider_amount,
            )
            outcomes[action.id] = "error"
            continue

        db.expire_all()
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == action.id)
            .with_for_update()
            .one()
        )
        if (
            transaction.status != TransactionStatus.pending
            or transaction.customer_action
            not in ("initiating", "processing_otp")
        ):
            outcomes[action.id] = transaction.status.value
            continue

        if provider_status == "completed":
            transaction.status = TransactionStatus.completed
            transaction.customer_action = "none"
            transaction.action_expires_at = None
            if (
                transaction.transaction_type == TransactionType.repayment
                and transaction.loan_id
            ):
                loan = (
                    db.query(Loan)
                    .filter(Loan.id == transaction.loan_id)
                    .with_for_update()
                    .first()
                )
                if loan and loan.status == LoanStatus.disbursed:
                    loan.status = LoanStatus.repaid
                    loan.repaid_at = datetime.utcnow()
        elif provider_status == "failed":
            transaction.status = TransactionStatus.failed
            transaction.customer_action = "none"
            transaction.action_expires_at = None
        else:
            retry_ttl = (
                PROCESSING_ACTION_TTL
                if transaction.customer_action == "processing_otp"
                else INITIATING_ACTION_TTL
            )
            transaction.action_expires_at = datetime.utcnow() + retry_ttl
            provider_status = "pending"

        db.commit()
        outcomes[action.id] = provider_status
    return outcomes


def expire_customer_actions(
    db: Session,
    *,
    farmer_id: int | None = None,
    cooperative_id: int | None = None,
    loan_id: int | None = None,
    transaction_type: TransactionType | None = None,
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
    if loan_id is not None:
        query = query.filter(Transaction.loan_id == loan_id)
    if transaction_type is not None:
        query = query.filter(Transaction.transaction_type == transaction_type)
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
            Transaction.customer_action.in_(
                ("initiating", "otp", "processing_otp", "approval")
            ),
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
    from fastapi import HTTPException
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
    from app.services.dues_service import run_dues_collect
    return await run_dues_collect(
        farmer=farmer,
        amount=transaction.amount,
        channel=transaction.channel or "13",
        description=transaction.description,
        external_ref=transaction.moolre_reference,
        otp_code=otp_code,
        db=db,
        initiation_channel=transaction.initiation_channel,
    )
