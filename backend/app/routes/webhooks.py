"""
Moolre Webhook Routes

Handles:
  - POST /webhooks/moolre/payment  — real-time payment confirmation
  - POST /webhooks/moolre/ussd     — USSD session menu handler
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import (
    CooperativeMembership as Farmer,
)
from app.models.models import (
    Loan,
    LoanStatus,
    PaymentWebhookEvent,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
    UssdSession,
)
from app.routes.loans import resume_loan_repayment_customer_action
from app.routes.transactions import (
    _run_dues_collect,
    pending_customer_actions,
    resume_dues_customer_action,
)
from app.schemas.schemas import UssdSessionResponse
from app.services.auth_service import get_current_user
from app.services.communications_service import CommunicationsService
from app.services.loan_request_service import (
    PendingLoanRequestError,
    create_farmer_loan_request,
)
from app.services.membership_service import memberships_for_phone
from app.services.moolre_service import MoolreService
from app.services.trust_score_service import TrustScoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

settings = get_settings()

# ---------------------------------------------------------------------------
# Signature verification helper
# ---------------------------------------------------------------------------


def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    """
    Verify Moolre webhook HMAC-SHA256 signature.
    Moolre sends the signature as:  X-Moolre-Signature: <hex_digest>

    If no secret is configured (dev/sandbox), skip verification.
    """
    if not settings.moolre_webhook_secret:
        logger.warning("MOOLRE_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    if not signature_header:
        return False

    expected = hmac.new(
        settings.moolre_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.lower().strip())


def _record_webhook_event(
    db: Session,
    *,
    payload: dict,
    signature_valid: bool,
    transaction: Transaction | None = None,
    processed: bool = False,
    message: str | None = None,
) -> PaymentWebhookEvent:
    data = payload.get("data") or {}
    external_ref = data.get("externalref") or payload.get("reference")
    event = PaymentWebhookEvent(
        event_type="payment",
        moolre_reference=external_ref,
        transaction_id=transaction.id if transaction else None,
        signature_valid=signature_valid,
        payload=json.dumps(payload),
        processed=processed,
        message=message,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _process_payment_payload(
    payload: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    signature_valid: bool,
) -> dict:
    moolre_status: int = payload.get("status", 0)
    data: dict = payload.get("data") or {}

    external_ref: str | None = data.get("externalref") or payload.get("reference")
    transaction_id: str | None = data.get("transactionid")
    amount_raw = data.get("amount") or data.get("value", "0")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    tx: Transaction | None = None
    if external_ref:
        tx = (
            db.query(Transaction)
            .filter(Transaction.moolre_reference == external_ref)
            .with_for_update()
            .first()
        )

    if not tx and transaction_id:
        tx = (
            db.query(Transaction)
            .filter(Transaction.moolre_reference == transaction_id)
            .with_for_update()
            .first()
        )

    if not tx:
        _record_webhook_event(
            db,
            payload=payload,
            signature_valid=signature_valid,
            processed=False,
            message="reference not found",
        )
        logger.warning(
            "Webhook received for unknown reference '%s' (txid: %s)", external_ref, transaction_id
        )
        return {"status": "ok", "message": "reference not found — acknowledged"}

    if tx.status in (TransactionStatus.completed, TransactionStatus.failed):
        _record_webhook_event(
            db,
            payload=payload,
            signature_valid=signature_valid,
            transaction=tx,
            processed=True,
            message=f"transaction already {tx.status.value}",
        )
        return {
            "status": "ok",
            "transaction_id": tx.id,
            "message": f"transaction already {tx.status.value}",
        }

    if moolre_status == 1:
        if abs(float(tx.amount) - amount) >= 0.01:
            _record_webhook_event(
                db,
                payload=payload,
                signature_valid=signature_valid,
                transaction=tx,
                processed=False,
                message="amount mismatch",
            )
            logger.warning(
                "Payment amount mismatch for tx_id=%s: expected=%s received=%s",
                tx.id,
                tx.amount,
                amount,
            )
            return {"status": "ok", "message": "amount mismatch — acknowledged"}

        tx.status = TransactionStatus.completed
        tx.customer_action = "none"
        tx.action_expires_at = None
        if tx.transaction_type == TransactionType.repayment and tx.loan_id:
            loan = (
                db.query(Loan)
                .filter(Loan.id == tx.loan_id, Loan.farmer_id == tx.farmer_id)
                .first()
            )
            if loan and loan.status == LoanStatus.disbursed:
                loan.status = LoanStatus.repaid
                loan.repaid_at = datetime.utcnow()
        db.commit()

        _record_webhook_event(
            db,
            payload=payload,
            signature_valid=signature_valid,
            transaction=tx,
            processed=True,
            message="Payment confirmed",
        )

        background_tasks.add_task(
            _post_payment_tasks,
            farmer_id=tx.farmer_id,
            amount=amount,
            reference=external_ref or str(transaction_id),
        )

        logger.info(
            "Payment confirmed: tx_id=%s farmer_id=%s amount=GHS%.2f",
            tx.id,
            tx.farmer_id,
            amount,
        )
        return {
            "status": "ok",
            "transaction_id": tx.id,
            "reference": external_ref,
            "message": "Payment confirmed — Trust Score queued for update",
        }

    tx.status = TransactionStatus.failed
    tx.customer_action = "none"
    tx.action_expires_at = None
    db.commit()
    _record_webhook_event(
        db,
        payload=payload,
        signature_valid=signature_valid,
        transaction=tx,
        processed=True,
        message="Payment failure recorded",
    )
    logger.info("Payment failed: tx_id=%s ref=%s", tx.id, external_ref)
    return {
        "status": "ok",
        "transaction_id": tx.id,
        "reference": external_ref,
        "message": "Payment failure recorded",
    }


# ---------------------------------------------------------------------------
# Background task: recalculate trust score + send confirmation SMS
# ---------------------------------------------------------------------------


async def _post_payment_tasks(farmer_id: int, amount: float, reference: str) -> None:
    """Runs asynchronously after a successful payment webhook."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        try:
            TrustScoreService.calculate_trust_score(farmer_id, db)
            logger.info("Trust score recalculated for farmer %s", farmer_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Trust score recalculation failed for farmer %s: %s", farmer_id, exc)

        try:
            farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
            if farmer:
                comms = CommunicationsService()
                await comms.send_payment_confirmation(farmer, amount, reference, db)
        except Exception as exc:  # noqa: BLE001
            logger.error("Payment confirmation SMS failed for farmer %s: %s", farmer_id, exc)
    finally:
        db_gen.close()


# ---------------------------------------------------------------------------
# Payment webhook
# ---------------------------------------------------------------------------


@router.post("/moolre/payment")
async def handle_moolre_payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_moolre_signature: str | None = Header(default=None),
):
    """
    Receive Moolre payment confirmation events.

    Expected payload (Moolre Payment Webhook):
    {
      "status": 1,
      "code": "P01",
      "message": "Transaction Successful",
      "data": {
        "transactionid": "...",
        "externalref": "...",    ← matches our moolre_reference
        "amount": "10.00",
        "payer": "233551300186",
        ...
      }
    }
    """
    body = await request.body()
    signature_valid = _verify_signature(body, x_moolre_signature)

    if not signature_valid:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    return _process_payment_payload(
        payload,
        db,
        background_tasks,
        signature_valid=signature_valid,
    )


# ---------------------------------------------------------------------------
# USSD session handler
#
# Moolre's USSD callback contract (docs.moolre.com/#/ussd):
#   Request body:  {"sessionId", "new", "msisdn", "network", "message",
#                    "extension", "data"}
#   Response body: {"message": "<text to show>", "reply": true|false}
#     reply=true  -> session continues, we expect another request with the
#                    user's next keystroke in "message"
#     reply=false -> session ends after this message is shown
#
# Unlike Africa's Talking-style gateways, "message" is NOT a cumulative
# dialed string — it is only what the user typed at *this* step. Session
# continuity comes entirely from "sessionId", so we keep a small in-memory
# state machine keyed by sessionId. This resets if the Render dyno restarts,
# which is an acceptable tradeoff for the demo (Issue #16 tracks moving this
# to persistent storage later).
#
# Per SECURITY.md (Issue #30): the USSD callback is unsigned by Moolre,
# unlike the HMAC-signed /moolre/payment webhook above, so no signature
# check is applied here.
# ---------------------------------------------------------------------------

USSD_MENU_MAIN = (
    "Welcome to AgroOS\n"
    "1. Check Loan Balance\n"
    "2. Pay Dues\n"
    "3. Request Loan\n"
    "4. Announcements\n"
    "5. Complete Pending Payment"
)

NOT_REGISTERED_MSG = "Phone not registered with AgroOS. Contact your cooperative."

# In-memory USSD session state: {sessionId: {...}}. See module docstring above.
_ussd_sessions: dict[str, dict] = {}


def _log_ussd_session(
    db: Session,
    *,
    session_id: str,
    phone: str,
    input_path: str,
    response_text: str,
    farmer: Farmer | None,
) -> None:
    db.add(
        UssdSession(
            session_id=session_id or None,
            phone=phone,
            input_path=input_path or None,
            response_text=response_text,
            farmer_id=farmer.id if farmer else None,
        )
    )
    db.commit()


@router.get("/ussd/logs", response_model=list[UssdSessionResponse])
def list_ussd_logs(
    limit: int = Query(default=50, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Recent USSD interactions for dashboard visibility."""
    query = db.query(UssdSession)
    if current_user is not None:
        query = query.join(Farmer, UssdSession.farmer_id == Farmer.id).filter(
            Farmer.cooperative_id == current_user.cooperative_id
        )
    return (
        query
        .order_by(UssdSession.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/moolre/ussd")
async def handle_ussd_session(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle USSD session callbacks from Moolre. See module docstring above
    for the request/response contract."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    session_id: str = payload.get("sessionId", "")
    is_new: bool = bool(payload.get("new"))
    msisdn: str = payload.get("msisdn", "")
    message: str = str(payload.get("message", "")).strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing sessionId")

    # ---- Fresh session: silently resolve the farmer's membership, then show the menu
    if is_new or session_id not in _ussd_sessions:
        memberships = memberships_for_phone(msisdn, db)
        if len(memberships) > 1:
            options = "\n".join(
                f"{index}. {membership.cooperative.name}"
                for index, membership in enumerate(memberships, start=1)
            )
            msg = f"Choose your cooperative:\n{options}"
            _ussd_sessions[session_id] = {
                "step": "select_cooperative",
                "membership_ids": [membership.id for membership in memberships],
            }
            _log_ussd_session(
                db,
                session_id=session_id,
                phone=msisdn,
                input_path="new",
                response_text=msg,
                farmer=None,
            )
            return {"message": msg, "reply": True}

        farmer = memberships[0] if memberships else None
        _ussd_sessions[session_id] = {
            "step": "main",
            "farmer_id": farmer.id if farmer else None,
        }
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path="new", response_text=USSD_MENU_MAIN, farmer=farmer)
        return {"message": USSD_MENU_MAIN, "reply": True}

    state = _ussd_sessions[session_id]

    if state["step"] == "select_cooperative":
        try:
            selected_index = int(message) - 1
            membership_id = state["membership_ids"][selected_index]
            if selected_index < 0:
                raise IndexError
        except (TypeError, ValueError, IndexError):
            return {
                "message": "Invalid cooperative. Enter one of the listed numbers:",
                "reply": True,
            }
        farmer = (
            db.query(Farmer)
            .filter(Farmer.id == membership_id)
            .first()
        )
        if not farmer:
            _ussd_sessions.pop(session_id, None)
            return {"message": NOT_REGISTERED_MSG, "reply": False}
        state["step"] = "main"
        state["farmer_id"] = farmer.id
        _log_ussd_session(
            db,
            session_id=session_id,
            phone=msisdn,
            input_path=message,
            response_text=USSD_MENU_MAIN,
            farmer=farmer,
        )
        return {"message": USSD_MENU_MAIN, "reply": True}

    farmer = db.query(Farmer).filter(Farmer.id == state.get("farmer_id")).first() if state.get("farmer_id") else None

    # ---- Main menu: dispatch on the option chosen
    if state["step"] == "main":
        if message == "1":
            if not farmer:
                _ussd_sessions.pop(session_id, None)
                _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
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
            _ussd_sessions.pop(session_id, None)
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": False}

        if message == "2":
            if not farmer:
                _ussd_sessions.pop(session_id, None)
                _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            state["step"] = "pay_amount"
            msg = "Enter amount to pay (GHS):"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": True}

        if message == "3":
            if not farmer:
                _ussd_sessions.pop(session_id, None)
                _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            state["step"] = "loan_amount"
            msg = "Enter requested loan amount (GHS):"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": True}

        if message == "4":
            announcement_text = "No new announcements. Check with your cooperative leader."
            if farmer:
                moolre = MoolreService()
                sms_result = await moolre.send_single_sms(
                    phone=farmer.phone, message=announcement_text, ref=f"announce-{farmer.id}"
                )
                if sms_result.get("success"):
                    announcement_text += "\n(Also sent via SMS.)"
            _ussd_sessions.pop(session_id, None)
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=announcement_text, farmer=farmer)
            return {"message": announcement_text, "reply": False}

        if message == "5":
            if not farmer:
                _ussd_sessions.pop(session_id, None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            actions = pending_customer_actions(farmer=farmer, db=db)
            if not actions:
                _ussd_sessions.pop(session_id, None)
                return {"message": "You have no pending payments.", "reply": False}
            if len(actions) > 1:
                state["step"] = "pending_payment_select"
                state["transaction_ids"] = [tx.id for tx in actions]
                options = "\n".join(
                    f"{index}. {tx.transaction_type.value.title()} GHS {tx.amount:.2f}"
                    for index, tx in enumerate(actions, start=1)
                )
                return {"message": f"Choose a pending payment:\n{options}", "reply": True}
            tx = actions[0]
            if tx.customer_action == "approval":
                _ussd_sessions.pop(session_id, None)
                return {
                    "message": (
                        f"GHS {tx.amount:.2f} is waiting for approval on your phone."
                    ),
                    "reply": False,
                }
            state["step"] = "pending_payment_otp"
            state["transaction_id"] = tx.id
            return {
                "message": (
                    f"Complete {tx.transaction_type.value} payment of "
                    f"GHS {tx.amount:.2f}. Enter the OTP sent to your phone:"
                ),
                "reply": True,
            }

        msg = "Invalid option.\n" + USSD_MENU_MAIN
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
        return {"message": msg, "reply": True}

    if state["step"] == "pending_payment_select":
        try:
            selected_index = int(message) - 1
            if selected_index < 0:
                raise IndexError
            transaction_id = state["transaction_ids"][selected_index]
        except (TypeError, ValueError, IndexError):
            return {"message": "Enter one of the listed payment numbers:", "reply": True}
        tx = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.farmer_id == farmer.id)
            .first()
        )
        if not tx:
            _ussd_sessions.pop(session_id, None)
            return {"message": "Pending payment not found.", "reply": False}
        if tx.customer_action == "approval":
            _ussd_sessions.pop(session_id, None)
            return {
                "message": f"GHS {tx.amount:.2f} is waiting for approval on your phone.",
                "reply": False,
            }
        state["step"] = "pending_payment_otp"
        state["transaction_id"] = tx.id
        return {
            "message": f"Enter the OTP for GHS {tx.amount:.2f}:",
            "reply": True,
        }

    if state["step"] == "pending_payment_otp":
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.id == state.get("transaction_id"),
                Transaction.farmer_id == farmer.id,
            )
            .first()
        )
        if not tx:
            _ussd_sessions.pop(session_id, None)
            return {"message": "Pending payment not found.", "reply": False}
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
        retry_otp = tx.customer_action == "otp" and tx.status == TransactionStatus.pending
        if not retry_otp:
            _ussd_sessions.pop(session_id, None)
        _log_ussd_session(
            db,
            session_id=session_id,
            phone=msisdn,
            input_path="[otp-redacted]",
            response_text=msg,
            farmer=farmer,
        )
        return {"message": msg, "reply": retry_otp}

    # ---- Request loan: amount, purpose, and confirmation
    if state["step"] == "loan_amount":
        try:
            amount = float(message)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return {
                "message": "Enter a valid loan amount greater than zero (GHS):",
                "reply": True,
            }
        state["amount"] = amount
        state["step"] = "loan_purpose"
        return {"message": "What will the loan be used for?", "reply": True}

    if state["step"] == "loan_purpose":
        purpose = message.strip()
        if not purpose or len(purpose) > 500:
            return {
                "message": "Enter a loan purpose of 1 to 500 characters:",
                "reply": True,
            }
        state["purpose"] = purpose
        state["step"] = "loan_confirm"
        return {
            "message": (
                f"Request GHS {state['amount']:.2f} for {purpose}?\n"
                "1. Submit\n2. Cancel"
            ),
            "reply": True,
        }

    if state["step"] == "loan_confirm":
        if message == "2":
            _ussd_sessions.pop(session_id, None)
            msg = "Loan request cancelled."
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": False}
        if message != "1":
            return {"message": "Enter 1 to submit or 2 to cancel:", "reply": True}
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
        _ussd_sessions.pop(session_id, None)
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
        return {"message": msg, "reply": False}

    # ---- Pay dues: amount entry
    if state["step"] == "pay_amount":
        try:
            amount = float(message)
            if amount <= 0:
                raise ValueError
        except ValueError:
            msg = "Enter a valid amount (GHS):"
            return {"message": msg, "reply": True}

        external_ref = str(uuid.uuid4())
        result = await _run_dues_collect(
            farmer=farmer,
            amount=amount,
            channel="13",
            description="Cooperative dues (USSD)",
            external_ref=external_ref,
            otp_code=None,
            db=db,
            initiation_channel="moolre_ussd",
        )
        if result.outcome == "verification_required":
            state["step"] = "pay_otp"
            state["external_ref"] = external_ref
            state["amount"] = amount
            msg = "Enter the OTP sent to your phone:"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": True}

        _ussd_sessions.pop(session_id, None)
        msg = result.message or (
            "Payment request sent. Approve the prompt on your phone." if result.status == "pending" else "Payment could not be started. Try again later."
        )
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
        return {"message": msg, "reply": False}

    # ---- Pay dues: OTP confirmation
    if state["step"] == "pay_otp":
        result = await _run_dues_collect(
            farmer=farmer,
            amount=state.get("amount", 0),
            channel="13",
            description="Cooperative dues (USSD)",
            external_ref=state["external_ref"],
            otp_code=message,
            db=db,
            initiation_channel="moolre_ussd",
        )
        msg = result.message or "Payment could not be completed. Try again later."
        retry_otp = result.customer_action == "otp"
        if not retry_otp:
            _ussd_sessions.pop(session_id, None)
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path="[otp-redacted]", response_text=msg, farmer=farmer)
        return {"message": msg, "reply": retry_otp}

    # ---- Unknown state (shouldn't happen) — reset gracefully
    _ussd_sessions.pop(session_id, None)
    msg = "Session expired. Please dial again."
    _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=None)
    return {"message": msg, "reply": False}
