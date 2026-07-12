"""Tests for /loans endpoints (with Moolre transfer mocked)"""

from unittest.mock import AsyncMock, patch

from app.services.moolre_service import MoolreService


def _transfer_initiated(ext_ref: str = "some-uuid") -> dict:
    return {
        "success": True,
        "moolre_transfer_ref": "TEST-TRANSFER-001",
        "external_ref": ext_ref,
        "message": "Pay out Successful",
        "raw": {},
    }


def _transfer_status_completed(amount: str | float = "250.0") -> dict:
    return {
        "success": True,
        "status": "completed",
        "transaction_id": "TEST-TRANSFER-001",
        "amount": str(amount),
        "raw": {},
    }


def _payment_initiated(ext_ref: str = "repay-uuid") -> dict:
    return {
        "success": True,
        "verification_required": False,
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "Payment request sent",
        "raw": {},
    }


def _payment_status_completed(amount: str | float = "150.0") -> dict:
    return {
        "success": True,
        "status": "completed",
        "transaction_id": "TEST-PAYMENT-001",
        "amount": str(amount),
        "raw": {},
    }


def _approve_and_disburse(client, farmer, amount: float, loan_id: int | None = None):
    if loan_id is None:
        create_resp = client.post(
            "/loans/", json={"farmer_id": farmer["id"], "amount": amount}
        )
        loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=_transfer_initiated(),
        ),
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value=_transfer_status_completed(amount),
        ),
    ):
        disburse_resp = client.post(f"/loans/{loan_id}/disburse")
    assert disburse_resp.status_code == 200, disburse_resp.text
    return loan_id


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
    """Mock Moolre transfer + status reconciliation."""
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=_transfer_initiated(),
        ) as mock_transfer,
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value=_transfer_status_completed(),
        ) as mock_status,
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disbursed"
    assert data["moolre_transfer_ref"] == "TEST-TRANSFER-001"
    mock_transfer.assert_called_once()
    mock_status.assert_called_once()


def test_disburse_loan_uses_cooperative_account(client, farmer, cooperative):
    client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"moolre_account_number": "COOP-WALLET-999"},
    )
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=_transfer_initiated(),
        ) as mock_transfer,
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value=_transfer_status_completed(),
        ),
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    assert mock_transfer.call_args.kwargs["account_number"] == "COOP-WALLET-999"


def test_resolve_account_number_prefers_cooperative_wallet():
    service = MoolreService()
    assert service.resolve_account_number("COOP-123") == "COOP-123"
    assert service.resolve_account_number("") == service.settings.moolre_account_number
    assert service.resolve_account_number(None) == service.settings.moolre_account_number


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
        "app.routes.loans.MoolreService.initiate_transfer",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 502
    loan_resp = client.get(f"/loans/{loan_id}")
    assert loan_resp.json()["status"] == "approved"


def test_disburse_loan_keeps_approved_when_transfer_status_fails(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=_transfer_initiated(),
        ),
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value={"success": False, "status": "failed", "raw": {}},
        ),
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 502
    loan_resp = client.get(f"/loans/{loan_id}")
    assert loan_resp.json()["status"] == "approved"


def test_disburse_loan_keeps_approved_when_transfer_pending(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=_transfer_initiated(),
        ),
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value={"success": False, "status": "pending", "raw": {}},
        ),
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 502
    loan_resp = client.get(f"/loans/{loan_id}")
    assert loan_resp.json()["status"] == "approved"


def test_repay_loan(client, farmer):
    """Repayment requires verified Moolre collection before marking repaid."""
    loan_id = _approve_and_disburse(client, farmer, 150.0)

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_payment",
            new_callable=AsyncMock,
            return_value=_payment_initiated("repay-ref-001"),
        ) as mock_pay,
        patch(
            "app.routes.loans.MoolreService.payment_status",
            new_callable=AsyncMock,
            return_value=_payment_status_completed(150.0),
        ) as mock_status,
    ):
        repay_resp = client.post(f"/loans/{loan_id}/repay")

    assert repay_resp.status_code == 200
    assert repay_resp.json()["status"] == "repaid"
    mock_pay.assert_called_once()
    mock_status.assert_called_once()


def test_repay_loan_stays_disbursed_when_payment_pending(client, farmer):
    loan_id = _approve_and_disburse(client, farmer, 150.0)

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_payment",
            new_callable=AsyncMock,
            return_value=_payment_initiated("repay-ref-pending"),
        ),
        patch(
            "app.routes.loans.MoolreService.payment_status",
            new_callable=AsyncMock,
            return_value={"success": False, "status": "pending", "raw": {}},
        ),
    ):
        repay_resp = client.post(f"/loans/{loan_id}/repay")

    assert repay_resp.status_code == 200
    assert repay_resp.json()["status"] == "disbursed"


def test_repay_loan_uses_cooperative_account(client, farmer, cooperative):
    client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"moolre_account_number": "COOP-REPAY-888"},
    )
    loan_id = _approve_and_disburse(client, farmer, 120.0)

    with (
        patch(
            "app.routes.loans.MoolreService.initiate_payment",
            new_callable=AsyncMock,
            return_value=_payment_initiated("repay-ref-coop"),
        ) as mock_pay,
        patch(
            "app.routes.loans.MoolreService.payment_status",
            new_callable=AsyncMock,
            return_value=_payment_status_completed(120.0),
        ),
    ):
        resp = client.post(f"/loans/{loan_id}/repay")

    assert resp.status_code == 200
    assert mock_pay.call_args.kwargs["account_number"] == "COOP-REPAY-888"
