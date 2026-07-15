"""Tests for /transactions endpoints"""

from unittest.mock import AsyncMock, patch

from app.models.models import Transaction


def test_create_transaction(client, farmer):
    resp = client.post(
        "/transactions/",
        json={
            "farmer_id": farmer["id"],
            "transaction_type": "dues",
            "amount": 75.0,
            "currency": "GHS",
            "description": "Q1 Dues",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 75.0
    assert data["status"] == "pending"
    assert data["transaction_type"] == "dues"


def test_create_transaction_bad_farmer(client):
    resp = client.post(
        "/transactions/",
        json={"farmer_id": 999999, "transaction_type": "dues", "amount": 10.0},
    )
    assert resp.status_code == 404


def test_get_transaction(client, transaction):
    resp = client.get(f"/transactions/{transaction['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == transaction["id"]


def test_transaction_receipt_and_reconciliation(client, db, transaction):
    tx = db.query(Transaction).filter(Transaction.id == transaction["id"]).one()
    tx.moolre_reference = "PAYMENT-REF-001"
    db.commit()

    receipt = client.get(f"/transactions/{tx.id}/receipt")
    assert receipt.status_code == 200
    assert receipt.json()["receipt_number"].endswith(f"{tx.id:08d}")

    with patch(
        "app.routes.transactions.MoolreService.payment_status",
        new_callable=AsyncMock,
        return_value={"success": True, "status": "completed", "raw": {}},
    ):
        reconciled = client.post(f"/transactions/{tx.id}/reconcile")

    assert reconciled.status_code == 200
    assert reconciled.json()["provider_status"] == "completed"
    assert reconciled.json()["transaction"]["status"] == "completed"

    for provider_status in ("pending", "failed"):
        with patch(
            "app.routes.transactions.MoolreService.payment_status",
            new_callable=AsyncMock,
            return_value={"success": True, "status": provider_status, "raw": {}},
        ):
            repeated = client.post(f"/transactions/{tx.id}/reconcile")
        assert repeated.status_code == 200
        assert repeated.json()["transaction"]["status"] == "completed"


def test_get_transaction_not_found(client):
    resp = client.get("/transactions/999999")
    assert resp.status_code == 404


def test_list_transactions(client, transaction, cooperative):
    resp = client.get(f"/transactions/?cooperative_id={cooperative['id']}")
    assert resp.status_code == 200
    assert any(t["id"] == transaction["id"] for t in resp.json())


def test_list_transactions_filter_by_status(client, transaction, cooperative):
    resp = client.get(f"/transactions/?cooperative_id={cooperative['id']}&status=pending")
    assert resp.status_code == 200
    assert all(t["status"] == "pending" for t in resp.json())


def test_list_transactions_filter_by_type(client, transaction, cooperative):
    resp = client.get(f"/transactions/?cooperative_id={cooperative['id']}&transaction_type=dues")
    assert resp.status_code == 200
    assert all(t["transaction_type"] == "dues" for t in resp.json())


def test_same_farmer_transactions_are_isolated_by_membership(client, farmer, cooperative):
    first_tx = client.post(
        "/transactions/",
        json={"farmer_id": farmer["id"], "transaction_type": "dues", "amount": 10},
    ).json()
    second_coop = client.post(
        "/cooperatives/",
        json={"name": "Isolated Finance Cooperative", "currency": "GHS"},
    ).json()
    second_membership = client.post(
        "/farmers/",
        json={
            "name": farmer["name"],
            "phone": farmer["phone"],
            "cooperative_id": second_coop["id"],
        },
    ).json()
    second_tx = client.post(
        "/transactions/",
        json={
            "farmer_id": second_membership["id"],
            "transaction_type": "dues",
            "amount": 20,
        },
    ).json()

    first_list = client.get(
        f"/transactions/?cooperative_id={cooperative['id']}"
    ).json()
    second_list = client.get(
        f"/transactions/?cooperative_id={second_coop['id']}"
    ).json()
    assert first_tx["id"] in {row["id"] for row in first_list}
    assert second_tx["id"] not in {row["id"] for row in first_list}
    assert second_tx["id"] in {row["id"] for row in second_list}
    assert first_tx["id"] not in {row["id"] for row in second_list}


def test_update_transaction_status(client, transaction):
    resp = client.patch(
        f"/transactions/{transaction['id']}/status",
        json={"status": "failed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


def test_update_transaction_status_completed_forbidden(client, transaction):
    resp = client.patch(
        f"/transactions/{transaction['id']}/status",
        json={"status": "completed"},
    )
    assert resp.status_code == 403


def test_update_transaction_status_hidden_in_production(client, transaction, demo_admin, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-production-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-production-test-password")
    from app.config import get_settings
    from app.services.auth_service import create_access_token

    get_settings.cache_clear()
    try:
        token = create_access_token({"sub": demo_admin.email})
        resp = client.patch(
            f"/transactions/{transaction['id']}/status",
            json={"status": "failed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()


def test_get_farmer_transactions(client, farmer, transaction):
    resp = client.get(f"/transactions/farmer/{farmer['id']}")
    assert resp.status_code == 200
    assert any(t["id"] == transaction["id"] for t in resp.json())
