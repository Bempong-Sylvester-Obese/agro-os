"""Tests for demo-critical endpoints: auth, webhook simulate, payment link, USSD logs."""


def test_auth_login(client, demo_admin):
    resp = client.post(
        "/auth/login",
        json={"email": "admin@agroos.demo", "password": "demo1234"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "admin@agroos.demo"


def test_simulate_payment_webhook(client, farmer, demo_admin, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-webhook-events")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-admin-password")
    from app.config import get_settings
    get_settings.cache_clear()

    tx_resp = client.post(
        "/transactions/",
        json={
            "farmer_id": farmer["id"],
            "transaction_type": "dues",
            "amount": 80.0,
            "currency": "GHS",
            "description": "Simulate webhook target",
        },
    )
    assert tx_resp.status_code == 201, tx_resp.text
    pending_tx = tx_resp.json()

    simulate = client.post(
        "/webhooks/moolre/payment/simulate",
        json={"transaction_id": pending_tx["id"]},
    )
    assert simulate.status_code == 200, simulate.text
    assert simulate.json()["status"] == "ok"

    login = client.post(
        "/auth/login",
        json={"email": "admin@agroos.demo", "password": "demo1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    events = client.get(
        "/transactions/webhook-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    assert len(events.json()) >= 1

    get_settings.cache_clear()


def test_ussd_session_logged(client, farmer):
    resp = client.post(
        "/webhooks/moolre/ussd",
        json={
            "sessionid": "test-session-1",
            "phone": farmer["phone"],
            "input": "5",
        },
    )
    assert resp.status_code == 200, resp.text

    logs = client.get("/webhooks/ussd/logs")
    assert logs.status_code == 200
    assert any(log["phone"] == farmer["phone"] for log in logs.json())


def test_payment_link_route(client, farmer, monkeypatch):
    async def fake_generate_payment_link(self, **kwargs):
        return {
            "success": True,
            "payment_url": "https://sandbox.moolre.com/pay/demo",
            "reference": kwargs.get("external_ref"),
        }

    monkeypatch.setattr(
        "app.routes.transactions.MoolreService.generate_payment_link",
        fake_generate_payment_link,
    )

    resp = client.post(
        "/transactions/payment-link",
        json={
            "farmer_id": farmer["id"],
            "amount": 50.0,
            "email": "farmer@example.com",
            "description": "Test payment link",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["payment_url"]
    assert body["transaction_id"]
