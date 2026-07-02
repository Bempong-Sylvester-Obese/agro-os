"""Tests for MoolreService header construction."""

from app.services.moolre_service import MoolreService


def test_live_headers_include_pubkey(monkeypatch) -> None:
    monkeypatch.setenv("MOOLRE_ENV", "live")
    monkeypatch.setenv("MOOLRE_API_USER", "live-user")
    monkeypatch.setenv("MOOLRE_API_KEY", "live-key")
    monkeypatch.setenv("MOOLRE_API_PUBKEY", "live-pubkey")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        service = MoolreService()
        headers = service._build_base_headers()
        assert headers["X-API-USER"] == "live-user"
        assert headers["X-API-KEY"] == "live-key"
        assert headers["X-API-PUBKEY"] == "live-pubkey"
    finally:
        get_settings.cache_clear()


def test_sandbox_headers_omit_pubkey(monkeypatch) -> None:
    monkeypatch.setenv("MOOLRE_ENV", "sandbox")
    monkeypatch.setenv("MOOLRE_API_USER", "sandbox-user")
    monkeypatch.setenv("MOOLRE_API_KEY", "sandbox-key")
    monkeypatch.setenv("MOOLRE_API_PUBKEY", "should-not-appear")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        service = MoolreService()
        headers = service._build_base_headers()
        assert "X-API-PUBKEY" not in headers
    finally:
        get_settings.cache_clear()
