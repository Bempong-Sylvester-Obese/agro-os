"""Cross-gateway parity: the same menu path yields the same outcome on every stateful gateway.

Moolre posts JSON per keystroke; Africa's Talking posts form data with the cumulative
``text``. Both must reach the same UssdApplicationService state and produce the same
message text and continue/end decision. (USSDK exposes action hooks rather than a menu
and is covered by ``test_ussdk_hooks.py``.)
"""
import pytest

from app.models.models import Cooperative, CooperativeMembership, Farmer
from app.services.ussd_application import (
    LINK_COOP_CODE_PROMPT,
    LINK_FARMER_CODE_PROMPT,
    LINK_SUCCESS_MSG,
    NOT_REGISTERED_MSG,
    USSD_MAIN_MENU,
)


class MoolreGateway:
    name = "moolre"

    def __init__(self, client):
        self.client = client

    def drive(self, session_id: str, phone: str, inputs: list[str]) -> tuple[str, bool]:
        body = {"sessionId": session_id, "new": True, "msisdn": phone, "network": 3, "message": "", "extension": "109", "data": ""}
        resp = self.client.post("/webhooks/moolre/ussd", json=body).json()
        for message in inputs:
            body = {**body, "new": False, "message": message}
            resp = self.client.post("/webhooks/moolre/ussd", json=body).json()
        return resp["message"], bool(resp["reply"])


class AfricasTalkingGateway:
    name = "africas_talking"

    def __init__(self, client):
        self.client = client

    def _post(self, session_id: str, phone: str, text: str) -> tuple[str, bool]:
        resp = self.client.post(
            "/ussd/callback",
            data={"sessionId": session_id, "serviceCode": "*123#", "phoneNumber": phone, "text": text},
        )
        assert resp.status_code == 200, resp.text
        prefix, _, message = resp.text.partition(" ")
        assert prefix in ("CON", "END")
        return message, prefix == "CON"

    def drive(self, session_id: str, phone: str, inputs: list[str]) -> tuple[str, bool]:
        result = self._post(session_id, phone, "")
        for index in range(len(inputs)):
            result = self._post(session_id, phone, "*".join(inputs[: index + 1]))
        return result


GATEWAYS = [MoolreGateway, AfricasTalkingGateway]


@pytest.fixture(params=GATEWAYS, ids=lambda g: g.name)
def gateway(request, client):
    return request.param(client)


def test_new_session_shows_shared_main_menu(gateway):
    message, cont = gateway.drive(f"{gateway.name}-menu", "+233000000000", [])
    assert message == USSD_MAIN_MENU
    assert cont is True


def test_unregistered_phone_gets_not_registered_on_finance_options(gateway):
    for option in ("1", "2", "3", "6"):
        message, cont = gateway.drive(f"{gateway.name}-unreg-{option}", "+233000000000", [option])
        assert message == NOT_REGISTERED_MSG
        assert cont is False


def test_registered_farmer_sees_loan_balance(gateway, farmer):
    message, cont = gateway.drive(f"{gateway.name}-bal", farmer["phone"], ["1"])
    assert "Kofi Mensah" in message
    assert "no active loans" in message
    assert cont is False


def test_pay_dues_prompts_for_amount(gateway, farmer):
    message, cont = gateway.drive(f"{gateway.name}-dues", farmer["phone"], ["2"])
    assert message == "Enter amount to pay (GHS):"
    assert cont is True


def test_invalid_option_re_shows_menu(gateway):
    message, cont = gateway.drive(f"{gateway.name}-bad", "+233551111111", ["9"])
    assert message.startswith("Invalid option.")
    assert USSD_MAIN_MENU in message
    assert cont is True


def test_link_phone_flow_links_membership_on_every_gateway(gateway, db, cooperative):
    coop = db.get(Cooperative, cooperative["id"])
    coop.ussd_code = "4321" if gateway.name == "moolre" else "8765"
    person = Farmer(name="Ama Linkable", phone=f"+23355{'1' if gateway.name == 'moolre' else '2'}999000")
    db.add(person)
    db.flush()
    membership = CooperativeMembership(
        farmer_id=person.id,
        cooperative_id=coop.id,
        farmer_code="654321",
    )
    db.add(membership)
    db.commit()

    new_phone = f"+23320{'1' if gateway.name == 'moolre' else '2'}000111"

    prompt, cont = gateway.drive(f"{gateway.name}-link-1", new_phone, ["7"])
    assert (prompt, cont) == (LINK_COOP_CODE_PROMPT, True)

    prompt, cont = gateway.drive(f"{gateway.name}-link-2", new_phone, ["7", coop.ussd_code])
    assert (prompt, cont) == (LINK_FARMER_CODE_PROMPT, True)

    done, cont = gateway.drive(f"{gateway.name}-link-3", new_phone, ["7", coop.ussd_code, "654321"])
    assert (done, cont) == (LINK_SUCCESS_MSG, False)

    db.refresh(person)
    assert person.phone == new_phone


def test_link_phone_rejects_bad_cooperative_code(gateway):
    message, cont = gateway.drive(f"{gateway.name}-link-bad", "+233209999999", ["7", "0000"])
    assert message == "Invalid Cooperative Code. Please try again."
    assert cont is False


def test_link_phone_on_already_linked_phone_ends(gateway, farmer):
    message, cont = gateway.drive(f"{gateway.name}-link-dup", farmer["phone"], ["7"])
    assert "already linked" in message
    assert cont is False
