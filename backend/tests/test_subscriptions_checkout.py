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


def test_pre_checkout_rejects_unknown_band_instead_of_charging_default(client):
    resp = client.post(
        "/subscriptions/pre-checkout",
        json={"plan_key": "growth", "band": "not-a-band", "organisation": "Acme"},
    )
    assert resp.status_code == 400


def test_pre_checkout_persists_default_band_and_plan_organization_type(
    client, db, monkeypatch
):
    _mock_link(monkeypatch)

    resp = client.post(
        "/subscriptions/pre-checkout",
        json={
            "plan_key": "solo",
            "organisation": "Acme Farm",
            "organization_type": "cooperative",
        },
    )

    assert resp.status_code == 200
    saved = db.query(PendingCheckout).filter(
        PendingCheckout.reference == resp.json()["reference"]
    ).one()
    assert saved.band == "w20"
    assert saved.organization_type == "solo_farm"


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


def test_webhook_does_not_confirm_checkout_with_wrong_amount(client, db):
    checkout = PendingCheckout(
        reference="sub_pre_wrong_amount",
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
            "data": {"externalref": checkout.reference, "amount": "1.00"},
        },
    )

    assert resp.status_code == 200
    db.refresh(checkout)
    assert checkout.status == "pending"
    assert "amount mismatch" in resp.json()["message"]


def test_payment_webhook_requires_signature_secret_in_production(client, monkeypatch):
    from app.routes import webhooks as webhooks_module

    monkeypatch.setattr(webhooks_module.settings, "app_env", "production")
    monkeypatch.setattr(webhooks_module.settings, "moolre_webhook_secret", "")

    resp = client.post(
        "/webhooks/moolre/payment",
        json={
            "status": 1,
            "data": {"externalref": "sub_pre_forged", "amount": "299.00"},
        },
    )

    assert resp.status_code == 401


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


def test_paid_checkout_is_single_use_and_duplicate_webhook_does_not_reopen_it(
    client, db
):
    checkout = _paid_checkout(db, reference="sub_pre_single_use")
    signup_body = {
        "email": "first-owner@example.com",
        "password": "strong-password",
        "cooperative_name": "First Cooperative",
        "subscription_plan": "growth",
        "checkout_ref": checkout.reference,
    }

    first = client.post("/auth/signup", json=signup_body)
    assert first.status_code == 201, first.text
    db.refresh(checkout)
    assert checkout.status == "consumed"

    webhook = client.post(
        "/webhooks/moolre/payment",
        json={
            "status": 1,
            "data": {"externalref": checkout.reference, "amount": "299.00"},
        },
    )
    assert webhook.status_code == 200
    db.refresh(checkout)
    assert checkout.status == "consumed"

    second = client.post(
        "/auth/signup",
        json={**signup_body, "email": "second-owner@example.com"},
    )
    assert second.status_code == 402


def test_solo_checkout_controls_signup_organization_type(client, db):
    _paid_checkout(
        db,
        reference="sub_pre_solo_signup",
        plan_key="solo",
        band="w20",
        amount=99.0,
        organisation="Solo Farm",
    ).organization_type = "solo_farm"
    db.commit()

    resp = client.post(
        "/auth/signup",
        json={
            "email": "solo-owner@example.com",
            "password": "strong-password",
            "cooperative_name": "Ignored Name",
            "subscription_plan": "starter",
            "organization_type": "cooperative",
            "checkout_ref": "sub_pre_solo_signup",
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["organization_type"] == "solo_farm"
    coop = db.query(Cooperative).filter(Cooperative.name == "Solo Farm").one()
    assert coop.organization_type == "solo_farm"


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

    webhook = client.post(
        "/webhooks/moolre/payment",
        json={
            "status": 1,
            "data": {
                "externalref": resp.json()["reference"],
                "amount": "599.00",
            },
        },
    )
    assert webhook.status_code == 200
    db.refresh(demo_admin.cooperative)
    assert demo_admin.cooperative.subscription_plan == "growth"
    assert demo_admin.cooperative.subscription_band == "plus_100"
