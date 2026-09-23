"""Subscription domain service — payment intents, pre-checkout and upgrade activation.

Every paid subscription flow starts by recording a single-use
:class:`PendingCheckout` intent (plan, band, amount, cooperative). The payment
webhook then reconciles the provider's event against that intent:

* the paid amount must equal the intent amount,
* the intent's plan must still be a valid paid plan,
* activation happens once — a second delivery for the same reference is a
  no-op and does not extend the expiry again.

References created before intents existed (``sub_upg_<coop>_<plan>_<ts>_<band>``)
are still accepted through :func:`_legacy_upgrade_from_reference`, which is the
only place plan information is ever parsed out of a reference string.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.payment_event import PaymentEvent
from app.models.models import Cooperative, PaymentWebhookEvent, PendingCheckout
from app.services import subscription_lifecycle as lifecycle
from app.services.plans import PLANS, get_band, get_plan, resolve_amount

logger = logging.getLogger(__name__)

PRE_CHECKOUT_PREFIX = "sub_pre_"
UPGRADE_PREFIX = "sub_upg_"

AMOUNT_TOLERANCE = 0.01


class SubscriptionIntentError(ValueError):
    """Raised when an intent cannot be created for the requested plan/band."""


def is_subscription_reference(reference: str | None) -> bool:
    return bool(reference) and reference.startswith((PRE_CHECKOUT_PREFIX, UPGRADE_PREFIX))


def _amounts_match(expected: float, received: float) -> bool:
    return abs(float(expected) - float(received)) <= AMOUNT_TOLERANCE


# ---------------------------------------------------------------------------
# Intent creation
# ---------------------------------------------------------------------------


def create_upgrade_intent(
    db: Session,
    *,
    cooperative: Cooperative,
    plan_key: str,
    band_key: str | None,
    created_by_user_id: int | None = None,
) -> PendingCheckout:
    """Record a single-use upgrade intent for an existing cooperative.

    Returns the unflushed intent; callers commit after the payment link has
    been generated so a provider failure leaves nothing behind.
    """
    plan = get_plan(plan_key)
    band = get_band(plan_key, band_key)
    amount = resolve_amount(plan_key, band_key)
    if not plan or not band or amount is None or amount <= 0:
        raise SubscriptionIntentError("Invalid paid plan selected")

    intent = PendingCheckout(
        reference=f"{UPGRADE_PREFIX}{cooperative.id}_{uuid.uuid4().hex[:16]}",
        kind=PendingCheckout.KIND_UPGRADE,
        cooperative_id=cooperative.id,
        created_by_user_id=created_by_user_id,
        plan_key=plan["key"],
        band=band["key"],
        amount=float(amount),
        currency=cooperative.currency or "GHS",
        organisation=cooperative.name,
        organization_type=cooperative.organization_type or "cooperative",
        status=PendingCheckout.STATUS_PENDING,
    )
    db.add(intent)
    db.flush()
    return intent


# ---------------------------------------------------------------------------
# Webhook dispatch
# ---------------------------------------------------------------------------


def process_subscription_event(db: Session, event: PaymentEvent) -> dict:
    """Dispatch a normalized payment event to the matching subscription flow."""
    if event.external_ref.startswith(PRE_CHECKOUT_PREFIX):
        return process_pre_checkout(db, event)
    return process_subscription_upgrade(db, event)


def _lock_intent(db: Session, reference: str) -> PendingCheckout | None:
    return (
        db.query(PendingCheckout)
        .filter(PendingCheckout.reference == reference)
        .with_for_update()
        .first()
    )


def _record_event(
    db: Session,
    event: PaymentEvent,
    *,
    processed: bool,
    message: str,
) -> None:
    db.add(
        PaymentWebhookEvent(
            event_type="subscription",
            provider_payment_ref=event.external_ref,
            signature_valid=event.signature_valid,
            payload=json.dumps(event.metadata.get("raw", {})),
            processed=processed,
            message=message,
        )
    )


def _already_processed(db: Session, reference: str) -> bool:
    return (
        db.query(PaymentWebhookEvent)
        .filter(
            PaymentWebhookEvent.provider_payment_ref == reference,
            PaymentWebhookEvent.processed.is_(True),
        )
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# Pre-checkout (public pricing page, before signup)
# ---------------------------------------------------------------------------


def process_pre_checkout(db: Session, event: PaymentEvent) -> dict:
    """Handle a pre-checkout payment confirmation (sub_pre_* references)."""
    if not event.is_success:
        return {"status": "ok", "message": "Pre-checkout webhook processed"}

    amount = float(event.amount or 0.0)
    checkout = _lock_intent(db, event.external_ref)
    if checkout is None:
        logger.warning("Pre-checkout webhook for unknown intent %s", event.external_ref)
        return {"status": "ok", "message": "Pre-checkout webhook processed"}

    if not _amounts_match(checkout.amount, amount):
        logger.warning(
            "Pre-checkout amount mismatch for %s: expected=%s received=%s",
            checkout.reference,
            checkout.amount,
            amount,
        )
        return {"status": "ok", "message": "amount mismatch — acknowledged"}

    if checkout.status == PendingCheckout.STATUS_PENDING:
        checkout.status = PendingCheckout.STATUS_PAID
        checkout.paid_at = datetime.utcnow()
        checkout.provider_transaction_id = event.provider_transaction_id
        db.commit()
        logger.info("Pending checkout %s marked paid", checkout.reference)
    return {"status": "ok", "message": "Pre-checkout webhook processed"}


# ---------------------------------------------------------------------------
# Upgrade (authenticated admin, existing cooperative)
# ---------------------------------------------------------------------------


def process_subscription_upgrade(db: Session, event: PaymentEvent) -> dict:
    """Handle a subscription upgrade payment confirmation (sub_upg_* references)."""
    if not event.is_success:
        return {"status": "ok", "message": "Subscription webhook processed"}

    try:
        intent = _lock_intent(db, event.external_ref)
        if intent is not None:
            return _activate_from_intent(db, event, intent)
        return _legacy_upgrade_from_reference(db, event)
    except (TypeError, ValueError, IndexError) as exc:
        db.rollback()
        logger.warning("Rejected subscription webhook: %s", exc)
        return {"status": "ok", "message": "Invalid subscription reference"}
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.error("Failed to process subscription webhook: %s", exc)
        return {"status": "ok", "message": "Subscription webhook processed"}


def _activate_from_intent(db: Session, event: PaymentEvent, intent: PendingCheckout) -> dict:
    """Verify the event against a stored intent and activate exactly once."""
    if intent.kind != PendingCheckout.KIND_UPGRADE:
        raise ValueError("reference is not an upgrade intent")

    if intent.status != PendingCheckout.STATUS_PENDING:
        logger.info("Upgrade intent %s already %s; ignoring replay", intent.reference, intent.status)
        return {"status": "ok", "message": "Subscription webhook already processed"}

    amount = float(event.amount or 0.0)
    if not _amounts_match(intent.amount, amount):
        _record_event(db, event, processed=False, message="subscription amount mismatch")
        db.commit()
        logger.warning(
            "Subscription payment amount %s did not match intent %s (%s) for %s",
            amount,
            intent.reference,
            intent.amount,
            intent.plan_key,
        )
        return {"status": "ok", "message": "Subscription amount mismatch"}

    plan = get_plan(intent.plan_key)
    if not plan or float(plan["price"]) <= 0:
        raise ValueError("invalid paid subscription plan")
    if intent.band and get_band(intent.plan_key, intent.band) is None:
        raise ValueError("invalid subscription band")

    coop = (
        db.query(Cooperative)
        .filter(Cooperative.id == intent.cooperative_id)
        .with_for_update()
        .first()
    )
    if not coop:
        return {"status": "ok", "message": "Cooperative not found"}

    lifecycle.renew(coop, intent.plan_key, intent.band)
    now = datetime.utcnow()
    intent.status = PendingCheckout.STATUS_CONSUMED
    intent.paid_at = now
    intent.consumed_at = now
    intent.provider_transaction_id = event.provider_transaction_id
    _record_event(db, event, processed=True, message=f"subscription activated: {intent.plan_key}")
    db.commit()
    logger.info(
        "Subscription upgraded for cooperative %s to %s/%s via intent %s",
        coop.id,
        intent.plan_key,
        intent.band,
        intent.reference,
    )
    return {"status": "ok", "message": "Subscription webhook processed"}


def _legacy_upgrade_from_reference(db: Session, event: PaymentEvent) -> dict:
    """Activate from a pre-intent reference (``sub_upg_<coop>_<plan>_<ts>_<band>``).

    Kept so payment links issued before intents existed still work. New links
    never take this path because their intent is found first.
    """
    external_ref = event.external_ref
    amount = float(event.amount or 0.0)

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
            if candidate["price"] > 0 and _amounts_match(candidate["price"], amount)
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

    if _already_processed(db, external_ref):
        return {"status": "ok", "message": "Subscription webhook already processed"}

    if not _amounts_match(expected_amount, amount):
        _record_event(db, event, processed=False, message="subscription amount mismatch")
        db.commit()
        logger.warning(
            "Subscription payment amount %s did not match %s for %s",
            amount,
            expected_amount,
            plan_key,
        )
        return {"status": "ok", "message": "Subscription amount mismatch"}

    lifecycle.renew(coop, plan_key, band_key)
    _record_event(db, event, processed=True, message=f"subscription activated: {plan_key}")
    db.commit()
    logger.info(
        "Subscription upgraded for cooperative %s to %s (legacy reference)",
        coop.id,
        plan_key,
    )
    return {"status": "ok", "message": "Subscription webhook processed"}
