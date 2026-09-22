"""Shared loan/ledger helpers used by the disbursement and repayment services."""
import uuid

from sqlalchemy.orm import Session

from app.models.models import (
    Cooperative,
    CooperativeMembership as Farmer,
    Loan,
    Transaction,
    TransactionType,
)


def disburse_external_ref(loan_id: int) -> str:
    """Return the provider-safe numeric reference for each payout attempt.

    Some providers coerce alphanumeric references to ``0``, which makes separate
    attempts indistinguishable in their ledger. Keep this to 12 numeric digits.
    """
    loan_prefix = str(loan_id % 100).zfill(2)
    random_suffix = str(uuid.uuid4().int % 10_000_000_000).zfill(10)
    return f"{loan_prefix}{random_suffix}"


def repay_external_ref(loan_id: int) -> str:
    return f"agro-loan-repay-{loan_id}-{uuid.uuid4().hex[:8]}"


def provider_amount_matches(expected: float, provider_amount) -> bool:
    if provider_amount is None or provider_amount == "":
        return False
    try:
        return abs(float(provider_amount) - float(expected)) < 0.01
    except (TypeError, ValueError):
        return False


def cooperative_account(farmer: Farmer, db: Session) -> str | None:
    """Return the cooperative's provider wallet when configured."""
    cooperative = db.query(Cooperative).filter(Cooperative.id == farmer.cooperative_id).first()
    return cooperative.wallet_account_id if cooperative else None


def loan_transaction_description(loan_id: int, transaction_type: TransactionType) -> str:
    kind = "disbursement" if transaction_type == TransactionType.payout else "repayment"
    return f"Loan {kind} #{loan_id}"


def latest_loan_transaction(
    db: Session,
    *,
    loan: Loan,
    transaction_type: TransactionType,
    lock: bool = False,
) -> Transaction | None:
    query = (
        db.query(Transaction)
        .filter(
            Transaction.farmer_id == loan.farmer_id,
            Transaction.transaction_type == transaction_type,
            Transaction.description == loan_transaction_description(loan.id, transaction_type),
        )
        .order_by(Transaction.created_at.desc())
    )
    if lock:
        query = query.with_for_update()
    return query.first()
