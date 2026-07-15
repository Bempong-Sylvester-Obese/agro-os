"""Tests for dashboard dues initiation and farmer-side payment completion."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.models import Transaction, TransactionStatus, TransactionType


def _tp14_result(ext_ref: str) -> dict:
    return {
        "success": False,
        "outcome": "verification_required",
        "moolre_code": "TP14",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "Please complete the verification process sent to you via SMS and try again.",
        "raw": {"status": 1, "code": "TP14", "message": "Please complete the verification process sent to you via SMS and try again."},
    }


def _tr099_result(ext_ref: str) -> dict:
    return {
        "success": True,
        "outcome": "push_sent",
        "moolre_code": "TR099",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "Payment request sent",
        "raw": {"status": 1, "code": "TR099", "message": "Payment request sent"},
    }


def _failed_result(ext_ref: str) -> dict:
    return {
        "success": False,
        "outcome": "failed",
        "moolre_code": "TP01",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "Insufficient balance",
        "raw": {"status": 0, "code": "TP01", "message": "Insufficient balance"},
    }


def test_collect_dues_uses_cooperative_account(client, farmer, cooperative):
    client.put(
        f"/cooperatives/{cooperative['id']}",
        json={"moolre_account_number": "COOP-DUES-777"},
    )

    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tr099_result("coop-dues-ref")

        resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 10.0, "channel": "13"},
        )

    assert resp.status_code == 200
    assert mock_pay.call_args.kwargs["account_number"] == "COOP-DUES-777"


def test_initiate_payment_rejects_missing_moolre_user(monkeypatch):
    import asyncio

    from app.config import get_settings
    from app.services.moolre_service import MoolreService

    monkeypatch.setenv("MOOLRE_API_USER", "")
    get_settings.cache_clear()
    service = MoolreService()
    result = asyncio.run(
        service.initiate_payment(payer_phone="0551000001", amount=1.0, external_ref="cfg-test")
    )
    get_settings.cache_clear()
    assert result["outcome"] == "failed"
    assert "MOOLRE_API_USER" in result["message"]


def test_collect_dues_tp14_verification_required(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tp14_result("test-ref-tp14")

        resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 10.0, "channel": "13"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verification_required"
    assert data["outcome"] == "verification_required"
    assert data["moolre_code"] == "TP14"
    assert data["transaction_id"]
    assert data["moolre_reference"]
    assert data["customer_action"] == "otp"
    assert data["action_expires_at"]

    tx_resp = client.get(f"/transactions/{data['transaction_id']}")
    assert tx_resp.status_code == 200
    assert tx_resp.json()["status"] == "pending"


def test_collect_dues_tr099_pending(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tr099_result("test-ref-tr099")

        resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 25.0},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["outcome"] == "push_sent"
    assert data["moolre_code"] == "TR099"
    assert data["customer_action"] == "approval"


def test_dashboard_collect_is_idempotent_while_member_action_is_pending(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        return_value=_tp14_result("idempotent-ref"),
    ) as mock_pay:
        first = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 30},
        )
        repeated = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 30},
        )
        changed = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 31},
        )

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json()["transaction_id"] == first.json()["transaction_id"]
    assert changed.status_code == 409
    mock_pay.assert_called_once()


def test_ambiguous_dues_initiation_preserves_reference_and_blocks_retry(
    client, farmer, db
):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        side_effect=RuntimeError("provider timeout"),
    ) as mock_pay:
        with pytest.raises(RuntimeError, match="provider timeout"):
            client.post(
                "/transactions/dues/collect",
                json={"farmer_id": farmer["id"], "amount": 30},
            )
        repeated = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 30},
        )

    tx = db.query(Transaction).filter(
        Transaction.farmer_id == farmer["id"],
        Transaction.transaction_type == TransactionType.dues,
    ).one()
    assert repeated.status_code == 200
    assert repeated.json()["transaction_id"] == tx.id
    assert tx.status == TransactionStatus.pending
    assert tx.customer_action == "initiating"
    assert tx.action_expires_at is not None
    mock_pay.assert_called_once()


def test_expired_customer_action_becomes_terminal_on_dashboard_read(
    client, farmer, cooperative, db
):
    tx = Transaction(
        farmer_id=farmer["id"],
        transaction_type=TransactionType.dues,
        amount=20,
        status=TransactionStatus.pending,
        moolre_reference="expired-action-ref",
        customer_action="otp",
        action_expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    db.add(tx)
    db.commit()

    response = client.get(
        f"/transactions/?cooperative_id={cooperative['id']}"
    )

    assert response.status_code == 200
    row = next(item for item in response.json() if item["id"] == tx.id)
    assert row["status"] == "failed"
    assert row["customer_action"] == "expired"


def test_collect_dues_moolre_failure(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _failed_result("test-ref-fail")

        resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 5.0},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["outcome"] == "failed"


def test_farmer_resumes_dashboard_dues_otp_from_ussdk(client, farmer, db):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tp14_result("verify-ref-001")

        collect_resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 15.0},
        )
        tx_id = collect_resp.json()["transaction_id"]
        ext_ref = collect_resp.json()["moolre_reference"]

        mock_pay.return_value = _tr099_result(ext_ref)
        mock_pay.reset_mock()

        list_resp = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": farmer["phone"]},
                    "values": {},
                },
            },
        )
        assert list_resp.json()["payments"][0]["transaction_id"] == tx_id

        verify_resp = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": farmer["phone"]},
                    "values": {
                        "transaction_id": tx_id,
                        "otp_code": "123456",
                    },
                },
            },
        )

    assert verify_resp.status_code == 200
    assert verify_resp.json()["action"] == "end"
    transaction = db.query(Transaction).filter(Transaction.id == tx_id).one()
    assert transaction.status == TransactionStatus.pending
    assert transaction.customer_action == "approval"

    mock_pay.assert_called_once()
    call_kwargs = mock_pay.call_args.kwargs
    assert call_kwargs["otpcode"] == "123456"
    assert call_kwargs["external_ref"] == ext_ref


def test_otp_attempt_is_claimed_before_provider_call(client, farmer, db):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tp14_result("claimed-otp-ref")
        collect = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 15},
        )
        tx_id = collect.json()["transaction_id"]

        mock_pay.side_effect = RuntimeError("provider timeout")
        first = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": farmer["phone"]},
                    "values": {"transaction_id": tx_id, "otp_code": "123456"},
                },
            },
        )
        second = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": farmer["phone"]},
                    "values": {"transaction_id": tx_id, "otp_code": "123456"},
                },
            },
        )

    tx = db.query(Transaction).filter(Transaction.id == tx_id).one()
    assert first.json()["action"] == "end"
    assert second.json()["action"] == "end"
    assert "already being processed" in second.json()["message"]
    assert tx.status == TransactionStatus.pending
    assert tx.customer_action == "processing_otp"
    assert mock_pay.call_count == 2


def test_pending_payment_cannot_be_resumed_by_another_phone(
    client, farmer, cooperative
):
    other = client.post(
        "/farmers/",
        json={
            "name": "Other Member",
            "phone": "0247778899",
            "cooperative_id": cooperative["id"],
        },
    ).json()
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
        return_value=_tp14_result("phone-scope-ref"),
    ) as mock_pay:
        collect = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 15},
        )
        response = client.post(
            "/ussdk/pending-payment",
            json={
                "input": {},
                "props": {
                    "session": {"msisdn": other["phone"]},
                    "values": {
                        "transaction_id": collect.json()["transaction_id"],
                        "otp_code": "123456",
                    },
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Pending payment not found."
    mock_pay.assert_called_once()


def test_admin_dues_otp_endpoint_is_removed(client):
    resp = client.post(
        "/transactions/dues/collect/verify",
        json={"transaction_id": 999999, "otp_code": "123456"},
    )
    assert resp.status_code == 404


def test_initiate_payment_tp14_not_success():
    """Unit test: TP14 with status=1 must not be treated as push success."""
    import asyncio

    from app.services.moolre_service import MoolreService

    service = MoolreService()

    async def fake_post(path, payload, headers=None):
        return {
            "status": 1,
            "code": "TP14",
            "message": "Please complete the verification process sent to you via SMS and try again.",
            "data": payload["externalref"],
        }

    with patch.object(service, "_post", new=fake_post):
        result = asyncio.run(
            service.initiate_payment(payer_phone="233551000001", amount=1.0, external_ref="otp-test-ref")
        )

    assert result["outcome"] == "verification_required"
    assert result["success"] is False
    assert result["moolre_code"] == "TP14"


def test_initiate_payment_tp14_field_name_echo_not_used_as_reference():
    """Regression test: Moolre's TP14 response can echo a field name (e.g. 'otpcode')
    in the 'data' field instead of a real reference. That must never be stored as
    moolre_reference — it isn't unique across requests and previously caused an
    IntegrityError on the second OTP attempt when reused across transactions."""
    import asyncio

    from app.services.moolre_service import MoolreService

    service = MoolreService()

    async def fake_post(path, payload, headers=None):
        return {
            "status": 1,
            "code": "TP14",
            "message": "Please complete the verification process sent to you via SMS and try again.",
            "data": "otpcode",  # field-name echo, NOT a real reference
        }

    with patch.object(service, "_post", new=fake_post):
        result = asyncio.run(
            service.initiate_payment(payer_phone="233551000001", amount=1.0, external_ref="otp-echo-ref")
        )

    assert result["verification_required"] is True
    # Must fall back to the real external_ref, never the echoed field name.
    assert result["moolre_reference"] == "otp-echo-ref"
    assert result["moolre_reference"] != "otpcode"


def test_initiate_payment_includes_otpcode_in_payload():
    import asyncio

    from app.services.moolre_service import MoolreService

    service = MoolreService()
    captured = {}

    async def fake_post(path, payload, headers=None):
        captured.update(payload)
        return {"status": 1, "code": "TR099", "message": "OK", "data": payload["externalref"]}

    with patch.object(service, "_post", new=fake_post):
        asyncio.run(
            service.initiate_payment(
                payer_phone="233551000001",
                amount=1.0,
                external_ref="otp-payload-ref",
                otpcode="654321",
            )
        )

    assert captured.get("otpcode") == "654321"
    assert captured.get("externalref") == "otp-payload-ref"
