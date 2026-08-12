"""Pre-checkout flow tests (public, no auth)."""

from app.models.models import PendingCheckout


def _mock_link(monkeypatch, **extra):
    async def fake_generate_payment_link(self, **kwargs):
        return {
            "success": True,
            "payment_url": "https://sandbox.moolre.com/pay/pre",
            "reference": kwargs.get("external_ref"),
        }

    monkeypatch.setattr(
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link",
        fake_generate_payment_link,
    )


def test_pre_checkout_creates_pending_record_and_returns_link(client, db, monkeypatch):
    _mock_link(monkeypatch)

    resp = client.post(
        "/subscriptions/pre-checkout",
        json={
            "plan_key": "growth",
            "band": "plus_50",
            "organisation": "Ashanti Farmers Cooperative",
            "location": "Kumasi",
            "member_count": 100,
            "role": "Cooperative administrator",
            "organization_type": "cooperative",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["amount"] == 449.0
    assert body["authorization_url"]
    assert body["reference"].startswith("sub_pre_")

    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == body["reference"]).one()
    assert saved.plan_key == "growth"
    assert saved.band == "plus_50"
    assert saved.status == "pending"


def test_pre_checkout_rejects_unknown_plan(client):
    resp = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "vip", "organisation": "Acme"},
    )
    assert resp.status_code == 400


def test_pre_checkout_rejects_custom_solo_band(client):
    resp = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "solo", "band": "custom", "organisation": "Acme Farm"},
    )
    assert resp.status_code == 400


def test_webhook_marks_pending_checkout_paid(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_wh123",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Webhook Coop",
    )
    db.add(checkout)
    db.commit()

    resp = client.post(
        "/webhooks/moolre/payment",
        json={
            "status": 1,
            "data": {"externalref": "sub_pre_wh123", "amount": "299.00"},
        },
    )

    assert resp.status_code == 200
    saved = db.query(PendingCheckout).filter(PendingCheckout.reference == "sub_pre_wh123").one()
    assert saved.status == "paid"
