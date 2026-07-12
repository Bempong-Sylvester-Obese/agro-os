"""Tests for Moolre SMS configuration and phone normalization."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.moolre_service import MoolreService


@pytest.mark.asyncio
async def test_send_sms_requires_vaskey(monkeypatch):
    monkeypatch.setenv("MOOLRE_API_VASKEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    service = MoolreService()
    result = await service.send_sms([{"recipient": "0244123456", "message": "Hi"}])
    get_settings.cache_clear()
    assert result["success"] is False
    assert "MOOLRE_API_VASKEY" in result["message"]


@pytest.mark.asyncio
@patch.object(MoolreService, "_post", new_callable=AsyncMock)
async def test_send_sms_uses_vas_headers_only(mock_post, monkeypatch):
    monkeypatch.setenv("MOOLRE_API_VASKEY", "test-vas-key")
    monkeypatch.setenv("MOOLRE_API_KEY", "test-api-key")
    monkeypatch.setenv("MOOLRE_API_PUBKEY", "test-pub-key")
    monkeypatch.setenv("DEFAULT_SMS_SENDER_ID", "AgroOs")
    from app.config import get_settings

    get_settings.cache_clear()
    mock_post.return_value = {"status": 1, "message": "Success", "code": "SMS01"}
    service = MoolreService()
    await service.send_sms([{"recipient": "+233244123456", "message": "Hello"}])
    get_settings.cache_clear()

    payload = mock_post.call_args[0][1]
    headers = mock_post.call_args[1]["headers"]
    assert "accountnumber" not in payload
    assert payload["messages"][0]["recipient"] == "0244123456"
    assert headers["X-API-VASKEY"] == "test-vas-key"
    assert "X-API-USER" in headers
    assert "X-API-KEY" not in headers
    assert "X-API-PUBKEY" not in headers


def test_format_sms_error_includes_vas_hint():
    message = MoolreService.format_sms_error("AIN01", "Authentication Error", "AgroOs")
    assert "MOOLRE_API_VASKEY" in message
    assert "Authentication Error" in message
