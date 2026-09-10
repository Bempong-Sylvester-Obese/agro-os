"""USSD application service — provider-neutral menu state machine.

Extracted from routes/webhooks.py (Moolre USSD), routes/ussdk_hooks.py, and
routes/ussd.py so that all three gateways share one business-logic core.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import (
    Announcement,
    Cooperative,
    CooperativeMembership,
    Loan,
    LoanStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
    UssdSession,
)
from app.services.ussd_service import resolve_farmer_by_phone

logger = logging.getLogger(__name__)

USSD_MENU_MAIN = (
    "Welcome to AgroOS\n"
    "1. Check Loan Balance\n"
    "2. Pay Dues\n"
    "3. Request Loan\n"
    "4. Announcements\n"
    "5. Complete Pending Payment\n"
    "6. Repay Loan"
)

NOT_REGISTERED_MSG = "Phone not registered with AgroOS. Contact your cooperative."

_USSD_SESSION_TTL_SECONDS = 3600

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USSD_MAIN_MENU = (
    "Welcome to AgroOS\n"
    "1. Check Loan Balance\n"
    "2. Pay Dues\n"
    "3. Request Loan\n"
    "4. Announcements\n"
    "5. Complete Pending Payment\n"
    "6. Repay Loan"
)

NOT_REGISTERED_MSG = "Phone not registered with AgroOS. Contact your cooperative."

_USSD_SESSION_TTL_SECONDS = 3600


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass
class UssdRequest:
    session_id: str
    phone_number: str
    input_text: str
    is_new_session: bool
    cooperative_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UssdResponse:
    text: str
    continue_session: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------


def get_ussd_state(db: Session, session_id: str, phone: str) -> dict | None:
    rows = (
        db.query(UssdSession)
        .filter(
            UssdSession.session_id == session_id,
            UssdSession.phone == phone,
        )
        .order_by(UssdSession.created_at.desc())
        .all()
    )
    for row in rows:
        if row.session_state is not None:
            if (datetime.utcnow() - row.created_at).total_seconds() <= _USSD_SESSION_TTL_SECONDS:
                return row.session_state
    return None


def clear_ussd_state(db: Session, session_id: str) -> None:
    db.query(UssdSession).filter(
        UssdSession.session_id == session_id
    ).update({UssdSession.session_state: None}, synchronize_session=False)
    db.commit()


def persist_state(db: Session, session_id: str, phone: str, state: dict) -> None:
    db.add(
        UssdSession(
            session_id=session_id or None,
            phone=phone,
            session_state=state,
        )
    )
    db.commit()


def log_ussd_session(
    db: Session,
    *,
    session_id: str,
    phone: str,
    input_path: str,
    response_text: str,
    farmer: CooperativeMembership | None,
    state: dict | None = None,
) -> None:
    db.add(
        UssdSession(
            session_id=session_id or None,
            phone=phone,
            input_path=input_path or None,
            response_text=response_text,
            farmer_id=farmer.id if farmer else None,
            session_state=state,
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# Application service
# ---------------------------------------------------------------------------


class UssdApplicationService:
    """Provider-neutral USSD menu state machine + finance orchestration."""

    # ------------------------------------------------------------------
    # Stateful session handler (Moolre-style per-keystroke sessions)
    # ------------------------------------------------------------------

    async def handle(self, request: UssdRequest, db) -> UssdResponse:
        session_id = request.session_id
        msisdn = request.phone_number
        message = request.input_text.strip()
        is_new = request.is_new_session

        if not session_id:
            raise HTTPException(status_code=400, detail="Missing sessionId")

        state = None if is_new else get_ussd_state(db, session_id, msisdn)

        # ---- Fresh or expired session
        if state is None:
            farmer_obj, memberships = resolve_farmer_by_phone(msisdn, db)
            if len(memberships) > 1:
                options = "\n".join(
                    f"{index}. {membership.cooperative.name}"
                    for index, membership in enumerate(memberships, start=1)
                )
                msg = f"Choose your cooperative:\n{options}"
                state = {
                    "step": "select_cooperative",
                    "membership_ids": [membership.id for membership in memberships],
                }
                log_ussd_session(
                    db,
                    session_id=session_id,
                    phone=msisdn,
                    input_path="new",
                    response_text=msg,
                    farmer=None,
                    state=state,
                )
                return UssdResponse(text=msg, continue_session=True)

            primary_membership = memberships[0] if memberships else None
            state = {
                "step": "main",
                "farmer_id": primary_membership.id if primary_membership else None,
            }
            log_ussd_session(
                db,
                session_id=session_id,
                phone=msisdn,
                input_path="new",
                response_text=USSD_MENU_MAIN,
                farmer=primary_membership,
                state=state,
            )
            return UssdResponse(text=USSD_MENU_MAIN, continue_session=True)

        # ---- Cooperative selection
        if state["step"] == "select_cooperative":
            try:
                selected_index = int(message) - 1
                membership_id = state["membership_ids"][selected_index]
                if selected_index < 0:
                    raise IndexError
            except (TypeError, ValueError, IndexError):
                return UssdResponse(
                    text="Invalid cooperative. Enter one of the listed numbers:",
                    continue_session=True,
                )
            farmer = (
                db.query(CooperativeMembership)
                .filter(CooperativeMembership.id == membership_id)
                .first()
            )
            if not farmer:
                clear_ussd_state(db, session_id)
                return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
            state["step"] = "main"
            state["farmer_id"] = farmer.id
            log_ussd_session(
                db,
                session_id=session_id,
                phone=msisdn,
                input_path=message,
                response_text=USSD_MENU_MAIN,
                farmer=farmer,
                state=state,
            )
            return UssdResponse(text=USSD_MENU_MAIN, continue_session=True)

        farmer = (
            db.query(CooperativeMembership)
            .filter(CooperativeMembership.id == state.get("farmer_id"))
            .first()
            if state.get("farmer_id")
            else None
        )

        # ---- Main menu
        if state["step"] == "main":
            if message == "1":
                if not farmer:
                    clear_ussd_state(db, session_id)
                    log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                    return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
                active_loans = (
                    db.query(Loan)
                    .filter(Loan.farmer_id == farmer.id, Loan.status == LoanStatus.disbursed)
                    .all()
                )
                if not active_loans:
                    msg = f"Hello {farmer.name}, you have no active loans."
                else:
                    total = sum(ln.amount for ln in active_loans)
                    msg = f"Hello {farmer.name}, active loan balance: GHS {total:.2f}"
                clear_ussd_state(db, session_id)
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
                return UssdResponse(text=msg, continue_session=False)

            if message == "2":
                if not farmer:
                    clear_ussd_state(db, session_id)
                    log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                    return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
                state["step"] = "pay_amount"
                msg = "Enter amount to pay (GHS):"
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
                return UssdResponse(text=msg, continue_session=True)

            if message == "3":
                if not farmer:
                    clear_ussd_state(db, session_id)
                    log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                    return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
                state["step"] = "loan_amount"
                msg = "Enter requested loan amount (GHS):"
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
                return UssdResponse(text=msg, continue_session=True)

            if message == "4":
                announcements = (
                    db.query(Announcement)
                    .filter(
                        Announcement.cooperative_id == farmer.cooperative_id,
                        Announcement.deleted_at.is_(None),
                    )
                    .order_by(Announcement.created_at.desc())
                    .limit(3)
                    .all()
                ) if farmer else []
                if announcements:
                    lines = []
                    for a in announcements:
                        lines.append(f"{a.title}: {a.body[:120]}")
                    announcement_text = "\n---\n".join(lines)
                else:
                    announcement_text = "No announcements yet. Check with your cooperative leader."
                if announcements and farmer and farmer.sms_consent:
                    from app.services.providers.factory import get_sms_provider
                    sms = get_sms_provider()
                    sms_result = await sms.send_sms(
                        recipient=farmer.phone,
                        message=announcement_text,
                    )
                    if sms_result.get("success"):
                        announcement_text += "\n(Also sent via SMS.)"
                clear_ussd_state(db, session_id)
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=announcement_text, farmer=farmer)
                return UssdResponse(text=announcement_text, continue_session=False)

            if message == "5":
                if not farmer:
                    clear_ussd_state(db, session_id)
                    return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
                from app.services.customer_action_service import (
                    pending_customer_actions,
                    reconcile_stale_customer_actions,
                )
                await reconcile_stale_customer_actions(db, farmer_id=farmer.id)
                actions = pending_customer_actions(farmer=farmer, db=db)
                if not actions:
                    clear_ussd_state(db, session_id)
                    return UssdResponse(text="You have no pending payments.", continue_session=False)
                if len(actions) > 1:
                    state["step"] = "pending_payment_select"
                    state["transaction_ids"] = [tx.id for tx in actions]
                    persist_state(db, session_id, msisdn, state)
                    options = "\n".join(
                        f"{index}. {tx.transaction_type.value.title()} GHS {tx.amount:.2f}"
                        for index, tx in enumerate(actions, start=1)
                    )
                    return UssdResponse(text=f"Choose a pending payment:\n{options}", continue_session=True)
                tx = actions[0]
                if tx.customer_action == "approval":
                    clear_ussd_state(db, session_id)
                    return UssdResponse(
                        text=f"GHS {tx.amount:.2f} is waiting for approval on your phone.",
                        continue_session=False,
                    )
                if tx.customer_action in ("initiating", "processing_otp"):
                    clear_ussd_state(db, session_id)
                    return UssdResponse(
                        text=(
                            "Your OTP is already being processed; the payment is "
                            "still processing. Check again shortly."
                            if tx.customer_action == "processing_otp"
                            else "Your payment is still processing. Check again shortly."
                        ),
                        continue_session=False,
                    )
                state["step"] = "pending_payment_otp"
                state["transaction_id"] = tx.id
                persist_state(db, session_id, msisdn, state)
                return UssdResponse(
                    text=(
                        f"Complete {tx.transaction_type.value} payment of "
                        f"GHS {tx.amount:.2f}. Enter the OTP sent to your phone:"
                    ),
                    continue_session=True,
                )

            if message == "6":
                if not farmer:
                    clear_ussd_state(db, session_id)
                    return UssdResponse(text=NOT_REGISTERED_MSG, continue_session=False)
                loans = (
                    db.query(Loan)
                    .filter(
                        Loan.farmer_id == farmer.id,
                        Loan.status == LoanStatus.disbursed,
                    )
                    .order_by(Loan.expected_repayment_date, Loan.id)
                    .all()
                )
                if not loans:
                    clear_ussd_state(db, session_id)
                    return UssdResponse(text="You have no active loans to repay.", continue_session=False)
                state["loan_ids"] = [loan.id for loan in loans]
                if len(loans) > 1:
                    state["step"] = "repay_loan_select"
                    persist_state(db, session_id, msisdn, state)
                    options = "\n".join(
                        f"{index}. Loan #{loan.id} GHS {loan.amount:.2f}"
                        for index, loan in enumerate(loans, start=1)
                    )
                    return UssdResponse(text=f"Choose a loan to repay:\n{options}", continue_session=True)
                state["step"] = "repay_confirm"
                state["loan_id"] = loans[0].id
                persist_state(db, session_id, msisdn, state)
                return UssdResponse(
                    text=(
                        f"Repay loan #{loans[0].id} of GHS {loans[0].amount:.2f}?\n"
                        "1. Confirm\n2. Cancel"
                    ),
                    continue_session=True,
                )

            msg = "Invalid option.\n" + USSD_MENU_MAIN
            log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return UssdResponse(text=msg, continue_session=True)

        # ---- Repay loan: select
        if state["step"] == "repay_loan_select":
            try:
                selected_index = int(message) - 1
                loan_id = state["loan_ids"][selected_index]
                if selected_index < 0:
                    raise IndexError
            except (TypeError, ValueError, IndexError):
                return UssdResponse(text="Choose a valid loan number:", continue_session=True)
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            if not loan:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Loan not found.", continue_session=False)
            state["step"] = "repay_confirm"
            state["loan_id"] = loan.id
            persist_state(db, session_id, msisdn, state)
            return UssdResponse(
                text=(
                    f"Repay loan #{loan.id} of GHS {loan.amount:.2f}?\n"
                    "1. Confirm\n2. Cancel"
                ),
                continue_session=True,
            )

        # ---- Repay loan: confirm
        if state["step"] == "repay_confirm":
            if message != "1":
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Loan repayment cancelled.", continue_session=False)
            from app.services.loan_repayment_service import start_farmer_loan_repayment
            try:
                loan = await start_farmer_loan_repayment(
                    loan_id=state["loan_id"],
                    farmer=farmer,
                    db=db,
                    initiation_channel="moolre_ussd",
                )
            except HTTPException as exc:
                clear_ussd_state(db, session_id)
                return UssdResponse(text=str(exc.detail), continue_session=False)
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.loan_id == loan.id,
                    Transaction.transaction_type == TransactionType.repayment,
                )
                .order_by(Transaction.created_at.desc())
                .first()
            )
            if loan.status == LoanStatus.repaid:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Loan repayment completed.", continue_session=False)
            if tx and tx.customer_action == "otp":
                state["step"] = "repay_otp"
                state["transaction_id"] = tx.id
                persist_state(db, session_id, msisdn, state)
                return UssdResponse(
                    text="Enter the OTP sent to your phone:",
                    continue_session=True,
                )
            clear_ussd_state(db, session_id)
            return UssdResponse(
                text="Approve the repayment prompt on your phone to complete.",
                continue_session=False,
            )

        # ---- Repay loan: OTP
        if state["step"] == "repay_otp":
            from app.services.loan_repayment_service import resume_loan_repayment_customer_action
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.id == state["transaction_id"],
                    Transaction.farmer_id == farmer.id,
                )
                .first()
            )
            if not tx:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Pending repayment not found.", continue_session=False)
            try:
                loan = await resume_loan_repayment_customer_action(
                    transaction=tx,
                    farmer=farmer,
                    otp_code=message,
                    db=db,
                )
            except HTTPException as exc:
                if exc.status_code in (404, 410):
                    clear_ussd_state(db, session_id)
                    return UssdResponse(text=str(exc.detail), continue_session=False)
                return UssdResponse(text=str(exc.detail), continue_session=True)
            if loan.status == LoanStatus.repaid:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Loan repayment completed.", continue_session=False)
            refreshed = db.query(Transaction).filter(Transaction.id == tx.id).first()
            if refreshed and refreshed.customer_action == "otp":
                return UssdResponse(text="OTP still required. Try again:", continue_session=True)
            clear_ussd_state(db, session_id)
            return UssdResponse(
                text="OTP accepted. Approve the repayment prompt on your phone.",
                continue_session=False,
            )

        # ---- Pending payment: select
        if state["step"] == "pending_payment_select":
            try:
                selected_index = int(message) - 1
                if selected_index < 0:
                    raise IndexError
                transaction_id = state["transaction_ids"][selected_index]
            except (TypeError, ValueError, IndexError):
                return UssdResponse(text="Enter one of the listed payment numbers:", continue_session=True)
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.id == transaction_id,
                    Transaction.farmer_id == farmer.id,
                    Transaction.status == TransactionStatus.pending,
                    Transaction.customer_action.in_(
                        ("initiating", "otp", "processing_otp", "approval")
                    ),
                )
                .first()
            )
            if not tx:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Pending payment not found.", continue_session=False)
            if tx.customer_action == "approval":
                clear_ussd_state(db, session_id)
                return UssdResponse(
                    text=f"GHS {tx.amount:.2f} is waiting for approval on your phone.",
                    continue_session=False,
                )
            if tx.customer_action in ("initiating", "processing_otp"):
                clear_ussd_state(db, session_id)
                return UssdResponse(
                    text=(
                        "Your OTP is already being processed; the payment is still "
                        "processing. Check again shortly."
                        if tx.customer_action == "processing_otp"
                        else "Your payment is still processing. Check again shortly."
                    ),
                    continue_session=False,
                )
            state["step"] = "pending_payment_otp"
            state["transaction_id"] = tx.id
            persist_state(db, session_id, msisdn, state)
            return UssdResponse(
                text=f"Enter the OTP for GHS {tx.amount:.2f}:",
                continue_session=True,
            )

        # ---- Pending payment: OTP
        if state["step"] == "pending_payment_otp":
            from app.services.customer_action_service import resume_dues_customer_action
            from app.services.loan_repayment_service import resume_loan_repayment_customer_action
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.id == state.get("transaction_id"),
                    Transaction.farmer_id == farmer.id,
                )
                .first()
            )
            if not tx:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Pending payment not found.", continue_session=False)
            try:
                if tx.transaction_type == TransactionType.dues:
                    result = await resume_dues_customer_action(
                        transaction=tx,
                        farmer=farmer,
                        otp_code=message,
                        db=db,
                    )
                    msg = result.message or "OTP accepted. Approve the payment prompt."
                elif tx.transaction_type == TransactionType.repayment:
                    loan = await resume_loan_repayment_customer_action(
                        transaction=tx,
                        farmer=farmer,
                        otp_code=message,
                        db=db,
                    )
                    msg = (
                        "Loan repayment completed."
                        if loan.status == LoanStatus.repaid
                        else "OTP accepted. Approve the repayment prompt on your phone."
                    )
                else:
                    msg = "This payment cannot be completed through USSD."
            except HTTPException as exc:
                msg = exc.detail if isinstance(exc.detail, str) else "Payment could not be completed."
            except Exception:
                logger.exception("Pending USSD payment failed for transaction %s", tx.id)
                msg = "Payment could not be completed. Check again shortly."
            db.refresh(tx)
            retry_otp = tx.customer_action == "otp" and tx.status == TransactionStatus.pending
            if not retry_otp:
                clear_ussd_state(db, session_id)
            log_ussd_session(
                db,
                session_id=session_id,
                phone=msisdn,
                input_path="[otp-redacted]",
                response_text=msg,
                farmer=farmer,
            )
            return UssdResponse(text=msg, continue_session=retry_otp)

        # ---- Request loan: amount
        if state["step"] == "loan_amount":
            try:
                amount = float(message)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                return UssdResponse(
                    text="Enter a valid loan amount greater than zero (GHS):",
                    continue_session=True,
                )
            state["amount"] = amount
            state["step"] = "loan_purpose"
            persist_state(db, session_id, msisdn, state)
            return UssdResponse(text="What will the loan be used for?", continue_session=True)

        # ---- Request loan: purpose
        if state["step"] == "loan_purpose":
            purpose = message.strip()
            if not purpose or len(purpose) > 500:
                return UssdResponse(
                    text="Enter a loan purpose of 1 to 500 characters:",
                    continue_session=True,
                )
            state["purpose"] = purpose
            state["step"] = "loan_confirm"
            persist_state(db, session_id, msisdn, state)
            return UssdResponse(
                text=(
                    f"Request GHS {state['amount']:.2f} for {purpose}?\n"
                    "1. Submit\n2. Cancel"
                ),
                continue_session=True,
            )

        # ---- Request loan: confirm
        if state["step"] == "loan_confirm":
            if message == "2":
                clear_ussd_state(db, session_id)
                msg = "Loan request cancelled."
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
                return UssdResponse(text=msg, continue_session=False)
            if message != "1":
                return UssdResponse(text="Enter 1 to submit or 2 to cancel:", continue_session=True)
            from app.services.loan_request_service import (
                PendingLoanRequestError,
                create_farmer_loan_request,
            )
            try:
                loan = create_farmer_loan_request(
                    membership=farmer,
                    amount=state["amount"],
                    purpose=state["purpose"],
                    db=db,
                    request_channel="moolre_ussd",
                )
                msg = f"Loan request #{loan.id} submitted for cooperative review."
            except PendingLoanRequestError as exc:
                msg = str(exc)
            except ValueError as exc:
                msg = str(exc)
            clear_ussd_state(db, session_id)
            log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return UssdResponse(text=msg, continue_session=False)

        # ---- Pay dues: amount
        if state["step"] == "pay_amount":
            from app.services.dues_service import run_dues_collect
            try:
                amount = float(message)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                msg = "Enter a valid amount (GHS):"
                return UssdResponse(text=msg, continue_session=True)

            external_ref = str(uuid.uuid4())
            try:
                result = await run_dues_collect(
                    farmer=farmer,
                    amount=amount,
                    channel="13",
                    description="Cooperative dues (USSD)",
                    external_ref=external_ref,
                    otp_code=None,
                    db=db,
                    initiation_channel="moolre_ussd",
                )
            except Exception:
                logger.exception("Could not initiate USSD dues payment for farmer %s", farmer.id)
                clear_ussd_state(db, session_id)
                return UssdResponse(
                    text="Payment could not be started. Try again later.",
                    continue_session=False,
                )
            if result.outcome == "verification_required":
                state["step"] = "pay_otp"
                state["external_ref"] = result.provider_payment_ref or external_ref
                state["amount"] = amount
                msg = "Enter the OTP sent to your phone:"
                log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
                return UssdResponse(text=msg, continue_session=True)

            clear_ussd_state(db, session_id)
            msg = result.message or (
                "Payment request sent. Approve the prompt on your phone." if result.status == "pending" else "Payment could not be started. Try again later."
            )
            log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return UssdResponse(text=msg, continue_session=False)

        # ---- Pay dues: OTP
        if state["step"] == "pay_otp":
            from app.services.customer_action_service import resume_dues_customer_action
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.provider_payment_ref == state["external_ref"],
                    Transaction.farmer_id == farmer.id,
                )
                .first()
            )
            if not tx:
                clear_ussd_state(db, session_id)
                return UssdResponse(text="Pending payment not found.", continue_session=False)
            try:
                result = await resume_dues_customer_action(
                    transaction=tx,
                    farmer=farmer,
                    otp_code=message,
                    db=db,
                )
                msg = result.message or "Payment could not be completed. Try again later."
            except HTTPException as exc:
                msg = exc.detail if isinstance(exc.detail, str) else "Payment could not be completed."
            except Exception:
                logger.exception("USSD dues OTP failed for transaction %s", tx.id)
                msg = "Payment could not be completed. Check again shortly."
            db.refresh(tx)
            retry_otp = (
                tx.status == TransactionStatus.pending and tx.customer_action == "otp"
            )
            if not retry_otp:
                clear_ussd_state(db, session_id)
            log_ussd_session(db, session_id=session_id, phone=msisdn, input_path="[otp-redacted]", response_text=msg, farmer=farmer)
            return UssdResponse(text=msg, continue_session=retry_otp)

        # ---- Unknown state fallback
        clear_ussd_state(db, session_id)
        msg = "Session expired. Please dial again."
        log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=None)
        return UssdResponse(text=msg, continue_session=False)

    # ------------------------------------------------------------------
    # Individual action methods (for hook-based gateways like USSDK)
    # ------------------------------------------------------------------

    async def check_loan_balance(
        self, phone: str, membership_id: int | str | None, db: Session
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                return {"registered": False, "balance": None, "name": None}
            membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {"registered": False, "balance": None, "name": None}

        active_loans = (
            db.query(Loan)
            .filter(Loan.farmer_id == membership.id, Loan.status == LoanStatus.disbursed)
            .all()
        )
        total = sum(ln.amount for ln in active_loans)
        return {"registered": True, "name": farmer.name, "balance": total}

    async def request_loan(
        self,
        phone: str,
        amount: float,
        purpose: str,
        membership_id: int | str | None,
        db: Session,
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.loan_request_service import (
            PendingLoanRequestError,
            create_farmer_loan_request,
        )

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                return {"action": "end", "message": "Phone not registered with AgroOS. Contact your cooperative."}
            membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {
                "action": "end",
                "message": "Phone not registered with AgroOS. Contact your cooperative.",
            }

        try:
            loan = create_farmer_loan_request(
                membership=membership,
                amount=amount,
                purpose=purpose,
                db=db,
                request_channel="ussdk",
            )
        except PendingLoanRequestError as exc:
            return {"action": "end", "message": str(exc)}
        except ValueError as exc:
            return {"action": "retry", "message": str(exc)}

        return {
            "action": "end",
            "loan_id": loan.id,
            "status": loan.status.value,
            "message": f"Loan request #{loan.id} submitted for cooperative review.",
        }

    async def pay_dues(
        self,
        phone: str,
        amount: float,
        otp_code: str | None,
        external_ref: str,
        membership_id: int | str | None,
        db: Session,
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.dues_service import run_dues_collect

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                return {"action": "end", "message": "Phone not registered with AgroOS. Contact your cooperative."}
            membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {
                "action": "end",
                "message": "Phone not registered with AgroOS. Contact your cooperative.",
            }

        result = await run_dues_collect(
            farmer=membership,
            amount=amount,
            channel="13",
            description="Cooperative dues (USSD)",
            external_ref=external_ref,
            otp_code=otp_code,
            db=db,
            initiation_channel="ussdk",
        )

        if result.outcome == "verification_required":
            return {
                "verification_required": True,
                "external_ref": external_ref,
                "message": result.message,
            }

        if result.status == "pending":
            return {
                "verification_required": False,
                "message": "Approve the payment prompt on your phone to complete.",
            }

        return {
            "action": "end",
            "message": result.message or "Payment could not be started. Try again later.",
        }

    async def repay_loan(
        self,
        phone: str,
        loan_id: int | None,
        transaction_id: int | None,
        otp_code: str | None,
        membership_id: int | str | None,
        db: Session,
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.loan_repayment_service import (
            resume_loan_repayment_customer_action,
            start_farmer_loan_repayment,
        )

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                return {"action": "end", "message": "Phone not registered with AgroOS."}
            membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {"action": "end", "message": "Phone not registered with AgroOS."}

        if transaction_id and otp_code:
            try:
                selected_transaction_id = int(transaction_id)
            except (TypeError, ValueError):
                return {"action": "retry", "message": "Choose a valid repayment."}
            tx = (
                db.query(Transaction)
                .filter(
                    Transaction.id == selected_transaction_id,
                    Transaction.farmer_id == membership.id,
                    Transaction.transaction_type == TransactionType.repayment,
                )
                .first()
            )
            if not tx:
                return {"action": "end", "message": "Pending repayment not found."}
            loan = await resume_loan_repayment_customer_action(
                transaction=tx,
                farmer=membership,
                otp_code=otp_code,
                db=db,
            )
            return {
                "action": "end" if loan.status == LoanStatus.repaid else "pending",
                "message": (
                    "Loan repayment completed."
                    if loan.status == LoanStatus.repaid
                    else "OTP accepted. Approve the repayment prompt on your phone."
                ),
            }

        if not loan_id:
            loans = (
                db.query(Loan)
                .filter(
                    Loan.farmer_id == membership.id,
                    Loan.status == LoanStatus.disbursed,
                )
                .order_by(Loan.expected_repayment_date, Loan.id)
                .all()
            )
            return {
                "action": "select_loan" if loans else "end",
                "message": "Choose a loan to repay." if loans else "You have no active loans.",
                "loans": [
                    {
                        "loan_id": loan.id,
                        "amount": loan.amount,
                        "due_date": (
                            loan.expected_repayment_date.isoformat()
                            if loan.expected_repayment_date
                            else None
                        ),
                    }
                    for loan in loans
                ],
            }

        try:
            selected_loan_id = int(loan_id)
        except (TypeError, ValueError):
            return {"action": "retry", "message": "Choose a valid loan."}

        loan = await start_farmer_loan_repayment(
            loan_id=selected_loan_id,
            farmer=membership,
            db=db,
            initiation_channel="ussdk",
        )
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.loan_id == loan.id,
                Transaction.transaction_type == TransactionType.repayment,
            )
            .order_by(Transaction.created_at.desc())
            .first()
        )
        if loan.status == LoanStatus.repaid:
            return {"action": "end", "message": "Loan repayment completed."}
        if tx and tx.customer_action == "otp":
            return {
                "action": "request_otp",
                "transaction_id": tx.id,
                "message": "Enter the OTP sent to your phone.",
            }
        return {
            "action": "end",
            "message": "Approve the repayment prompt on your phone to complete.",
        }

    async def pending_payment(
        self,
        phone: str,
        transaction_id: int | None,
        otp_code: str | None,
        membership_id: int | str | None,
        db: Session,
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.customer_action_service import (
            expire_customer_actions,
            pending_customer_actions,
            reconcile_stale_customer_actions,
            resume_dues_customer_action,
        )
        from app.services.loan_repayment_service import resume_loan_repayment_customer_action

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                return {"action": "end", "message": "Phone not registered with AgroOS."}
            membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {"action": "end", "message": "Phone not registered with AgroOS."}

        await reconcile_stale_customer_actions(db, farmer_id=membership.id)
        if not transaction_id:
            actions = pending_customer_actions(farmer=membership, db=db)
            return {
                "action": "select_payment" if actions else "end",
                "message": (
                    "Choose a pending payment."
                    if actions
                    else "You have no pending payments."
                ),
                "payments": [
                    {
                        "transaction_id": tx.id,
                        "type": tx.transaction_type.value,
                        "amount": tx.amount,
                        "customer_action": tx.customer_action,
                    }
                    for tx in actions
                ],
            }

        try:
            selected_id = int(transaction_id)
        except (TypeError, ValueError):
            return {"action": "retry", "message": "Choose a valid pending payment."}
        expire_customer_actions(db, farmer_id=membership.id)
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.id == selected_id,
                Transaction.farmer_id == membership.id,
                Transaction.status == TransactionStatus.pending,
                Transaction.customer_action.in_(
                    ("initiating", "otp", "processing_otp", "approval")
                ),
            )
            .first()
        )
        if not tx:
            return {"action": "end", "message": "Pending payment not found."}
        if tx.customer_action == "approval":
            return {
                "action": "end",
                "message": "Approve the payment prompt on your phone to complete.",
            }
        if tx.customer_action in ("initiating", "processing_otp"):
            return {
                "action": "end",
                "message": (
                    "Your OTP is already being processed; the payment is still "
                    "processing. Check again shortly."
                    if tx.customer_action == "processing_otp"
                    else "Your payment is still processing. Check again shortly."
                ),
            }

        if not otp_code:
            return {
                "action": "request_otp",
                "transaction_id": tx.id,
                "message": "Enter the OTP sent to your phone.",
            }
        try:
            if tx.transaction_type == TransactionType.dues:
                result = await resume_dues_customer_action(
                    transaction=tx,
                    farmer=membership,
                    otp_code=otp_code,
                    db=db,
                )
                message = result.message
                retry_otp = result.customer_action == "otp"
            elif tx.transaction_type == TransactionType.repayment:
                loan = await resume_loan_repayment_customer_action(
                    transaction=tx,
                    farmer=membership,
                    otp_code=otp_code,
                    db=db,
                )
                message = (
                    "Loan repayment completed."
                    if loan.status == LoanStatus.repaid
                    else "OTP accepted. Approve the repayment prompt on your phone."
                )
                retry_otp = tx.customer_action == "otp"
            else:
                return {"action": "end", "message": "Unsupported pending payment."}
        except HTTPException as exc:
            return {
                "action": "end" if exc.status_code in (404, 410) else "retry",
                "message": str(exc.detail),
            }
        except Exception:
            logger.exception("Pending payment completion failed for transaction %s", tx.id)
            return {
                "action": "end",
                "message": "Payment could not be completed. Check again shortly.",
            }
        if retry_otp:
            return {
                "action": "request_otp",
                "transaction_id": tx.id,
                "message": message or "OTP verification is still required. Try again.",
            }
        return {"action": "end", "message": message}

    async def view_announcements(
        self, phone: str, membership_id: int | str | None, db: Session
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.providers.factory import get_sms_provider

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                membership = None
            else:
                membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership and len(memberships) > 1:
            return cooperative_selection_payload(memberships)

        coop_id = membership.cooperative_id if membership else None
        announcements = (
            db.query(Announcement)
            .filter(
                Announcement.cooperative_id == coop_id,
                Announcement.deleted_at.is_(None),
            )
            .order_by(Announcement.created_at.desc())
            .limit(3)
            .all()
        ) if coop_id is not None else []
        if announcements:
            lines = []
            for a in announcements:
                lines.append(f"{a.title}: {a.body[:120]}")
            announcement_text = "\n---\n".join(lines)
        else:
            announcement_text = "No announcements yet. Check with your cooperative leader."

        if announcements and farmer and membership and membership.sms_consent:
            sms = get_sms_provider()
            sms_result = await sms.send_sms(
                recipient=farmer.phone,
                message=announcement_text,
            )
            if sms_result.get("success"):
                return {"message": f"{announcement_text}\n(Also sent via SMS.)"}

        return {"message": announcement_text}

    async def check_wallet_balance(
        self, phone: str, membership_id: int | str | None, db: Session
    ) -> dict:
        from app.services.membership_service import cooperative_selection_payload
        from app.services.providers.factory import get_payment_provider

        farmer, memberships = resolve_farmer_by_phone(phone, db)

        if membership_id not in (None, ""):
            try:
                selected_id = int(membership_id)
            except (TypeError, ValueError):
                membership = None
            else:
                membership = next((m for m in memberships if m.id == selected_id), None)
        else:
            membership = memberships[0] if len(memberships) == 1 else None

        if not membership:
            if len(memberships) > 1:
                return cooperative_selection_payload(memberships)
            return {
                "action": "end",
                "message": "Phone not registered with AgroOS. Contact your cooperative.",
            }

        cooperative = (
            db.query(Cooperative).filter(Cooperative.id == membership.cooperative_id).first()
        )
        coop_account = cooperative.wallet_account_id if cooperative else None

        provider = get_payment_provider()
        result = await provider.account_status(account_number=coop_account)

        if not result.get("success"):
            return {
                "action": "end",
                "message": "Could not reach the payment provider right now. Try again later.",
            }

        balance = result.get("balance")
        account_name = result.get("account_name") or "your cooperative"
        return {
            "message": f"{account_name} wallet balance: GHS {balance}",
        }
