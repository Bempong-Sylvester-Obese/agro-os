"""Tests for /transactions endpoints"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
)


def _stale_payment(
    db,
    farmer_id: int,
    *,
    action: str = "initiating",
    reference: str = "stale-payment-ref",
) -> Transaction:
    transaction = Transaction(
        farmer_id=farmer_id,
        transaction_type=TransactionType.dues,
        amount=50,
        status=TransactionStatus.pending,
        moolre_reference=reference,
        customer_action=action,
        action_expires_at=datetime.utcnow() - timedelta(seconds=1),
        initiation_channel="moolre_ussd",
    )
    db.add(transaction)
    db.commit()
    return transaction


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
        "app.services.providers.moolre_adapter.MoolrePaymentAdapter.payment_status",
        new_callable=AsyncMock,
        return_value={"success": True, "status": "completed", "raw": {}},
    ):
        reconciled = client.post(f"/transactions/{tx.id}/reconcile")

    assert reconciled.status_code == 200
    assert reconciled.json()["provider_status"] == "completed"
    assert reconciled.json()["transaction"]["status"] == "completed"

    for provider_status in ("pending", "failed"):
        with patch(
            "app.services.providers.moolre_adapter.MoolrePaymentAdapter.payment_status",
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


@pytest.mark.parametrize(
    ("provider_status", "expected_status", "expected_action"),
    [
        ("completed", TransactionStatus.completed, "none"),
        ("failed", TransactionStatus.failed, "none"),
        ("pending", TransactionStatus.pending, "initiating"),
    ],
)
def test_dashboard_list_reconciles_stale_payment_actions(
    client,
    db,
    farmer,
    cooperative,
    provider_status,
    expected_status,
    expected_action,
):
    transaction = _stale_payment(db, farmer["id"])
    expired_at = transaction.action_expires_at
    with patch(
        "app.services.providers.moolre_adapter."
        "MoolrePaymentAdapter.payment_status",
        new_callable=AsyncMock,
        return_value={"status": provider_status, "amount": 50},
    ) as payment_status:
        response = client.get(
            f"/transactions/?cooperative_id={cooperative['id']}"
        )
        if provider_status == "pending":
            replay = client.get(
                f"/transactions/?cooperative_id={cooperative['id']}"
            )
            assert replay.status_code == 200

    assert response.status_code == 200
    db.refresh(transaction)
    assert transaction.status == expected_status
    assert transaction.customer_action == expected_action
    if provider_status == "pending":
        assert transaction.action_expires_at > expired_at
    else:
        assert transaction.action_expires_at is None
    payment_status.assert_awaited_once()


def test_dashboard_reconciliation_keeps_state_on_provider_error(
    client, db, farmer, cooperative
):
    transaction = _stale_payment(
        db,
        farmer["id"],
        action="processing_otp",
        reference="provider-error-ref",
    )
    expired_at = transaction.action_expires_at
    with patch(
        "app.services.providers.moolre_adapter."
        "MoolrePaymentAdapter.payment_status",
        new_callable=AsyncMock,
        side_effect=TimeoutError("provider unavailable"),
    ):
        response = client.get(
            f"/transactions/?cooperative_id={cooperative['id']}"
        )

    assert response.status_code == 200
    db.refresh(transaction)
    assert transaction.status == TransactionStatus.pending
    assert transaction.customer_action == "processing_otp"
    assert transaction.action_expires_at == expired_at


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
    monkeypatch.setenv("MOOLRE_WEBHOOK_SECRET", "test-secret")
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


def test_wallet_endpoints_use_authenticated_cooperative_account(
    client, db, demo_admin, monkeypatch
):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-auth-boundary-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-auth-boundary-password")
    from app.config import get_settings
    from app.models.models import Cooperative
    from app.services.auth_service import create_access_token

    cooperative = db.query(Cooperative).filter(
        Cooperative.id == demo_admin.cooperative_id
    ).one()
    cooperative.moolre_account_number = "TENANT-WALLET-1"
    db.commit()
    get_settings.cache_clear()
    token = create_access_token({"sub": demo_admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with (
            patch(
                "app.services.providers.moolre_adapter.MoolrePaymentAdapter.account_status",
                new_callable=AsyncMock,
                return_value={"success": True, "balance": "5.00"},
            ) as account_status,
            patch(
                "app.services.providers.moolre_adapter.MoolrePaymentAdapter.list_transactions",
                new_callable=AsyncMock,
                return_value={"success": True, "transactions": []},
            ) as list_transactions,
        ):
            balance = client.get(
                "/transactions/moolre/wallet-balance", headers=headers
            )
            transactions = client.get(
                "/transactions/moolre/account-transactions", headers=headers
            )

        assert balance.status_code == 200
        assert transactions.status_code == 200
        account_status.assert_awaited_once_with(
            account_number="TENANT-WALLET-1"
        )
        assert (
            list_transactions.await_args.kwargs["account_number"]
            == "TENANT-WALLET-1"
        )
    finally:
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()


def test_get_farmer_transactions(client, farmer, transaction):
    resp = client.get(f"/transactions/farmer/{farmer['id']}")
    assert resp.status_code == 200
    assert any(t["id"] == transaction["id"] for t in resp.json())
