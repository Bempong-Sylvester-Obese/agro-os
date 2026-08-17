"""Unified USSD application service — shared menu logic for all USSD gateways."""

from sqlalchemy.orm import Session

USSD_MAIN_MENU = (
    "Welcome to AgroOS\n"
    "1. Pay Dues\n"
    "2. Request Loan\n"
    "3. Repay Loan\n"
    "4. Check Balance\n"
)


def get_main_menu() -> str:
    """Return the standard USSD main menu text."""
    return USSD_MAIN_MENU


def resolve_farmer_by_phone(phone: str, db: Session):
    """Resolve a phone number to farmer memberships. Shared across all gateways."""
    from app.models.models import CooperativeMembership, Farmer

    farmer = db.query(Farmer).filter(Farmer.phone == phone).first()
    if not farmer:
        return None, []
    memberships = (
        db.query(CooperativeMembership)
        .filter(
            CooperativeMembership.farmer_id == farmer.id,
            CooperativeMembership.membership_status == "active",
        )
        .all()
    )
    return farmer, memberships


def format_loan_balance_response(phone: str, db: Session) -> str:
    """Calculate and format loan balance for USSD display. Shared logic."""
    from app.models.models import CooperativeMembership, Loan

    farmer, memberships = resolve_farmer_by_phone(phone, db)
    if not memberships:
        return "END Phone not registered. Contact your cooperative."

    total = 0.0
    for m in memberships:
        loans = (
            db.query(Loan)
            .filter(
                Loan.farmer_id == m.id,
                Loan.status == "disbursed",
            )
            .all()
        )
        for loan in loans:
            total += loan.amount

    if total == 0:
        return "END You have no active loans."
    return f"END Your total active loan balance is GHS {total:,.2f}"
