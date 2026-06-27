"""
Moolre Webhook Routes

Handles:
  - POST /webhooks/moolre/payment  — real-time payment confirmation
  - POST /webhooks/moolre/ussd     — USSD session menu handler
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import get_db
from app.models.models import Farmer, Transaction, TransactionStatus
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

    if not _verify_signature(body, x_moolre_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    moolre_status: int = payload.get("status", 0)
    data: dict = payload.get("data") or {}

    external_ref: str | None = data.get("externalref") or payload.get("reference")
    transaction_id: str | None = data.get("transactionid")
    amount_raw = data.get("amount") or data.get("value", "0")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    # Locate our transaction record
    tx: Transaction | None = None
    if external_ref:
        tx = db.query(Transaction).filter(Transaction.moolre_reference == external_ref).first()

    if not tx and transaction_id:
        # Fallback: try matching Moolre's own transaction ID
        tx = db.query(Transaction).filter(Transaction.moolre_reference == transaction_id).first()

    if not tx:
        logger.warning(
            "Webhook received for unknown reference '%s' (txid: %s)", external_ref, transaction_id
        )
        # Return 200 so Moolre doesn't retry
        return {"status": "ok", "message": "reference not found — acknowledged"}

    if moolre_status == 1:
        # Payment success
        tx.status = TransactionStatus.completed
        db.commit()

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

    else:
        # Payment failed
        tx.status = TransactionStatus.failed
        db.commit()
        logger.info("Payment failed: tx_id=%s ref=%s", tx.id, external_ref)
        return {
            "status": "ok",
            "transaction_id": tx.id,
            "reference": external_ref,
            "message": "Payment failure recorded",
        }


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


@router.post("/moolre/ussd")
async def handle_ussd_session(request: Request, db: Session = Depends(get_db)):
    """
    Handle USSD session callbacks from Moolre.
    Moolre posts session data; we respond with the next menu string.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    session_id: str = payload.get("sessionid", "")
    phone: str = payload.get("phone", "")
    input_text: str = str(payload.get("input", "")).strip()

    farmer = db.query(Farmer).filter(Farmer.phone == phone).first()

    # ---- Main menu (no input yet)
    if not input_text or input_text == "0":
        return {"response": USSD_MENU_MAIN, "action": "input"}

    parts = input_text.split("*")
    level_1 = parts[0] if parts else ""

    # ---- Option 1: Check Loan Balance
    if level_1 == "1":
        if not farmer:
            return {"response": "Phone not registered with AgroOS. Contact your cooperative.", "action": "end"}
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
        return {"response": msg, "action": "end"}

    # ---- Option 2: Pay Cooperative Dues (info — actual payment via USSD merchant code)
    elif level_1 == "2":
        merchant = settings.moolre_merchant_code or "AgroOS"
        return {
            "response": f"Dial *203*{merchant}# to pay your dues via mobile money. Thank you!",
            "action": "end",
        }

    # ---- Option 3: Request Input Loan
    elif level_1 == "3":
        if not farmer:
            return {"response": "Phone not registered with AgroOS.", "action": "end"}
        return {
            "response": (
                f"Hello {farmer.name}, loan requests must be submitted through your "
                "cooperative administrator. They will process it in AgroOS."
            ),
            "action": "end",
        }

    # ---- Option 4: View Announcements
    elif level_1 == "4":
        return {
            "response": "No new announcements. Check with your cooperative leader.",
            "action": "end",
        }

    # ---- Option 5: Check Farm Status
    elif level_1 == "5":
        if not farmer:
            return {"response": "Phone not registered with AgroOS.", "action": "end"}
        msg = (
            f"Farmer: {farmer.name}\n"
            f"Trust Score: {farmer.trust_score:.1f}/100\n"
            f"Status: {farmer.membership_status.value.capitalize()}"
        )
        return {"response": msg, "action": "end"}

    else:
        return {"response": "Invalid option. Please try again.", "action": "end"}
