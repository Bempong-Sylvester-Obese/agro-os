"""Tests for /transactions/dues/collect and /transactions/dues/collect/verify"""

from unittest.mock import AsyncMock, patch

from app.models.models import Transaction, TransactionStatus


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


def test_verify_dues_collect_with_otp(client, farmer):
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

        verify_resp = client.post(
            "/transactions/dues/collect/verify",
            json={"transaction_id": tx_id, "otp_code": "123456"},
        )

    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["status"] == "pending"
    assert data["outcome"] == "push_sent"
    assert data["moolre_code"] == "TR099"
    assert data["transaction_id"] == tx_id

    mock_pay.assert_called_once()
    call_kwargs = mock_pay.call_args.kwargs
    assert call_kwargs["otpcode"] == "123456"
    assert call_kwargs["external_ref"] == ext_ref


def test_verify_dues_collect_not_found(client):
    resp = client.post(
        "/transactions/dues/collect/verify",
        json={"transaction_id": 999999, "otp_code": "123456"},
    )
    assert resp.status_code == 404


def test_verify_dues_collect_not_pending(client, farmer, db):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tr099_result("completed-ref")

        collect_resp = client.post(
            "/transactions/dues/collect",
            json={"farmer_id": farmer["id"], "amount": 10.0},
        )
        tx_id = collect_resp.json()["transaction_id"]

    transaction = db.query(Transaction).filter(Transaction.id == tx_id).one()
    transaction.status = TransactionStatus.completed
    db.commit()

    verify_resp = client.post(
        "/transactions/dues/collect/verify",
        json={"transaction_id": tx_id, "otp_code": "123456"},
    )
    assert verify_resp.status_code == 409


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
