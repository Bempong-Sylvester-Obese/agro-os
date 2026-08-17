"""Loan workflow service — extracted from route-level logic."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import Loan, LoanStatus, User


def approve_loan(loan_id: int, approver: User, db: Session) -> Loan:
    loan = (
        db.query(Loan)
        .filter(Loan.id == loan_id)
        .with_for_update()
        .first()
    )
    if not loan:
        raise ValueError("Loan not found")
    if loan.status in (
        LoanStatus.approved,
        LoanStatus.disbursed,
        LoanStatus.repaid,
        LoanStatus.rejected,
        LoanStatus.cancelled,
    ):
        raise ValueError("Loan cannot be approved in its current state")
    loan.status = LoanStatus.approved
    loan.approved_by = str(approver.id) if approver else None
    loan.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan
