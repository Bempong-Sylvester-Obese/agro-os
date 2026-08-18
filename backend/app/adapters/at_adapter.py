"""Africa's Talking USSD gateway adapter — translates AT form-encoded to application-service calls.

AT-style USSD uses cumulative text input (e.g. "1*500") and CON/END prefixes.
"""

import hmac
import logging
import uuid

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.models import Cooperative, CooperativeMembership, Farmer, Loan, LoanStatus
from app.services.ussd_application import UssdApplicationService
from app.services.ussd_service import resolve_farmer_by_phone

logger = logging.getLogger(__name__)

_ussd_app = UssdApplicationService()


def _con(text: str) -> Response:
    return Response(content=f"CON {text}", media_type="text/plain")


def _end(text: str) -> Response:
    return Response(content=f"END {text}", media_type="text/plain")


def _verify_secret(request: Request) -> None:
    settings = get_settings()
    configured_secret = settings.ussd_callback_secret
    if not configured_secret:
        if settings.app_env.lower() in ("production", "prod"):
            logger.error("USSD_CALLBACK_SECRET is required in production")
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")
    else:
        from fastapi import HTTPException
        supplied_secret = request.query_params.get("secret", "")
        if not hmac.compare_digest(supplied_secret, configured_secret):
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")


async def handle_at_callback(
    request: Request,
    phone_number: str,
    text: str,
    db: Session,
) -> Response:
    _verify_secret(request)
    inputs = text.split("*") if text else []

    farmer, memberships = resolve_farmer_by_phone(phone_number, db)

    if not memberships:
        if len(inputs) == 0:
            return _con("Welcome to AgroOS.\nEnter your 4-digit Cooperative Code:")
        elif len(inputs) == 1:
            return _con("Enter your 6-digit Farmer ID:")
        elif len(inputs) == 2:
            coop_code = inputs[0]
            farmer_code = inputs[1]
            coop = db.query(Cooperative).filter(Cooperative.ussd_code == coop_code).first()
            if not coop:
                return _end("Invalid Cooperative Code. Please try again.")
            membership = db.query(CooperativeMembership).filter(
                CooperativeMembership.cooperative_id == coop.id,
                CooperativeMembership.farmer_code == farmer_code
            ).first()
            if not membership:
                return _end("Invalid Farmer ID. Please try again.")
            farmer_obj = db.query(Farmer).filter(Farmer.id == membership.farmer_id).first()
            if farmer_obj:
                farmer_obj.phone = phone_number
                db.commit()
                return _end("Phone linked successfully!\nPlease dial the code again to access your account.")
            else:
                return _end("System error. Farmer not found.")
        else:
            return _end("Invalid input.")

    if len(inputs) == 0:
        return _con(f"Welcome {farmer.name}!\n1. Pay Dues\n2. Request Loan\n3. Repay Loan\n4. Check Balance")

    menu_selection = inputs[0]

    if menu_selection == "1":
        if len(inputs) == 1:
            return _con("Enter amount to pay (GHS):")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return _end("Invalid amount.")
            external_ref = str(uuid.uuid4())
            membership = memberships[0]
            from app.services.dues_service import run_dues_collect
            await run_dues_collect(
                farmer=membership,
                amount=amount,
                channel="13",
                description="Cooperative dues (USSD)",
                external_ref=external_ref,
                otp_code=None,
                db=db,
                initiation_channel="ussd_native",
            )
            return _end("Please approve the payment prompt on your phone to complete your dues payment.")

    elif menu_selection == "2":
        if len(inputs) == 1:
            return _con("Enter loan amount to request (GHS):")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return _end("Invalid amount.")
            from app.services.loan_request_service import create_farmer_loan_request, PendingLoanRequestError
            try:
                membership = memberships[0]
                create_farmer_loan_request(
                    membership=membership,
                    amount=amount,
                    purpose="Loan request via USSD",
                    db=db,
                    request_channel="ussd_native",
                )
                return _end(f"Loan request for GHS {amount} submitted successfully for review.")
            except PendingLoanRequestError:
                return _end("You already have a pending loan request.")
            except Exception as e:
                return _end(f"Failed to request loan: {str(e)}")

    elif menu_selection == "3":
        if len(inputs) == 1:
            return _con("Enter amount to repay (GHS):")
        elif len(inputs) == 2:
            amount_raw = inputs[1]
            try:
                amount = float(amount_raw)
            except ValueError:
                return _end("Invalid amount.")
            from app.schemas.schemas import LoanRepaymentInit
            from app.services.loan_repayment_service import start_farmer_loan_repayment
            try:
                await start_farmer_loan_repayment(
                    LoanRepaymentInit(amount=amount),
                    db=db,
                    current_user=None,
                    x_ussd_msisdn=phone_number,
                    x_ussd_membership_id=str(memberships[0].id)
                )
                return _end("Please approve the payment prompt on your phone to complete your loan repayment.")
            except Exception as e:
                return _end(f"Failed to process repayment: {str(e)}")

    elif menu_selection == "4":
        membership_ids = [m.id for m in memberships]
        active_loans = (
            db.query(Loan)
            .filter(Loan.farmer_id.in_(membership_ids), Loan.status == LoanStatus.disbursed)
            .all()
        )
        total_balance = sum(ln.amount for ln in active_loans)
        return _end(f"Your total active loan balance is GHS {total_balance}.")

    return _end("Invalid selection.")
