"""Payment domain service — processes normalized PaymentEvents."""
import logging
from datetime import datetime

from app.domain.payment_event import PaymentEvent
from app.models.models import (
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
)

logger = logging.getLogger(__name__)

_LEDGER_STATUS = {
    "success": TransactionStatus.completed,
    "failed": TransactionStatus.failed,
    "pending": TransactionStatus.pending,
}


def process_payment_event(event: PaymentEvent, db) -> dict:
    """Process a normalized payment event against the ledger.

    This is the domain entry point for all provider-agnostic payment
    processing. Webhook handlers normalize raw provider payloads into
    PaymentEvent objects and delegate here.
    """
    target_status = _LEDGER_STATUS.get(event.status)
    if target_status is None:
        return {"status": "ignored", "reason": f"Unhandled status: {event.status}"}

    tx = (
        db.query(Transaction)
        .filter(Transaction.provider_payment_ref == event.external_ref)
        .first()
    )
    if not tx:
        return {"status": "ignored", "reason": "No transaction for reference"}

    if tx.status == target_status or tx.status in (
        TransactionStatus.completed,
        TransactionStatus.failed,
    ):
        return {"status": "duplicate", "transaction_id": tx.id}

    if event.status == "success":
        tx.status = TransactionStatus.completed
        tx.customer_action = "none"
        tx.action_expires_at = None

        if tx.transaction_type == TransactionType.dues and tx.farmer_id:
            from app.services.trust_score_service import TrustScoreService
            try:
                TrustScoreService.recalculate_for_farmer(tx.farmer_id, db)
            except Exception as exc:
                logger.warning("Failed to recalculate trust score for farmer %s: %s", tx.farmer_id, exc)

        if tx.loan_id:
            loan = db.query(Loan).filter(Loan.id == tx.loan_id).first()
            if loan:
                if tx.transaction_type == TransactionType.payout:
                    loan.status = LoanStatus.disbursed
                    loan.disbursed_at = loan.disbursed_at or datetime.utcnow()
                elif tx.transaction_type == TransactionType.repayment:
                    loan.status = LoanStatus.repaid
                    loan.repaid_at = datetime.utcnow()

    elif event.status == "failed":
        tx.status = TransactionStatus.failed
        tx.customer_action = "none"
        tx.action_expires_at = None

    db.commit()
    return {"status": "processed", "transaction_id": tx.id, "new_status": tx.status.value}
