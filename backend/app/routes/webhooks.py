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

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import MAX_PAGE_SIZE
from app.database.db import get_db
from app.models.models import Farmer, PaymentWebhookEvent, Transaction, TransactionStatus, User, UssdSession
from app.schemas.schemas import UssdSessionResponse
from app.services.auth_service import get_current_user
from app.services.communications_service import CommunicationsService
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
        tx = db.query(Transaction).filter(Transaction.moolre_reference == external_ref).first()

    if not tx and transaction_id:
        tx = db.query(Transaction).filter(Transaction.moolre_reference == transaction_id).first()

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

    if moolre_status == 1:
        tx.status = TransactionStatus.completed
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
# ---------------------------------------------------------------------------

USSD_MENU_MAIN = (
    "Welcome to AgroOS\n"
    "1. Check Loan Balance\n"
    "2. Pay Cooperative Dues\n"
    "3. Request Input Loan\n"
    "4. View Announcements\n"
    "5. Check Farm Status"
)


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
    x_moolre_signature: str | None = Header(default=None),
):
    """
    Handle USSD session callbacks from Moolre.
    Moolre posts session data; we respond with the next menu string.
    """
    body = await request.body()
    if not _verify_signature(body, x_moolre_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    session_id: str = payload.get("sessionid", "")
    phone: str = payload.get("phone", "")
    input_text: str = str(payload.get("input", "")).strip()

    farmer = db.query(Farmer).filter(Farmer.phone == phone).first()

    # ---- Main menu (no input yet)
    if not input_text or input_text == "0":
        response = {"response": USSD_MENU_MAIN, "action": "input"}
        _log_ussd_session(
            db,
            session_id=session_id,
            phone=phone,
            input_path=input_text or "menu",
            response_text=USSD_MENU_MAIN,
            farmer=farmer,
        )
        return response

    parts = input_text.split("*")
    level_1 = parts[0] if parts else ""

    # ---- Option 1: Check Loan Balance
    if level_1 == "1":
        if not farmer:
            msg = "Phone not registered with AgroOS. Contact your cooperative."
            _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=None)
            return {"response": msg, "action": "end"}
        from app.models.models import Loan, LoanStatus

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
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}

    # ---- Option 2: Pay Cooperative Dues (info — actual payment via USSD merchant code)
    elif level_1 == "2":
        merchant = settings.moolre_merchant_code or "AgroOS"
        msg = f"Dial *203*{merchant}# to pay your dues via mobile money. Thank you!"
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}

    # ---- Option 3: Request Input Loan
    elif level_1 == "3":
        if not farmer:
            msg = "Phone not registered with AgroOS."
            _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=None)
            return {"response": msg, "action": "end"}
        msg = (
            f"Hello {farmer.name}, loan requests must be submitted through your "
            "cooperative administrator. They will process it in AgroOS."
        )
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}

    # ---- Option 4: View Announcements
    elif level_1 == "4":
        msg = "No new announcements. Check with your cooperative leader."
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}

    # ---- Option 5: Check Farm Status
    elif level_1 == "5":
        if not farmer:
            msg = "Phone not registered with AgroOS."
            _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=None)
            return {"response": msg, "action": "end"}
        msg = (
            f"Farmer: {farmer.name}\n"
            f"Trust Score: {farmer.trust_score:.1f}/100\n"
            f"Status: {farmer.membership_status.value.capitalize()}"
        )
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}

    else:
        msg = "Invalid option. Please try again."
        _log_ussd_session(db, session_id=session_id, phone=phone, input_path=input_text, response_text=msg, farmer=farmer)
        return {"response": msg, "action": "end"}
