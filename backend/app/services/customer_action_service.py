"""Customer action domain service — extracted from routes/transactions.py."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    CooperativeMembership as Farmer,
    Farmer as LegacyFarmer,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.schemas.schemas import DuesCollectResponse

CUSTOMER_ACTION_TTL = timedelta(minutes=15)
INITIATING_ACTION_TTL = timedelta(minutes=2)
PROCESSING_ACTION_TTL = timedelta(minutes=2)


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
