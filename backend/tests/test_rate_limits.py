"""Route-specific abuse protection tests."""

import pytest

from app.config import get_settings
from app.middleware.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def isolated_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()
    get_settings.cache_clear()


def test_login_limit_returns_429_and_retry_after(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_MINUTE", "2")
    get_settings.cache_clear()

    for _ in range(2):
        response = client.post(
            "/auth/login",
            json={"email": "missing@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1


def test_webhook_limit_allows_provider_retries_then_limits(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_WEBHOOK_PER_MINUTE", "2")
    get_settings.cache_clear()

    for _ in range(2):
        response = client.post("/webhooks/moolre/payment", content=b"not-json")
        assert response.status_code == 400

    limited = client.post("/webhooks/moolre/payment", content=b"not-json")
    assert limited.status_code == 429
    assert "Retry-After" in limited.headers


def test_health_endpoints_are_exempt(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LOGIN_PER_MINUTE", "1")
    get_settings.cache_clear()

    for _ in range(5):
        assert client.get("/health/live").status_code == 200

