"""Farmer-originated loan request creation shared by phone channels."""

import math

from sqlalchemy.orm import Session

from app.models.models import CooperativeMembership, Loan, LoanStatus


class PendingLoanRequestError(ValueError):
    """Raised when a member already has a request awaiting a decision."""


class LoansNotInPlanError(PendingLoanRequestError):
    """Raised when the member's cooperative plan does not include AgroCredit.

    Subclasses ``PendingLoanRequestError`` so phone channels end the session
    with the message instead of prompting a retry.
    """


LOANS_NOT_IN_PLAN_MSG = (
    "Loans are not available for your cooperative's current plan. "
    "Ask your cooperative leader about upgrading."
)


def create_farmer_loan_request(
    *,
    membership: CooperativeMembership,
    amount: float,
    purpose: str,
    db: Session,
    request_channel: str = "ussd",
) -> Loan:
    """Create one pending request for the phone-resolved cooperative member."""
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Loan amount must be greater than zero.")

    normalized_purpose = purpose.strip()
    if not normalized_purpose:
        raise ValueError("Loan purpose is required.")
    if len(normalized_purpose) > 500:
        raise ValueError("Loan purpose must be 500 characters or fewer.")

    # Serialize requests for the same membership before checking for an
    # unresolved application. PostgreSQL honors this lock; SQLite safely
    # ignores it in local development.
    locked_membership = (
        db.query(CooperativeMembership)
        .filter(CooperativeMembership.id == membership.id)
        .with_for_update()
        .first()
    )
    if not locked_membership:
        raise ValueError("Cooperative membership is no longer active.")

    # AgroCredit is a Growth-tier feature (#233). Farmer channels resolve the
    # cooperative from the phone, so the entitlement is checked here rather
    # than by an HTTP dependency.
    from app.services import subscription_lifecycle as lifecycle
    from app.services.plans import has_feature

    cooperative = locked_membership.cooperative
    if cooperative is not None:
        lifecycle.reconcile_and_commit(db, cooperative)
        if not has_feature(lifecycle.effective_plan_key(cooperative), "loans"):
            raise LoansNotInPlanError(LOANS_NOT_IN_PLAN_MSG)

    existing = (
        db.query(Loan)
        .filter(
            Loan.farmer_id == membership.id,
            Loan.status == LoanStatus.requested,
        )
        .first()
    )
    if existing:
        raise PendingLoanRequestError(
            f"Loan request #{existing.id} is already awaiting review."
        )

    loan = Loan(
        farmer_id=membership.id,
        amount=amount,
        currency="GHS",
        purpose=normalized_purpose,
        status=LoanStatus.requested,
        request_channel=request_channel,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan
