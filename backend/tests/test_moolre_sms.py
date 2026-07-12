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
async def test_send_sms_includes_account_number(mock_post, monkeypatch):
    monkeypatch.setenv("MOOLRE_API_VASKEY", "test-vas-key")
    monkeypatch.setenv("MOOLRE_ACCOUNT_NUMBER", "ACC-12345")
    from app.config import get_settings

    get_settings.cache_clear()
    mock_post.return_value = {"status": 1, "message": "Queued"}
    service = MoolreService()
    await service.send_sms([{"recipient": "+233244123456", "message": "Hello"}])
    get_settings.cache_clear()

    payload = mock_post.call_args[0][1]
    assert payload["accountnumber"] == "ACC-12345"
    assert payload["messages"][0]["recipient"] == "0244123456"
