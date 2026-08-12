"""Pre-checkout flow tests (public, no auth)."""

from app.models.models import Cooperative, PendingCheckout


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


def _paid_checkout(db, reference="sub_pre_signup1", plan_key="growth", band="base", amount=299.0, organisation="Signup Coop"):
    checkout = PendingCheckout(
        reference=reference,
        plan_key=plan_key,
        band=band,
        amount=amount,
        organisation=organisation,
        status="paid",
    )
    db.add(checkout)
    db.commit()
    return checkout


def test_signup_with_paid_checkout_activates_and_sets_band(client, db):
    _paid_checkout(db, organisation="Paid Cooperative")

    resp = client.post(
        "/auth/signup",
        json={
            "email": "paid-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Paid Cooperative",
            "subscription_plan": "growth",
            "checkout_ref": "sub_pre_signup1",
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["subscription_plan"] == "growth"
    assert resp.json()["subscription_band"] == "base"

    coop = db.query(Cooperative).filter(Cooperative.name == "Paid Cooperative").one()
    assert coop.subscription_plan == "growth"
    assert coop.subscription_band == "base"
    assert coop.subscription_status == "active"
    assert coop.subscription_expires_at is not None


def test_signup_with_paid_plan_but_no_checkout_is_rejected(client):
    resp = client.post(
        "/auth/signup",
        json={
            "email": "unpaid-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Unpaid Cooperative",
            "subscription_plan": "growth",
        },
    )
    assert resp.status_code == 400


def test_signup_with_unpaid_checkout_is_rejected(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_unpaid1",
        plan_key="growth",
        band="base",
        amount=299.0,
        organisation="Unpaid Coop",
        status="pending",
    )
    db.add(checkout)
    db.commit()

    resp = client.post(
        "/auth/signup",
        json={
            "email": "pending-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Pending Cooperative",
            "subscription_plan": "growth",
            "checkout_ref": "sub_pre_unpaid1",
        },
    )
    assert resp.status_code == 402


def test_upgrade_checkout_uses_band_price(client, db, demo_admin, monkeypatch):
    captured = {}

    async def fake_generate_payment_link(self, **kwargs):
        captured["amount"] = kwargs.get("amount")
        return {
            "success": True,
            "payment_url": "https://sandbox.moolre.com/pay/upgrade",
            "reference": kwargs.get("external_ref"),
        }

    monkeypatch.setattr(
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.generate_payment_link",
        fake_generate_payment_link,
    )

    resp = client.post(
        "/subscriptions/checkout",
        json={"cooperative_id": demo_admin.cooperative_id, "plan_key": "growth", "band": "plus_100"},
    )
    assert resp.status_code == 200, resp.text
    assert captured["amount"] == 599.0
