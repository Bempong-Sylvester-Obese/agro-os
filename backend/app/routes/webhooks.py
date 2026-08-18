"""
Moolre Webhook Routes

Handles:
  - POST /webhooks/moolre/payment  — real-time payment confirmation
  - POST /webhooks/moolre/ussd     — USSD session menu handler (delegates to adapter)
"""

import hashlib
import hmac
import json
import logging

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
from app.domain.payment_event import PaymentEvent
from app.services.payment_normalization import normalize_moolre_payload
from app.models.models import (
    CooperativeMembership as Farmer,
    PaymentWebhookEvent,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
    UssdSession,
)
from app.schemas.schemas import UssdSessionResponse
from app.services.auth_service import get_current_user
from app.services.communications_service import CommunicationsService
from app.services.subscription_service import process_pre_checkout, process_subscription_upgrade
from app.services.providers.factory import get_payment_provider, get_sms_provider
from app.services.trust_score_service import TrustScoreService
from app.adapters.moolre_ussd import handle_moolre_ussd as _handle_moolre_ussd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

settings = get_settings()

def _normalize_payload(raw: dict) -> PaymentEvent:
    return normalize_moolre_payload(raw)


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
        if settings.app_env.lower() in ("production", "prod"):
            logger.error(
                "Rejecting Moolre payment webhook because no signature secret is configured"
            )
            return False
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
        provider_payment_ref=external_ref,
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

    if external_ref and external_ref.startswith("sub_pre_"):
        return process_pre_checkout(
            db,
            external_ref=external_ref,
            amount=amount,
            status_code=moolre_status,
        )

    if external_ref and external_ref.startswith("sub_upg_"):
        return process_subscription_upgrade(
            db,
            external_ref=external_ref,
            amount=amount,
            status_code=moolre_status,
            signature_valid=signature_valid,
            payload=payload,
        )

    event = normalize_moolre_payload(payload)
    event.metadata["signature_valid"] = signature_valid

    tx: Transaction | None = None
    if external_ref:
        tx = (
            db.query(Transaction)
            .filter(Transaction.provider_payment_ref == external_ref)
            .with_for_update()
            .first()
        )

    if not tx and transaction_id:
        tx = (
            db.query(Transaction)
            .filter(Transaction.provider_payment_ref == transaction_id)
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

    if tx.amount and amount and abs(float(tx.amount) - amount) >= 0.01:
        _record_webhook_event(
            db,
            payload=payload,
            signature_valid=signature_valid,
            transaction=tx,
            processed=False,
            message="amount mismatch",
        )
        logger.warning(
            "Amount mismatch for tx %s: expected %.2f got %.2f",
            tx.id, tx.amount, amount,
        )
        return {"status": "ok", "transaction_id": tx.id, "message": "amount mismatch"}

    from app.services.payment_service import process_payment_event
    result = process_payment_event(event, db)

    if result["status"] == "processed":
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
    elif result["status"] == "duplicate":
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
    else:
        _record_webhook_event(
            db,
            payload=payload,
            signature_valid=signature_valid,
            transaction=tx,
            processed=True,
            message=result.get("reason", "Payment processed"),
        )
        logger.info("Payment processed: tx_id=%s ref=%s result=%s", tx.id, external_ref, result)
        return {
            "status": "ok",
            "transaction_id": tx.id,
            "reference": external_ref,
            "message": result.get("reason", "Payment processed"),
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
                
                # Sweep platform fee (e.g., 2% of transaction)
                # Only if the cooperative has a dedicated Moolre account
                coop = farmer.cooperative
                if coop and coop.wallet_account_id:
                    fee_amount = round(amount * 0.02, 2)
                    if fee_amount > 0:
                        provider = get_payment_provider()
                        # Transfer from Coop sub-wallet to Platform Master wallet
                        await provider.internal_transfer(
                            receiver_account=settings.moolre_account_number,
                            amount=fee_amount,
                            currency=coop.currency or "GHS",
                            reference=f"Platform Fee for tx {reference}",
                            from_account_number=coop.wallet_account_id
                        )
                        logger.info(f"Swept GHS {fee_amount} fee from coop {coop.id} to master wallet")
        except Exception as exc:  # noqa: BLE001
            logger.error("Payment confirmation or fee sweep failed for farmer %s: %s", farmer_id, exc)
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
# continuity comes from "sessionId", with state persisted in the database so
# sessions survive process restarts and work across multiple app instances.
# ---------------------------------------------------------------------------

# Re-export for backward compatibility with tests
from app.services.ussd_application import get_ussd_state as _get_ussd_state


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
    """Handle USSD session callbacks from Moolre — delegates to the unified adapter."""
    configured_secret = settings.moolre_ussd_secret
    if not configured_secret:
        if settings.app_env.lower() in ("production", "prod"):
            logger.error("MOOLRE_USSD_SECRET is required in production")
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")
    else:
        supplied_secret = request.query_params.get("secret", "")
        if not hmac.compare_digest(supplied_secret, configured_secret):
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")
    return await _handle_moolre_ussd(request, db)
