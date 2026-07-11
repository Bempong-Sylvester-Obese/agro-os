"""Tests for /transactions endpoints"""


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


def test_get_transaction_not_found(client):
    resp = client.get("/transactions/999999")
    assert resp.status_code == 404


def test_list_transactions(client, transaction):
    resp = client.get("/transactions/")
    assert resp.status_code == 200
    assert any(t["id"] == transaction["id"] for t in resp.json())


def test_list_transactions_filter_by_status(client, transaction):
    resp = client.get("/transactions/?status=pending")
    assert resp.status_code == 200
    assert all(t["status"] == "pending" for t in resp.json())


def test_list_transactions_filter_by_type(client, transaction):
    resp = client.get("/transactions/?transaction_type=dues")
    assert resp.status_code == 200
    assert all(t["transaction_type"] == "dues" for t in resp.json())


def test_update_transaction_status(client, transaction):
    resp = client.patch(
        f"/transactions/{transaction['id']}/status",
        json={"status": "failed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


def test_get_farmer_transactions(client, farmer, transaction):
    resp = client.get(f"/transactions/farmer/{farmer['id']}")
    assert resp.status_code == 200
    assert any(t["id"] == transaction["id"] for t in resp.json())
