"""Tests for /ussdk/loan-balance and /ussdk/pay-dues"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def _tp14_result(ext_ref: str) -> dict:
    return {
        "success": False,
        "outcome": "verification_required",
        "moolre_code": "TP14",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": (
            "Please complete the verification process sent to you via SMS "
            "and try again."
        ),
    }


def _tr099_result(ext_ref: str) -> dict:
    return {
        "success": True,
        "outcome": "push_sent",
        "moolre_code": "TR099",
        "moolre_reference": ext_ref,
        "external_ref": ext_ref,
        "message": "Payment request sent",
    }


def _hook_payload(msisdn: str, values: dict | None = None) -> dict:
    return {
        "input": {},
        "props": {
            "session": {"msisdn": msisdn, "network": "mtn"},
            "values": values or {},
        },
    }


def test_ussdk_hooks_fail_closed_without_production_secret(client):
    with patch(
        "app.routes.ussdk_hooks.get_settings",
        return_value=SimpleNamespace(
            ussdk_hook_secret="",
            app_env="production",
        ),
    ):
        response = client.post(
            "/ussdk/loan-request",
            json=_hook_payload(
                "0240000000",
                {"amount": "100", "purpose": "Seed"},
            ),
        )

    assert response.status_code == 401


def test_pay_dues_unregistered_phone_ends_session(client):
    resp = client.post(
        "/ussdk/pay-dues",
        json=_hook_payload("0200000000", {"amount": "5"}),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "end"
    assert "not registered" in body["message"]


def test_pay_dues_missing_amount_returns_retry(client, farmer):
    resp = client.post(
        "/ussdk/pay-dues",
        json=_hook_payload(farmer["phone"], {}),
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "retry"


def test_pay_dues_success_prompts_phone_approval(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tr099_result("ussd-ref-1")

        resp = client.post(
            "/ussdk/pay-dues",
            json=_hook_payload(farmer["phone"], {"amount": "5"}),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_required"] is False
    assert "phone" in body["message"].lower()


def test_pay_dues_otp_required_returns_external_ref_for_retry(client, farmer):
    with patch(
        "app.routes.transactions.MoolreService.initiate_payment",
        new_callable=AsyncMock,
    ) as mock_pay:
        mock_pay.return_value = _tp14_result("ussd-ref-2")

        resp = client.post(
            "/ussdk/pay-dues",
            json=_hook_payload(farmer["phone"], {"amount": "5"}),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_required"] is True
    assert body["external_ref"]


def test_loan_balance_unregistered_phone(client):
    resp = client.post(
        "/ussdk/loan-balance",
        json=_hook_payload("0200000000"),
    )
    assert resp.status_code == 200
    assert resp.json()["registered"] is False


def test_loan_balance_registered_farmer_no_loans(client, farmer):
    resp = client.post(
        "/ussdk/loan-balance",
        json=_hook_payload(farmer["phone"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["registered"] is True
    assert body["balance"] == 0


def test_farmer_can_request_loan_from_ussdk(client, farmer, db):
    from app.models.models import Loan

    resp = client.post(
        "/ussdk/loan-request",
        json=_hook_payload(
            farmer["phone"],
            {"amount": "500", "purpose": "Irrigation pump"},
        ),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "end"
    assert body["status"] == "requested"
    loan = db.query(Loan).filter(Loan.id == body["loan_id"]).one()
    assert loan.farmer_id == farmer["id"]
    assert loan.request_channel == "ussdk"


def test_ussdk_loan_request_handles_unregistered_and_multiple_memberships(
    client, farmer
):
    unregistered = client.post(
        "/ussdk/loan-request",
        json=_hook_payload(
            "0200000000",
            {"amount": "100", "purpose": "Seed"},
        ),
    )
    assert unregistered.json()["action"] == "end"
    assert "not registered" in unregistered.json()["message"].lower()

    second_coop = client.post(
        "/cooperatives/",
        json={"name": "Loan Request Cooperative", "currency": "GHS"},
    ).json()
    client.post(
        "/farmers/",
        json={
            "name": farmer["name"],
            "phone": farmer["phone"],
            "cooperative_id": second_coop["id"],
        },
    )
    choose = client.post(
        "/ussdk/loan-request",
        json=_hook_payload(
            farmer["phone"],
            {"amount": "100", "purpose": "Seed"},
        ),
    )
    assert choose.json()["requires_cooperative_selection"] is True
    assert len(choose.json()["cooperatives"]) == 2


def test_ussdk_loan_request_validates_input_and_pending_request(client, farmer):
    invalid = client.post(
        "/ussdk/loan-request",
        json=_hook_payload(farmer["phone"], {"amount": "0", "purpose": ""}),
    )
    assert invalid.json()["action"] == "retry"

    payload = _hook_payload(
        farmer["phone"],
        {"amount": "100", "purpose": "Seed"},
    )
    first = client.post("/ussdk/loan-request", json=payload)
    assert first.json()["status"] == "requested"

    duplicate = client.post("/ussdk/loan-request", json=payload)
    assert duplicate.json()["action"] == "end"
    assert "already awaiting review" in duplicate.json()["message"].lower()


def test_multiple_memberships_require_cooperative_selection(client, farmer):
    second_coop = client.post(
        "/cooperatives/",
        json={"name": "Second USSD Cooperative", "currency": "GHS"},
    ).json()
    second_membership = client.post(
        "/farmers/",
        json={
            "name": farmer["name"],
            "phone": farmer["phone"],
            "cooperative_id": second_coop["id"],
        },
    ).json()

    choose_resp = client.post(
        "/ussdk/loan-balance",
        json=_hook_payload(farmer["phone"]),
    )
    assert choose_resp.status_code == 200
    choose_body = choose_resp.json()
    assert choose_body["requires_cooperative_selection"] is True
    assert len(choose_body["cooperatives"]) == 2

    selected_resp = client.post(
        "/ussdk/loan-balance",
        json=_hook_payload(
            farmer["phone"],
            {"membership_id": second_membership["id"]},
        ),
    )
    assert selected_resp.status_code == 200
    assert selected_resp.json()["registered"] is True


def test_rejects_membership_selection_owned_by_another_phone(client, farmer):
    other_coop = client.post(
        "/cooperatives/",
        json={"name": "Other Phone Cooperative", "currency": "GHS"},
    ).json()
    other_member = client.post(
        "/farmers/",
        json={
            "name": "Different Farmer",
            "phone": "0249999999",
            "cooperative_id": other_coop["id"],
        },
    ).json()

    resp = client.post(
        "/ussdk/loan-balance",
        json=_hook_payload(
            farmer["phone"],
            {"membership_id": other_member["id"]},
        ),
    )
    assert resp.status_code == 200
    assert resp.json()["registered"] is False


def test_wallet_balance_unregistered_phone_ends_session(client):
    resp = client.post(
        "/ussdk/wallet-balance",
        json=_hook_payload("0200000000"),
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "end"


def test_wallet_balance_success(client, farmer):
    with patch(
        "app.routes.ussdk_hooks.MoolreService.account_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.return_value = {
            "success": True,
            "balance": "1250.00",
            "account_name": "Test Cooperative",
        }
        resp = client.post(
            "/ussdk/wallet-balance",
            json=_hook_payload(farmer["phone"]),
        )

    assert resp.status_code == 200
    assert "1250.00" in resp.json()["message"]


def test_wallet_balance_moolre_failure_ends_session(client, farmer):
    with patch(
        "app.routes.ussdk_hooks.MoolreService.account_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.return_value = {"success": False}
        resp = client.post(
            "/ussdk/wallet-balance",
            json=_hook_payload(farmer["phone"]),
        )

    assert resp.status_code == 200
    assert resp.json()["action"] == "end"


def test_announcements_unregistered_phone_still_answers(client):
    resp = client.post(
        "/ussdk/announcements",
        json=_hook_payload("0200000000"),
    )
    assert resp.status_code == 200
    assert "No new announcements" in resp.json()["message"]


def test_announcements_sends_sms_for_registered_farmer(client, farmer):
    with patch(
        "app.routes.ussdk_hooks.MoolreService.send_single_sms",
        new_callable=AsyncMock,
    ) as mock_sms:
        mock_sms.return_value = {"success": True}
        resp = client.post(
            "/ussdk/announcements",
            json=_hook_payload(farmer["phone"]),
        )

    assert resp.status_code == 200
    mock_sms.assert_called_once()
    assert "SMS" in resp.json()["message"]
