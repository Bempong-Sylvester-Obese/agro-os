"""Operational health endpoint tests."""

from unittest.mock import MagicMock

import main


def test_health_live_returns_process_status(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_reports_database_and_model(client, monkeypatch):
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    monkeypatch.setattr(main.engine, "connect", lambda: context)

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"
    assert payload["model_source"] in {"artifact", "synthetic"}
    assert payload["model_ready"] is True
    connection.execute.assert_called_once()


def test_health_ready_returns_503_when_database_is_unavailable(client, monkeypatch):
    def fail_connect():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main.engine, "connect", fail_connect)

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database"] == "fail"
    assert "model_source" in payload

