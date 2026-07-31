"""Tests for /loans endpoints (with Moolre transfer mocked)"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.models import (
    CommunicationLog,
    Loan,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.routes.loans import _disburse_external_ref
from app.services.moolre_service import MoolreService


@contextmanager
def _mock_disburse_moolre(*, transfer_result=None, status_result=None, wallet_account="PLATFORM-ACC"):
    transfer_result = transfer_result or _transfer_initiated()
    status_result = status_result or _transfer_status_completed()
    with (
        patch(
            "app.routes.loans.MoolreService.resolve_verified_account",
            new_callable=AsyncMock,
            return_value=(wallet_account, None),
        ),
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value=transfer_result,
        ) as mock_transfer,
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            return_value=status_result,
        ) as mock_status,
    ):
        yield mock_transfer, mock_status


def test_legacy_loan_creation_is_available_only_in_test_mode(client, farmer):
    with patch(
        "app.routes.loans.get_settings",
        return_value=SimpleNamespace(app_env="development"),
    ):
        response = client.post(
            "/loans/",
            json={
                "farmer_id": farmer["id"],
                "amount": 100,
                "purpose": "Legacy fixture",
            },
        )

    assert response.status_code == 403


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


def _payment_otp_required(ext_ref: str = "repay-otp") -> dict:
    return {
        "success": False,
        "verification_required": True,
        "outcome": "verification_required",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "OTP required",
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


def test_disburse_external_ref_is_unique_numeric_moolre_format():
    first = _disburse_external_ref(7)
    second = _disburse_external_ref(7)

    assert first.isdigit()
    assert len(first) == 12
    assert first.startswith("07")
    assert second != first


def _approve_and_disburse(client, farmer, amount: float, loan_id: int | None = None):
    if loan_id is None:
        create_resp = client.post(
            "/loans/", json={"farmer_id": farmer["id"], "amount": amount}
        )
        loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with _mock_disburse_moolre(status_result=_transfer_status_completed(amount)):
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


def test_create_loan_with_repayment_date(client, farmer):
    resp = client.post(
        "/loans/",
        json={
            "farmer_id": farmer["id"],
            "amount": 500.0,
            "purpose": "Seeds",
            "repayment_date": "2026-07-26",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["expected_repayment_date"] == "2026-07-26"


def test_create_loan_bad_farmer(client):
    resp = client.post(
        "/loans/",
        json={"farmer_id": 999999, "amount": 100.0},
    )
    assert resp.status_code == 404


def test_list_loans(client, farmer, cooperative):
    client.post("/loans/", json={"farmer_id": farmer["id"], "amount": 200.0})
    resp = client.get(f"/loans/?cooperative_id={cooperative['id']}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_list_loans_filter_by_farmer(client, farmer, cooperative):
    client.post("/loans/", json={"farmer_id": farmer["id"], "amount": 100.0})
    resp = client.get(f"/loans/?cooperative_id={cooperative['id']}&farmer_id={farmer['id']}")
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
    assert data["approved_by"] == "system"


def test_approve_already_approved_loan_fails(client, farmer):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})
    resp = client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin2"})
    assert resp.status_code == 409


def test_reject_loan_records_reason_and_sends_sms(client, farmer, db):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    )
    loan_id = create_resp.json()["id"]
    with patch(
        "app.services.communications_service.MoolreService.send_single_sms",
        new_callable=AsyncMock,
        return_value={
            "success": True,
            "message": "SMS queued",
            "raw": {"data": "sms-ref-123"},
        },
    ) as mock_send:
        resp = client.post(
            f"/loans/{loan_id}/reject",
            json={"reason": "Insufficient repayment history"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["rejection_reason"] == "Insufficient repayment history"
    assert resp.json()["rejected_at"] is not None
    assert resp.json()["notification_status"] == "sent"
    mock_send.assert_awaited_once()
    assert mock_send.await_args.kwargs["phone"] == farmer["phone"]
    assert (
        "Reason: Insufficient repayment history"
        in mock_send.await_args.kwargs["message"]
    )
    log = db.query(CommunicationLog).order_by(CommunicationLog.id.desc()).first()
    assert log.status == "sent"
    assert log.moolre_ref == "sms-ref-123"


def test_reject_loan_requires_reason(client, farmer):
    loan_id = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    ).json()["id"]

    resp = client.post(f"/loans/{loan_id}/reject", json={})

    assert resp.status_code == 422


def test_reject_loan_reports_failed_sms_delivery(client, farmer):
    loan_id = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    ).json()["id"]
    with patch(
        "app.services.communications_service.MoolreService.send_single_sms",
        new_callable=AsyncMock,
        return_value={"success": False, "message": "Provider unavailable", "raw": {}},
    ):
        resp = client.post(
            f"/loans/{loan_id}/reject",
            json={"reason": "Incomplete application"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["notification_status"] == "failed"


def test_cancel_requested_loan_records_reason(client, farmer):
    loan_id = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 100.0}
    ).json()["id"]

    resp = client.post(
        f"/loans/{loan_id}/cancel",
        json={"reason": "Member withdrew the request"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["cancellation_reason"] == "Member withdrew the request"
    assert resp.json()["cancelled_at"] is not None


def test_cancel_pending_disbursement_is_blocked(client, farmer):
    loan_id = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    ).json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})
    with _mock_disburse_moolre(
        status_result={"success": False, "status": "pending", "raw": {}},
    ):
        client.post(f"/loans/{loan_id}/disburse")

    resp = client.post(
        f"/loans/{loan_id}/cancel",
        json={"reason": "Duplicate request"},
    )

    assert resp.status_code == 409
    assert "still processing" in resp.json()["detail"]


def test_reconcile_failed_disbursement_enables_cancel_and_retry(client, farmer):
    loan_id = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    ).json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})
    with _mock_disburse_moolre(
        status_result={"success": False, "status": "pending", "raw": {}},
    ):
        client.post(f"/loans/{loan_id}/disburse")

    with _mock_disburse_moolre(
        status_result={"success": False, "status": "failed", "raw": {}},
    ):
        resp = client.get(f"/loans/{loan_id}/disbursement-status")

    assert resp.status_code == 200
    assert resp.json()["payout_status"] == "failed"
    assert resp.json()["can_cancel"] is True
    assert resp.json()["can_retry"] is True


def test_disbursement_status_preserves_completed_payout(client, db, farmer):
    loan_id = client.post(
        "/loans/",
        json={"farmer_id": farmer["id"], "amount": 250.0},
    ).json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})
    db.add(
        Transaction(
            farmer_id=farmer["id"],
            transaction_type=TransactionType.payout,
            amount=250.0,
            status=TransactionStatus.completed,
            moolre_transfer_ref="COMPLETED-PAYOUT",
            description=f"Loan disbursement #{loan_id}",
        )
    )
    db.commit()

    response = client.get(f"/loans/{loan_id}/disbursement-status")

    assert response.status_code == 200
    assert response.json()["loan_status"] == "disbursed"
    assert response.json()["payout_status"] == "completed"
    assert db.query(Loan).filter(Loan.id == loan_id).one().status.value == "disbursed"


def test_disburse_loan(client, farmer):
    """Mock Moolre transfer + status reconciliation."""
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with _mock_disburse_moolre() as (mock_transfer, mock_status):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disbursed"
    assert data["moolre_transfer_ref"] == "TEST-TRANSFER-001"
    mock_transfer.assert_called_once()
    mock_status.assert_called_once()
    assert mock_status.call_args.kwargs["id_type"] == "2"


def test_disburse_loan_uses_platform_wallet(client, farmer, cooperative):
    service = MoolreService()
    client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"moolre_account_number": "COOP-WALLET-999"},
    )
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with _mock_disburse_moolre(wallet_account=service.settings.moolre_account_number) as (mock_transfer, _mock_status):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    assert mock_transfer.call_args.kwargs["account_number"] == service.settings.moolre_account_number


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

    with _mock_disburse_moolre(transfer_result=mock_result):
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

    with _mock_disburse_moolre(
        status_result={"success": False, "status": "failed", "raw": {}},
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

    with _mock_disburse_moolre(
        status_result={"success": False, "status": "pending", "raw": {}},
    ):
        resp = client.post(f"/loans/{loan_id}/disburse")

    assert resp.status_code == 200
    loan_resp = client.get(f"/loans/{loan_id}")
    assert loan_resp.json()["status"] == "approved"


def test_disburse_retry_updates_pending_transaction_without_duplicate(client, farmer, db):
    create_resp = client.post(
        "/loans/", json={"farmer_id": farmer["id"], "amount": 250.0}
    )
    loan_id = create_resp.json()["id"]
    client.post(f"/loans/{loan_id}/approve", json={"approved_by": "Admin"})

    with _mock_disburse_moolre(
        status_result={"success": False, "status": "pending", "raw": {}},
    ):
        first_resp = client.post(f"/loans/{loan_id}/disburse")
    assert first_resp.status_code == 200

    pending_tx = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_type == TransactionType.payout,
            Transaction.description == f"Loan disbursement #{loan_id}",
        )
        .one()
    )
    assert pending_tx.status == TransactionStatus.pending

    with (
        patch(
            "app.routes.loans.MoolreService.resolve_verified_account",
            new_callable=AsyncMock,
            return_value=("PLATFORM-ACC", None),
        ),
        patch(
            "app.routes.loans.MoolreService.transfer_status",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "success": False,
                    "status": "failed",
                    "transaction_id": pending_tx.moolre_transfer_ref,
                    "raw": {"message": "Transaction Failed"},
                },
                _transfer_status_completed(250.0),
            ],
        ) as mock_status,
        patch(
            "app.routes.loans.MoolreService.initiate_transfer",
            new_callable=AsyncMock,
            return_value={
                **_transfer_initiated("fresh-attempt"),
                "moolre_transfer_ref": "TEST-TRANSFER-002",
            },
        ) as mock_transfer,
    ):
        retry_resp = client.post(f"/loans/{loan_id}/disburse")

    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "disbursed"
    mock_transfer.assert_called_once()
    assert mock_status.call_args_list[0].kwargs["id_type"] == "2"
    assert db.query(Transaction).filter(
        Transaction.transaction_type == TransactionType.payout,
        Transaction.description == f"Loan disbursement #{loan_id}",
    ).count() == 2
    db.refresh(pending_tx)
    assert pending_tx.status == TransactionStatus.failed


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


def test_ambiguous_repayment_preserves_attempt_and_blocks_duplicate(
    client, farmer, db
):
    loan_id = _approve_and_disburse(client, farmer, 150.0)

    with patch(
        "app.routes.loans.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        side_effect=RuntimeError("provider timeout"),
    ) as mock_pay:
        with pytest.raises(RuntimeError, match="provider timeout"):
            client.post(f"/loans/{loan_id}/repay")
        repeated = client.post(f"/loans/{loan_id}/repay")

    tx = db.query(Transaction).filter(
        Transaction.loan_id == loan_id,
        Transaction.transaction_type == TransactionType.repayment,
    ).one()
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "disbursed"
    assert tx.status == TransactionStatus.pending
    assert tx.customer_action == "initiating"
    assert tx.action_expires_at is not None
    mock_pay.assert_called_once()


def test_farmer_completes_repayment_otp_from_ussdk(client, farmer, db):
    loan_id = _approve_and_disburse(client, farmer, 150.0)
    with (
        patch(
            "app.routes.loans.MoolreService.initiate_payment",
            new_callable=AsyncMock,
            side_effect=[
                _payment_otp_required("repay-ref-otp"),
                _payment_initiated("repay-ref-otp"),
            ],
        ) as mock_pay,
        patch(
            "app.routes.loans.MoolreService.payment_status",
            new_callable=AsyncMock,
            return_value={"success": False, "status": "pending", "raw": {}},
        ),
    ):
        initiated = client.post(f"/loans/{loan_id}/repay")
        assert initiated.status_code == 200
        tx = (
            db.query(Transaction)
            .filter(
                Transaction.loan_id == loan_id,
                Transaction.transaction_type == TransactionType.repayment,
            )
            .one()
        )
        assert tx.customer_action == "otp"

        completed = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": farmer["phone"]},
                    "values": {
                        "transaction_id": tx.id,
                        "otp_code": "654321",
                    },
                },
            },
        )

    assert completed.status_code == 200
    db.refresh(tx)
    assert tx.customer_action == "approval"
    assert mock_pay.call_args_list[1].kwargs["otpcode"] == "654321"
    assert (
        mock_pay.call_args_list[1].kwargs["external_ref"]
        == mock_pay.call_args_list[0].kwargs["external_ref"]
    )


def test_admin_repayment_otp_endpoint_is_removed(client, farmer):
    resp = client.post(
        "/loans/999/repay/verify",
        json={"otp_code": "123456"},
    )
    assert resp.status_code == 404


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
