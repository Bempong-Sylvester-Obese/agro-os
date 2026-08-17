"""
Moolre Webhook Routes

Handles:
  - POST /webhooks/moolre/payment  — real-time payment confirmation
  - POST /webhooks/moolre/ussd     — USSD session menu handler
# USSD Gateway (Moolre webhook format) — delegates to app.services.ussd_service

Domain logic note (M2 decoupling): _process_payment_payload currently does
payment processing inline. The domain model lives in app.domain.payment_event
and the extracted service scaffolding in app.services.payment_service.
In a future milestone the webhook handler should normalize the raw Moolre
payload into a PaymentEvent and delegate to process_payment_event() so that
new payment providers can reuse the same domain logic.
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
from app.domain.payment_event import PaymentEvent
from app.models.models import (
    Announcement,
    CooperativeMembership as Farmer,
    Loan,
    LoanStatus,
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
from app.services.customer_action_service import (
    pending_customer_actions,
    resume_dues_customer_action,
)
from app.services.dues_service import run_dues_collect
from app.services.loan_repayment_service import (
    resume_loan_repayment_customer_action,
    start_farmer_loan_repayment,
)
from app.services.loan_request_service import (
    PendingLoanRequestError,
    create_farmer_loan_request,
)
from app.services.plans import (
    PLANS,
    activate_subscription,
    get_plan,
    resolve_amount,
)
from app.services.providers.factory import get_payment_provider, get_sms_provider
from app.services.trust_score_service import TrustScoreService
from app.services.ussd_service import resolve_farmer_by_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

settings = get_settings()

def _normalize_payload(raw: dict) -> PaymentEvent:
    return PaymentEvent(
        provider="moolre",
        event_type=f"payment.{raw.get('status', 'unknown')}",
        external_ref=str(raw.get("moolre_reference", raw.get("reference", ""))),
        amount=float(raw.get("amount", 0)) if raw.get("amount") else None,
        currency=raw.get("currency", "GHS"),
        status=raw.get("status", "unknown"),
        payer_phone=raw.get("payer_phone"),
        metadata=raw,
    )


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

    if external_ref and external_ref.startswith("sub_pre_"):
        if moolre_status == 1:
            from app.models.models import PendingCheckout
            checkout = (
                db.query(PendingCheckout)
                .filter(PendingCheckout.reference == external_ref)
                .with_for_update()
                .first()
            )
            if checkout and abs(float(checkout.amount) - amount) >= 0.01:
                logger.warning(
                    "Pre-checkout amount mismatch for %s: expected=%s received=%s",
                    checkout.reference,
                    checkout.amount,
                    amount,
                )
                return {"status": "ok", "message": "amount mismatch — acknowledged"}
            if checkout and checkout.status == "pending":
                checkout.status = "paid"
                db.commit()
                logger.info("Pending checkout %s marked paid", checkout.reference)
        return {"status": "ok", "message": "Pre-checkout webhook processed"}

    if external_ref and external_ref.startswith("sub_upg_"):
        if moolre_status == 1:
            try:
                parts = external_ref.split("_")
                if len(parts) >= 6 and parts[3].isdigit():
                    coop_id = int(parts[2])
                    plan_key = parts[4]
                    band_key = "_".join(parts[5:])
                    expected_amount = resolve_amount(plan_key, band_key)
                elif len(parts) >= 6 and parts[4].isdigit():
                    coop_id = int(parts[2])
                    plan_key = parts[3]
                    band_key = "_".join(parts[5:])
                    expected_amount = resolve_amount(plan_key, band_key)
                elif len(parts) == 5:
                    coop_id = int(parts[2])
                    plan_key = parts[3]
                    band_key = None
                    plan = get_plan(plan_key)
                    expected_amount = plan["price"] if plan else None
                elif len(parts) == 4:
                    coop_id = int(parts[2])
                    band_key = None
                    matching_plans = [
                        key
                        for key, candidate in PLANS.items()
                        if candidate["price"] > 0
                        and abs(float(candidate["price"]) - amount) <= 0.01
                    ]
                    if len(matching_plans) != 1:
                        raise ValueError("ambiguous legacy subscription plan")
                    plan_key = matching_plans[0]
                    expected_amount = PLANS[plan_key]["price"]
                else:
                    raise ValueError("invalid subscription reference")
                plan = get_plan(plan_key)
                if not plan or expected_amount is None or expected_amount <= 0:
                    raise ValueError("invalid paid subscription plan")
                from app.models.models import Cooperative
                coop = (
                    db.query(Cooperative)
                    .filter(Cooperative.id == coop_id)
                    .with_for_update()
                    .first()
                )
                if not coop:
                    return {"status": "ok", "message": "Cooperative not found"}

                existing_event = (
                    db.query(PaymentWebhookEvent)
                    .filter(
                        PaymentWebhookEvent.moolre_reference == external_ref,
                        PaymentWebhookEvent.processed.is_(True),
                    )
                    .first()
                )
                if existing_event:
                    return {
                        "status": "ok",
                        "message": "Subscription webhook already processed",
                    }

                if abs(amount - expected_amount) > 0.01:
                    _record_webhook_event(
                        db,
                        payload=payload,
                        signature_valid=signature_valid,
                        processed=False,
                        message="subscription amount mismatch",
                    )
                    logger.warning(
                        "Subscription payment amount %s did not match %s for %s",
                        amount,
                        expected_amount,
                        plan_key,
                    )
                    return {
                        "status": "ok",
                        "message": "Subscription amount mismatch",
                    }

                activate_subscription(coop, plan_key)
                coop.subscription_band = band_key
                db.add(
                    PaymentWebhookEvent(
                        event_type="subscription",
                        moolre_reference=external_ref,
                        signature_valid=signature_valid,
                        payload=json.dumps(payload),
                        processed=True,
                        message=f"subscription activated: {plan_key}",
                    )
                )
                db.commit()
                logger.info(
                    "Subscription upgraded for cooperative %s to %s",
                    coop.id,
                    plan_key,
                )
            except (TypeError, ValueError, IndexError) as exc:
                db.rollback()
                logger.warning("Rejected subscription webhook: %s", exc)
                return {"status": "ok", "message": "Invalid subscription reference"}
            except Exception as exc:
                db.rollback()
                logger.error("Failed to process subscription webhook: %s", exc)
        return {"status": "ok", "message": "Subscription webhook processed"}

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
                
                # Sweep platform fee (e.g., 2% of transaction)
                # Only if the cooperative has a dedicated Moolre account
                coop = farmer.cooperative
                if coop and coop.moolre_account_number:
                    fee_amount = round(amount * 0.02, 2)
                    if fee_amount > 0:
                        provider = get_payment_provider()
                        # Transfer from Coop sub-wallet to Platform Master wallet
                        await provider.internal_transfer(
                            receiver_account=settings.moolre_account_number,
                            amount=fee_amount,
                            currency=coop.currency or "GHS",
                            reference=f"Platform Fee for tx {reference}",
                            from_account_number=coop.moolre_account_number
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


def _get_ussd_state(db: Session, session_id: str, phone: str) -> dict | None:
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


def _clear_ussd_state(db: Session, session_id: str) -> None:
    db.query(UssdSession).filter(
        UssdSession.session_id == session_id
    ).update({UssdSession.session_state: None}, synchronize_session=False)
    db.commit()


def _persist_state(db: Session, session_id: str, phone: str, state: dict) -> None:
    db.add(
        UssdSession(
            session_id=session_id or None,
            phone=phone,
            session_state=state,
        )
    )
    db.commit()


def _log_ussd_session(
    db: Session,
    *,
    session_id: str,
    phone: str,
    input_path: str,
    response_text: str,
    farmer: Farmer | None,
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
    configured_secret = settings.moolre_ussd_secret
    if not configured_secret:
        if settings.app_env.lower() in ("production", "prod"):
            logger.error("MOOLRE_USSD_SECRET is required in production")
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")
    else:
        supplied_secret = request.query_params.get("secret", "")
        if not hmac.compare_digest(supplied_secret, configured_secret):
            raise HTTPException(status_code=401, detail="Invalid USSD callback secret")

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

    state = None if is_new else _get_ussd_state(db, session_id, msisdn)

    # ---- Fresh or expired session: resolve the membership, then show the menu
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
            _log_ussd_session(
                db,
                session_id=session_id,
                phone=msisdn,
                input_path="new",
                response_text=msg,
                farmer=None,
                state=state,
            )
            return {"message": msg, "reply": True}

        primary_membership = memberships[0] if memberships else None
        state = {
            "step": "main",
            "farmer_id": primary_membership.id if primary_membership else None,
        }
        _log_ussd_session(
            db,
            session_id=session_id,
            phone=msisdn,
            input_path="new",
            response_text=USSD_MENU_MAIN,
            farmer=primary_membership,
            state=state,
        )
        return {"message": USSD_MENU_MAIN, "reply": True}

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
            _clear_ussd_state(db, session_id)
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
            state=state,
        )
        return {"message": USSD_MENU_MAIN, "reply": True}

    farmer = db.query(Farmer).filter(Farmer.id == state.get("farmer_id")).first() if state.get("farmer_id") else None

    # ---- Main menu: dispatch on the option chosen
    if state["step"] == "main":
        if message == "1":
            if not farmer:
                _clear_ussd_state(db, session_id)
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
            _clear_ussd_state(db, session_id)
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
            return {"message": msg, "reply": False}

        if message == "2":
            if not farmer:
                _clear_ussd_state(db, session_id)
                _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            state["step"] = "pay_amount"
            msg = "Enter amount to pay (GHS):"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
            return {"message": msg, "reply": True}

        if message == "3":
            if not farmer:
                _clear_ussd_state(db, session_id)
                _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=NOT_REGISTERED_MSG, farmer=None)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            state["step"] = "loan_amount"
            msg = "Enter requested loan amount (GHS):"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
            return {"message": msg, "reply": True}

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
                sms = get_sms_provider()
                sms_result = await sms.send_sms(
                    recipient=farmer.phone,
                    message=announcement_text,
                )
                if sms_result.get("success"):
                    announcement_text += "\n(Also sent via SMS.)"
            _clear_ussd_state(db, session_id)
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=announcement_text, farmer=farmer)
            return {"message": announcement_text, "reply": False}

        if message == "5":
            if not farmer:
                _clear_ussd_state(db, session_id)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
            actions = pending_customer_actions(farmer=farmer, db=db)
            if not actions:
                _clear_ussd_state(db, session_id)
                return {"message": "You have no pending payments.", "reply": False}
            if len(actions) > 1:
                state["step"] = "pending_payment_select"
                state["transaction_ids"] = [tx.id for tx in actions]
                _persist_state(db, session_id, msisdn, state)
                options = "\n".join(
                    f"{index}. {tx.transaction_type.value.title()} GHS {tx.amount:.2f}"
                    for index, tx in enumerate(actions, start=1)
                )
                return {"message": f"Choose a pending payment:\n{options}", "reply": True}
            tx = actions[0]
            if tx.customer_action == "approval":
                _clear_ussd_state(db, session_id)
                return {
                    "message": (
                        f"GHS {tx.amount:.2f} is waiting for approval on your phone."
                    ),
                    "reply": False,
                }
            if tx.customer_action == "processing_otp":
                _clear_ussd_state(db, session_id)
                return {
                    "message": "Your OTP is already being processed. Check again shortly.",
                    "reply": False,
                }
            state["step"] = "pending_payment_otp"
            state["transaction_id"] = tx.id
            _persist_state(db, session_id, msisdn, state)
            return {
                "message": (
                    f"Complete {tx.transaction_type.value} payment of "
                    f"GHS {tx.amount:.2f}. Enter the OTP sent to your phone:"
                ),
                "reply": True,
            }

        if message == "6":
            if not farmer:
                _clear_ussd_state(db, session_id)
                return {"message": NOT_REGISTERED_MSG, "reply": False}
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
                _clear_ussd_state(db, session_id)
                return {"message": "You have no active loans to repay.", "reply": False}
            state["loan_ids"] = [loan.id for loan in loans]
            if len(loans) > 1:
                state["step"] = "repay_loan_select"
                _persist_state(db, session_id, msisdn, state)
                options = "\n".join(
                    f"{index}. Loan #{loan.id} GHS {loan.amount:.2f}"
                    for index, loan in enumerate(loans, start=1)
                )
                return {"message": f"Choose a loan to repay:\n{options}", "reply": True}
            state["step"] = "repay_confirm"
            state["loan_id"] = loans[0].id
            _persist_state(db, session_id, msisdn, state)
            return {
                "message": (
                    f"Repay loan #{loans[0].id} of GHS {loans[0].amount:.2f}?\n"
                    "1. Confirm\n2. Cancel"
                ),
                "reply": True,
            }

        msg = "Invalid option.\n" + USSD_MENU_MAIN
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
        return {"message": msg, "reply": True}

    if state["step"] == "repay_loan_select":
        try:
            selected_index = int(message) - 1
            loan_id = state["loan_ids"][selected_index]
            if selected_index < 0:
                raise IndexError
        except (TypeError, ValueError, IndexError):
            return {"message": "Choose a valid loan number:", "reply": True}
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        if not loan:
            _clear_ussd_state(db, session_id)
            return {"message": "Loan not found.", "reply": False}
        state["step"] = "repay_confirm"
        state["loan_id"] = loan.id
        _persist_state(db, session_id, msisdn, state)
        return {
            "message": (
                f"Repay loan #{loan.id} of GHS {loan.amount:.2f}?\n"
                "1. Confirm\n2. Cancel"
            ),
            "reply": True,
        }

    if state["step"] == "repay_confirm":
        if message != "1":
            _clear_ussd_state(db, session_id)
            return {"message": "Loan repayment cancelled.", "reply": False}
        try:
            loan = await start_farmer_loan_repayment(
                loan_id=state["loan_id"],
                farmer=farmer,
                db=db,
                initiation_channel="moolre_ussd",
            )
        except HTTPException as exc:
            _clear_ussd_state(db, session_id)
            return {"message": str(exc.detail), "reply": False}
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
            _clear_ussd_state(db, session_id)
            return {"message": "Loan repayment completed.", "reply": False}
        if tx and tx.customer_action == "otp":
            state["step"] = "repay_otp"
            state["transaction_id"] = tx.id
            _persist_state(db, session_id, msisdn, state)
            return {
                "message": "Enter the OTP Moolre sent to your phone:",
                "reply": True,
            }
        _clear_ussd_state(db, session_id)
        return {
            "message": "Approve the repayment prompt on your phone to complete.",
            "reply": False,
        }

    if state["step"] == "repay_otp":
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.id == state["transaction_id"],
                Transaction.farmer_id == farmer.id,
            )
            .first()
        )
        if not tx:
            _clear_ussd_state(db, session_id)
            return {"message": "Pending repayment not found.", "reply": False}
        try:
            loan = await resume_loan_repayment_customer_action(
                transaction=tx,
                farmer=farmer,
                otp_code=message,
                db=db,
            )
        except HTTPException as exc:
            if exc.status_code in (404, 410):
                _clear_ussd_state(db, session_id)
                return {"message": str(exc.detail), "reply": False}
            return {"message": str(exc.detail), "reply": True}
        if loan.status == LoanStatus.repaid:
            _clear_ussd_state(db, session_id)
            return {"message": "Loan repayment completed.", "reply": False}
        refreshed = db.query(Transaction).filter(Transaction.id == tx.id).first()
        if refreshed and refreshed.customer_action == "otp":
            return {"message": "OTP still required. Try again:", "reply": True}
        _clear_ussd_state(db, session_id)
        return {
            "message": "OTP accepted. Approve the repayment prompt on your phone.",
            "reply": False,
        }

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
            .filter(
                Transaction.id == transaction_id,
                Transaction.farmer_id == farmer.id,
                Transaction.status == TransactionStatus.pending,
                Transaction.customer_action.in_(("otp", "processing_otp", "approval")),
                Transaction.action_expires_at > datetime.utcnow(),
            )
            .first()
        )
        if not tx:
            _clear_ussd_state(db, session_id)
            return {"message": "Pending payment not found.", "reply": False}
        if tx.customer_action == "approval":
            _clear_ussd_state(db, session_id)
            return {
                "message": f"GHS {tx.amount:.2f} is waiting for approval on your phone.",
                "reply": False,
            }
        if tx.customer_action == "processing_otp":
            _clear_ussd_state(db, session_id)
            return {
                "message": "Your OTP is already being processed. Check again shortly.",
                "reply": False,
            }
        state["step"] = "pending_payment_otp"
        state["transaction_id"] = tx.id
        _persist_state(db, session_id, msisdn, state)
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
            _clear_ussd_state(db, session_id)
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
        except Exception:
            logger.exception("Pending USSD payment failed for transaction %s", tx.id)
            msg = "Payment could not be completed. Check again shortly."
        db.refresh(tx)
        retry_otp = tx.customer_action == "otp" and tx.status == TransactionStatus.pending
        if not retry_otp:
            _clear_ussd_state(db, session_id)
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
        _persist_state(db, session_id, msisdn, state)
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
        _persist_state(db, session_id, msisdn, state)
        return {
            "message": (
                f"Request GHS {state['amount']:.2f} for {purpose}?\n"
                "1. Submit\n2. Cancel"
            ),
            "reply": True,
        }

    if state["step"] == "loan_confirm":
        if message == "2":
            _clear_ussd_state(db, session_id)
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
        _clear_ussd_state(db, session_id)
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
            _clear_ussd_state(db, session_id)
            return {
                "message": "Payment could not be started. Try again later.",
                "reply": False,
            }
        if result.outcome == "verification_required":
            state["step"] = "pay_otp"
            state["external_ref"] = result.moolre_reference or external_ref
            state["amount"] = amount
            msg = "Enter the OTP sent to your phone:"
            _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer, state=state)
            return {"message": msg, "reply": True}

        _clear_ussd_state(db, session_id)
        msg = result.message or (
            "Payment request sent. Approve the prompt on your phone." if result.status == "pending" else "Payment could not be started. Try again later."
        )
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=farmer)
        return {"message": msg, "reply": False}

    # ---- Pay dues: OTP confirmation
    if state["step"] == "pay_otp":
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.moolre_reference == state["external_ref"],
                Transaction.farmer_id == farmer.id,
            )
            .first()
        )
        if not tx:
            _clear_ussd_state(db, session_id)
            return {"message": "Pending payment not found.", "reply": False}
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
            _clear_ussd_state(db, session_id)
        _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path="[otp-redacted]", response_text=msg, farmer=farmer)
        return {"message": msg, "reply": retry_otp}

    # ---- Unknown state (shouldn't happen) — reset gracefully
    _clear_ussd_state(db, session_id)
    msg = "Session expired. Please dial again."
    _log_ussd_session(db, session_id=session_id, phone=msisdn, input_path=message, response_text=msg, farmer=None)
    return {"message": msg, "reply": False}
