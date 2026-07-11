"""Tests for /communications endpoints"""

from unittest.mock import AsyncMock, patch


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
