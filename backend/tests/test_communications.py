"""Tests for /communications endpoints"""

import asyncio
from unittest.mock import AsyncMock, patch

from app.models.models import CooperativeMembership
from app.services.communications_service import CommunicationsService


def _mock_sms_success(*_args, **_kwargs):
    return {"success": True, "message": "SMS queued", "raw": {"data": "ref-123"}}


@patch(
    "app.services.communications_service.MoolreService.send_sms",
    new_callable=AsyncMock,
    side_effect=_mock_sms_success,
)
def test_broadcast_sms(mock_send, client, cooperative, farmer):
    resp = client.post(
        "/communications/sms/broadcast",
        json={
            "cooperative_id": cooperative["id"],
            "message": "Meeting tomorrow at 10AM.",
            "sent_by": "admin",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["recipients_count"] == 1
    assert data["log_id"] is not None
    mock_send.assert_awaited_once()


@patch(
    "app.services.communications_service.MoolreService.send_sms",
    new_callable=AsyncMock,
    side_effect=_mock_sms_success,
)
def test_send_dues_reminder(mock_send, client, cooperative, farmer):
    resp = client.post(
        "/communications/sms/dues-reminder",
        json={
            "cooperative_id": cooperative["id"],
            "amount": 120.0,
            "due_date": "30 June 2026",
            "sent_by": "admin",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["recipients_count"] == 1
    mock_send.assert_awaited_once()
    message = mock_send.await_args.args[0][0]["message"]
    assert "Dial *919*4020# and choose Pay Cooperative Dues" in message
    assert "*203*" not in message


def test_payment_action_sms_uses_agroos_ussd_code(db, farmer):
    member = (
        db.query(CooperativeMembership)
        .filter(CooperativeMembership.id == farmer["id"])
        .one()
    )
    with patch(
        "app.services.communications_service.MoolreService.send_single_sms",
        new_callable=AsyncMock,
        return_value={"success": True, "message": "SMS queued", "raw": {}},
    ) as mock_send:
        asyncio.run(
            CommunicationsService().send_payment_action_required(
                farmer=member,
                amount=3,
                reference="payment-action-ref",
                db=db,
            )
        )

    message = mock_send.await_args.kwargs["message"]
    assert "Dial *919*4020# and choose Complete Pending Payment" in message
    assert "*203*" not in message


def test_broadcast_cooperative_not_found(client):
    resp = client.post(
        "/communications/sms/broadcast",
        json={"cooperative_id": 99999, "message": "Hello"},
    )
    assert resp.status_code == 404


@patch(
    "app.services.communications_service.MoolreService.send_sms",
    new_callable=AsyncMock,
    side_effect=_mock_sms_success,
)
def test_list_communication_logs(mock_send, client, cooperative, farmer):
    client.post(
        "/communications/sms/broadcast",
        json={
            "cooperative_id": cooperative["id"],
            "message": "Test broadcast",
        },
    )

    resp = client.get(f"/communications/logs?cooperative_id={cooperative['id']}")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["body"] == "Test broadcast"
    assert logs[0]["recipients_count"] == 1


@patch(
    "app.services.communications_service.MoolreService.send_sms",
    new_callable=AsyncMock,
)
def test_broadcast_sms_moolre_failure_returns_502(mock_send, client, cooperative, farmer):
    mock_send.return_value = {
        "success": False,
        "message": "Authentication Error, authentication information is required",
        "raw": {},
    }
    resp = client.post(
        "/communications/sms/broadcast",
        json={
            "cooperative_id": cooperative["id"],
            "message": "Meeting tomorrow.",
        },
    )
    assert resp.status_code == 502
    assert "Authentication Error" in resp.json()["detail"]
