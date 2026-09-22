"""Subscription payment intents (#235).

Upgrade checkout records a single-use intent (plan, band, amount, cooperative);
the webhook verifies the paid amount against that intent and activates exactly
once. Plan information is never derived from the amount or reference string
for intent-backed payments.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks

from app.models.models import Cooperative, PaymentWebhookEvent, PendingCheckout
from app.routes.webhooks import _process_payment_payload
from app.services.plans import resolve_amount


def _payload(reference: str, amount: str, transaction_id: str = "tx-1") -> dict:
    return {
        "status": 1,
        "code": "P01",
        "data": {
            "externalref": reference,
            "transactionid": transaction_id,
            "amount": amount,
        },
    }


def _deliver(db, reference: str, amount: str, transaction_id: str = "tx-1") -> dict:
    return _process_payment_payload(
        _payload(reference, amount, transaction_id),
        db,
        BackgroundTasks(),
        signature_valid=True,
    )


@pytest.fixture()
def provider_ok():
    provider = AsyncMock()
    provider.generate_payment_link.return_value = {
        "success": True,
        "payment_url": "https://payments.example/checkout",
        "reference": "provider-side-ref",
    }
    with patch("app.routes.subscriptions.get_payment_provider", return_value=provider):
        yield provider


def _checkout(client, cooperative_id: int, plan_key: str = "growth", band: str | None = "plus_50"):
    body = {"cooperative_id": cooperative_id, "plan_key": plan_key}
    if band is not None:
        body["band"] = band
    return client.post("/subscriptions/checkout", json=body)


# ---------------------------------------------------------------------------
# Intent creation
# ---------------------------------------------------------------------------


def test_checkout_records_single_use_intent(client, db, cooperative, provider_ok):
    resp = _checkout(client, cooperative["id"], "growth", "plus_50")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    intent = db.query(PendingCheckout).filter_by(reference=body["reference"]).one()
    assert intent.kind == PendingCheckout.KIND_UPGRADE
    assert intent.status == PendingCheckout.STATUS_PENDING
    assert intent.cooperative_id == cooperative["id"]
    assert intent.plan_key == "growth"
    assert intent.band == "plus_50"
    assert intent.amount == resolve_amount("growth", "plus_50") == 449.0
    assert body["amount"] == 449.0
    assert body["intent_id"] == intent.id

    call = provider_ok.generate_payment_link.await_args.kwargs
    assert call["external_ref"] == intent.reference
    assert call["amount"] == intent.amount
    assert call["reusable"] is False


def test_checkout_rejects_plan_without_price(client, db, cooperative, provider_ok):
    before = db.query(PendingCheckout).count()
    resp = _checkout(client, cooperative["id"], "enterprise", None)
    assert resp.status_code == 400
    assert db.query(PendingCheckout).count() == before
    provider_ok.generate_payment_link.assert_not_awaited()


def test_checkout_rejects_unknown_band(client, db, cooperative, provider_ok):
    before = db.query(PendingCheckout).count()
    resp = _checkout(client, cooperative["id"], "growth", "not-a-band")
    assert resp.status_code == 400
    assert db.query(PendingCheckout).count() == before


def test_checkout_leaves_no_intent_when_provider_fails(client, db, cooperative):
    provider = AsyncMock()
    provider.generate_payment_link.return_value = {"success": False}
    before = db.query(PendingCheckout).count()
    with patch("app.routes.subscriptions.get_payment_provider", return_value=provider):
        resp = _checkout(client, cooperative["id"])
    assert resp.status_code == 400
    assert db.query(PendingCheckout).count() == before


# ---------------------------------------------------------------------------
# Webhook activation from intent
# ---------------------------------------------------------------------------


def test_webhook_activates_from_intent_and_consumes_it(client, db, cooperative, provider_ok):
    reference = _checkout(client, cooperative["id"], "growth", "plus_50").json()["reference"]

    result = _deliver(db, reference, "449.00", transaction_id="tx-activate")
    assert result["message"] == "Subscription webhook processed"

    coop = db.get(Cooperative, cooperative["id"])
    db.refresh(coop)
    assert coop.subscription_plan == "growth"
    assert coop.subscription_band == "plus_50"
    assert coop.subscription_status == "active"
    assert coop.subscription_expires_at > datetime.utcnow() + timedelta(days=29)

    intent = db.query(PendingCheckout).filter_by(reference=reference).one()
    assert intent.status == PendingCheckout.STATUS_CONSUMED
    assert intent.paid_at is not None
    assert intent.consumed_at is not None
    assert intent.provider_transaction_id == "tx-activate"

    event = db.query(PaymentWebhookEvent).filter_by(provider_payment_ref=reference).one()
    assert event.processed is True
    assert "growth" in event.message


def test_duplicate_delivery_does_not_extend_expiry_twice(client, db, cooperative, provider_ok):
    reference = _checkout(client, cooperative["id"], "growth", "base").json()["reference"]

    first = _deliver(db, reference, "299.00")
    coop = db.get(Cooperative, cooperative["id"])
    db.refresh(coop)
    first_expiry = coop.subscription_expires_at

    second = _deliver(db, reference, "299.00")
    third = _deliver(db, reference, "299.00")
    db.refresh(coop)

    assert first["message"] == "Subscription webhook processed"
    assert second["message"] == "Subscription webhook already processed"
    assert third["message"] == "Subscription webhook already processed"
    assert coop.subscription_expires_at == first_expiry
    assert (
        db.query(PaymentWebhookEvent)
        .filter(
            PaymentWebhookEvent.provider_payment_ref == reference,
            PaymentWebhookEvent.processed.is_(True),
        )
        .count()
        == 1
    )


def test_webhook_refuses_amount_that_does_not_match_intent(client, db, cooperative, provider_ok):
    # Intent is for growth/plus_50 (449); provider reports the base-band price.
    reference = _checkout(client, cooperative["id"], "growth", "plus_50").json()["reference"]

    result = _deliver(db, reference, "299.00")
    assert result["message"] == "Subscription amount mismatch"

    coop = db.get(Cooperative, cooperative["id"])
    db.refresh(coop)
    assert coop.subscription_plan == "starter"
    assert coop.subscription_band is None

    intent = db.query(PendingCheckout).filter_by(reference=reference).one()
    assert intent.status == PendingCheckout.STATUS_PENDING
    event = db.query(PaymentWebhookEvent).filter_by(provider_payment_ref=reference).one()
    assert event.processed is False
    assert event.message == "subscription amount mismatch"


def test_webhook_does_not_infer_plan_from_amount_for_intent_backed_payment(
    client, db, cooperative, provider_ok
):
    # An intent for growth/base (299) paid with the solo w50 price (199) must not
    # activate "solo" or anything else — the intent is the only source of truth.
    reference = _checkout(client, cooperative["id"], "growth", "base").json()["reference"]
    result = _deliver(db, reference, "199.00")
    assert result["message"] == "Subscription amount mismatch"
    coop = db.get(Cooperative, cooperative["id"])
    db.refresh(coop)
    assert coop.subscription_plan == "starter"


def test_intent_activates_only_its_own_cooperative(client, db, cooperative, provider_ok):
    other = Cooperative(name="Other Coop", currency="GHS")
    db.add(other)
    db.commit()

    reference = _checkout(client, cooperative["id"], "growth", "base").json()["reference"]
    _deliver(db, reference, "299.00")

    db.refresh(other)
    target = db.get(Cooperative, cooperative["id"])
    db.refresh(target)
    assert target.subscription_plan == "growth"
    assert other.subscription_plan == "starter"


def test_failed_payment_event_leaves_intent_pending(client, db, cooperative, provider_ok):
    reference = _checkout(client, cooperative["id"], "growth", "base").json()["reference"]
    payload = _payload(reference, "299.00")
    payload["status"] = 0
    payload["code"] = "P99"
    _process_payment_payload(payload, db, BackgroundTasks(), signature_valid=True)

    intent = db.query(PendingCheckout).filter_by(reference=reference).one()
    assert intent.status == PendingCheckout.STATUS_PENDING
    coop = db.get(Cooperative, cooperative["id"])
    db.refresh(coop)
    assert coop.subscription_plan == "starter"


# ---------------------------------------------------------------------------
# Pre-checkout intents record provider details and consumption
# ---------------------------------------------------------------------------


def test_pre_checkout_records_paid_at_and_signup_records_consumption(client, db, monkeypatch):
    async def fake_generate_payment_link(self, **kwargs):
        return {"success": True, "payment_url": "https://pay.example/x", "reference": kwargs["external_ref"]}

    monkeypatch.setattr(
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link",
        fake_generate_payment_link,
    )
    pre = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "growth", "band": "base", "organisation": "Intent Coop"},
    )
    assert pre.status_code == 200, pre.text
    reference = pre.json()["reference"]

    _deliver(db, reference, "299.00", transaction_id="tx-pre")
    intent = db.query(PendingCheckout).filter_by(reference=reference).one()
    assert intent.kind == PendingCheckout.KIND_PRE_CHECKOUT
    assert intent.status == PendingCheckout.STATUS_PAID
    assert intent.paid_at is not None
    assert intent.provider_transaction_id == "tx-pre"
    assert intent.consumed_at is None

    signup = client.post(
        "/auth/signup",
        json={
            "email": "intent-admin@example.com",
            "password": "strong-password-123",
            "cooperative_name": "Intent Coop",
            "subscription_plan": "growth",
            "checkout_ref": reference,
        },
    )
    assert signup.status_code in (200, 201), signup.text
    db.refresh(intent)
    assert intent.status == PendingCheckout.STATUS_CONSUMED
    assert intent.consumed_at is not None
    assert intent.cooperative_id is not None
    coop = db.get(Cooperative, intent.cooperative_id)
    assert coop.subscription_plan == "growth"
