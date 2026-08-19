"""Subscription domain service — handles pre-checkout and upgrade activation."""
import json
import logging

from sqlalchemy.orm import Session

from app.models.models import Cooperative, PaymentWebhookEvent, PendingCheckout
from app.services.plans import PLANS, activate_subscription, get_plan, resolve_amount

logger = logging.getLogger(__name__)


def process_pre_checkout(
    db: Session,
    *,
    external_ref: str,
    amount: float,
    status_code: int,
) -> dict:
    """Handle a pre-checkout payment confirmation (sub_pre_* references)."""
    if status_code != 1:
        return {"status": "ok", "message": "Pre-checkout webhook processed"}

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


def process_subscription_upgrade(
    db: Session,
    *,
    external_ref: str,
    amount: float,
    status_code: int,
    signature_valid: bool,
    payload: dict,
) -> dict:
    """Handle a subscription upgrade payment confirmation (sub_upg_* references)."""
    if status_code != 1:
        return {"status": "ok", "message": "Subscription webhook processed"}

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
                PaymentWebhookEvent.provider_payment_ref == external_ref,
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
            db.add(
                PaymentWebhookEvent(
                    event_type="subscription",
                    provider_payment_ref=external_ref,
                    signature_valid=signature_valid,
                    payload=json.dumps(payload),
                    processed=False,
                    message="subscription amount mismatch",
                )
            )
            db.commit()
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
                provider_payment_ref=external_ref,
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
