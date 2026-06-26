"""Tests for /loans endpoints (with Moolre transfer mocked)"""

from unittest.mock import AsyncMock, patch


def test_create_loan(client, farmer):
    resp = client.post(
        "/loans/",
        json={
            "farmer_id": farmer["id"],
            "amount": 500.0,
            "currency": "GHS",
            "purpose": "Fertiliser for cocoa farm",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "requested"
    assert data["amount"] == 500.0


def test_create_loan_bad_farmer(client):
    resp = client.post(
        "/loans/",
        json={"farmer_id": 999999, "amount": 100.0},
    )
    assert resp.status_code == 404


def test_list_loans(client, farmer):
    client.post("/loans/", json={"farmer_id": farmer["id"], "amount": 200.0})
    resp = client.get("/loans/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_list_loans_filter_by_farmer(client, farmer):
    client.post("/loans/", json={"farmer_id": farmer["id"], "amount": 100.0})
    resp = client.get(f"/loans/?farmer_id={farmer['id']}")
    assert resp.status_code == 200
    assert all(ln["farmer_id"] == farmer["id"] for ln in resp.json())


def test_get_loan(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 300.0}
    )
    loan_id = create_resp.json()["id"]
    resp = client.get(f"/loans/{loan_id}")
    assert resp.status_code == 200


def test_approve_loan(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 400.0}
    )
    loan_id = create_resp.json()["id"]

    approve_resp = client.post(
        f"/loans/{loan_id}/approve",
        json={"approved_by": "Admin Kwame"},
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "approved"
    assert data["approved_by"] == "Admin Kwame"


def test_approve_already_approved_loan_fails(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})
    # Try approving again
    resp = client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin2"})
    assert resp.status_code == 409


def test_reject_loan(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    )
    loan_id = create_resp.json()["id"]
    resp = client.post(f"/loans/{loan_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_disburse_loan(client, farmer):
    """Mock Moolre transfer to avoid real HTTP calls."""
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    mock_result = {
        "success": True,
        "moolre_transfer_ref": "TEST-TRANSFER-001",
        "external_ref": "some-uuid",
        "message": "Pay out Successful",
        "raw": {},
    }

    with patch(
        "app.services.moolre_service.MoolreService.initiate_transfer",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disbursed"
    assert data["moolre_transfer_ref"] == "TEST-TRANSFER-001"


def test_disburse_loan_keeps_approved_when_transfer_fails(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    mock_result = {
        "success": False,
        "moolre_transfer_ref": None,
        "external_ref": "some-uuid",
        "message": "Transfer failed",
        "raw": {},
    }

    with patch(
        "app.services.moolre_service.MoolreService.initiate_transfer",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 502
    loan_resp = client.get(f"/loans/{loan_id}")
    assert loan_resp.json()["status"] == "approved"


def test_repay_loan(client, farmer):
    """Test full repay flow after disbursement (Moolre mocked)."""
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 150.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    mock_result = {
        "success": True,
        "moolre_transfer_ref": "TEST-TRANSFER-002",
        "external_ref": "uuid-002",
        "message": "Pay out Successful",
        "raw": {},
    }

    with patch(
        "app.services.moolre_service.MoolreService.initiate_transfer",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        client.post(f"/loans/{loan_id}/disburse")

    repay_resp = client.post(f"/loans/{loan_id}/repay")
    assert repay_resp.status_code == 200
    assert repay_resp.json()["status"] == "repaid"
