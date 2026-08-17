"""Focused billing and entitlement regression tests."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks

from app.models.models import Cooperative, PaymentWebhookEvent
from app.routes.webhooks import _process_payment_payload
from app.services.plans import get_plan_limit


def _subscription_payload(reference: str, amount: str = "299.00") -> dict:
    return {
        "status": 1,
        "data": {
            "externalref": reference,
            "transactionid": "subscription-transaction",
            "amount": amount,
        },
    }


def test_unknown_plan_uses_safe_starter_limits():
    assert get_plan_limit("unknown-plan", "max_members") == 10
    assert get_plan_limit("unknown-plan", "sms_per_month") == 100


def test_subscription_checkout_uses_provider_port(client, cooperative):
    provider = AsyncMock()
    provider.generate_payment_link.return_value = {
        "success": True,
        "payment_url": "https://payments.example/checkout",
        "reference": "provider-ref",
    }

    with patch(
        "app.routes.subscriptions.get_payment_provider",
        return_value=provider,
    ):
        response = client.post(
            "/subscriptions/checkout",
            json={"cooperative_id": cooperative["id"], "plan_key": "growth"},
        )

    assert response.status_code == 200, response.text
    provider.generate_payment_link.assert_awaited_once()
    call = provider.generate_payment_link.await_args.kwargs
    assert call["amount"] == 299.0
    assert call["external_ref"].startswith(
        f"sub_upg_{cooperative['id']}_growth_"
    )


def test_cooperative_api_cannot_grant_paid_subscription(client, cooperative):
    create_response = client.post(
        "/cooperatives/",
        json={
            "name": "Unpaid Growth Attempt",
            "subscription_plan": "growth",
            "subscription_status": "active",
        },
    )
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["subscription_plan"] == "starter"

    update_response = client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"subscription_plan": "growth"},
    )
    assert update_response.status_code == 403


def test_subscription_webhook_rejects_amount_mismatch(db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    reference = f"sub_upg_{coop.id}_growth_123"

    result = _process_payment_payload(
        _subscription_payload(reference, amount="2.99"),
        db,
        BackgroundTasks(),
        signature_valid=True,
    )

    db.refresh(coop)
    assert result["message"] == "Subscription amount mismatch"
    assert coop.subscription_plan == "starter"
    event = (
        db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.moolre_reference == reference)
        .one()
    )
    assert event.processed is False


def test_subscription_webhook_replay_does_not_extend_twice(db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    reference = f"sub_upg_{coop.id}_growth_456"
    payload = _subscription_payload(reference)

    first = _process_payment_payload(
        payload,
        db,
        BackgroundTasks(),
        signature_valid=True,
    )
    db.refresh(coop)
    first_expiry = coop.subscription_expires_at

    second = _process_payment_payload(
        payload,
        db,
        BackgroundTasks(),
        signature_valid=True,
    )
    db.refresh(coop)

    assert first["message"] == "Subscription webhook processed"
    assert second["message"] == "Subscription webhook already processed"
    assert coop.subscription_plan == "growth"
    assert coop.subscription_expires_at == first_expiry
    assert (
        db.query(PaymentWebhookEvent)
        .filter(
            PaymentWebhookEvent.moolre_reference == reference,
            PaymentWebhookEvent.processed.is_(True),
        )
        .count()
        == 1
    )


@patch(
    "app.services.providers.moolre_adapter.MoolreSmsAdapter.send_bulk_sms",
    new_callable=AsyncMock,
    return_value={"success": True, "message": "SMS queued", "raw": {}},
)
def test_sms_quota_resets_across_year_boundary(
    mock_send,
    client,
    db,
    cooperative,
    farmer,
):
    coop = db.get(Cooperative, cooperative["id"])
    now = datetime.utcnow()
    coop.sms_sent_this_month = 100
    coop.sms_month_reset = now.replace(year=now.year - 1)
    db.commit()

    response = client.post(
        "/communications/sms/broadcast",
        json={
            "cooperative_id": cooperative["id"],
            "message": "The new season begins tomorrow.",
        },
    )

    assert response.status_code == 200, response.text
    db.refresh(coop)
    assert coop.sms_sent_this_month == 1
    assert coop.sms_month_reset.year == now.year
    mock_send.assert_awaited_once()
