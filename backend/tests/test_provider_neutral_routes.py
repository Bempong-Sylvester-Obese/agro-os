"""
Provider-neutral route aliases (#228).

The public API surface must not be named after one vendor. Canonical paths are
``/webhooks/payment``, ``/webhooks/ussd`` and ``/transactions/provider/*``; the
``/webhooks/moolre/*`` and ``/transactions/moolre/*`` paths remain as hidden
aliases so callbacks registered before the rename keep working.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.middleware.rate_limit import rate_limiter
from main import _PUBLIC_PATHS, app


@pytest.fixture(autouse=True)
def _isolated_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()
    get_settings.cache_clear()


def _payment_payload(reference: str) -> dict:
    return {
        "status": 1,
        "code": "P01",
        "message": "Transaction Successful",
        "data": {
            "transactionid": f"TX-{reference}",
            "externalref": reference,
            "amount": "10.00",
            "payer": "233551300186",
        },
    }


def _ussd_new(session_id: str, msisdn: str) -> dict:
    return {
        "sessionId": session_id,
        "new": True,
        "msisdn": msisdn,
        "network": "MTN",
        "message": "",
        "extension": "",
        "data": "",
    }


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------


def _iter_api_routes(router):
    """Yield concrete API routes, descending into nested included routers.

    Newer FastAPI wraps ``include_router`` targets in an ``_IncludedRouter``
    that exposes the source ``APIRouter`` as ``original_router``.
    """
    for route in router.routes:
        if getattr(route, "methods", None) and hasattr(route, "include_in_schema"):
            yield route
        nested = getattr(route, "original_router", None) or (
            route if hasattr(route, "routes") else None
        )
        if nested is not None:
            yield from _iter_api_routes(nested)


def _paths_for(method: str) -> dict[str, bool]:
    """Map path -> include_in_schema for routes accepting ``method``."""
    return {
        route.path: route.include_in_schema
        for route in _iter_api_routes(app.router)
        if method in route.methods
    }


def test_neutral_paths_are_canonical_and_legacy_paths_are_hidden_aliases():
    posts = _paths_for("POST")
    gets = _paths_for("GET")

    assert posts["/webhooks/payment"] is True
    assert posts["/webhooks/ussd"] is True
    assert posts["/webhooks/moolre/payment"] is False
    assert posts["/webhooks/moolre/ussd"] is False

    assert gets["/transactions/provider/account-transactions"] is True
    assert gets["/transactions/provider/wallet-balance"] is True
    assert gets["/transactions/moolre/account-transactions"] is False
    assert gets["/transactions/moolre/wallet-balance"] is False


def test_configured_callback_path_resolves_to_a_route():
    """The URL we register with the provider must be served by the app."""
    settings = get_settings()
    assert settings.webhook_callback_path in _paths_for("POST")
    assert settings.webhook_callback_path in _PUBLIC_PATHS


def test_no_public_openapi_path_is_provider_named():
    schema = app.openapi()
    vendor_named = [p for p in schema["paths"] if "moolre" in p.lower()]
    assert vendor_named == []


# ---------------------------------------------------------------------------
# Webhooks: neutral and legacy paths behave identically
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/webhooks/payment", "/webhooks/moolre/payment"])
def test_payment_webhook_paths_accept_events(client, db, path):
    from app.models.models import PaymentWebhookEvent

    reference = f"NEUTRAL-{path.count('/')}-XYZ"
    resp = client.post(path, json=_payment_payload(reference))
    assert resp.status_code == 200
    assert "acknowledged" in resp.json()["message"]

    recorded = (
        db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.provider_payment_ref == reference)
        .first()
    )
    assert recorded is not None


@pytest.mark.parametrize("path", ["/webhooks/ussd", "/webhooks/moolre/ussd"])
def test_ussd_webhook_paths_serve_the_menu(client, path):
    resp = client.post(path, json=_ussd_new(f"sess-{path}", "+233000000000"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] is True
    assert "1. Check Loan Balance" in body["message"]


@pytest.mark.parametrize(
    "path",
    ["/webhooks/payment", "/webhooks/ussd", "/webhooks/moolre/payment", "/webhooks/moolre/ussd"],
)
def test_webhook_paths_are_public_when_auth_enabled(client, monkeypatch, path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-auth-boundary-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-auth-boundary-password")
    get_settings.cache_clear()
    try:
        assert path in _PUBLIC_PATHS
        resp = client.post(path, content=b"{}")
        assert resp.status_code != 401
    finally:
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()


@pytest.mark.parametrize("path", ["/webhooks/payment", "/webhooks/ussd"])
def test_neutral_webhook_paths_share_the_webhook_rate_limit(client, monkeypatch, path):
    monkeypatch.setenv("RATE_LIMIT_WEBHOOK_PER_MINUTE", "2")
    get_settings.cache_clear()

    for _ in range(2):
        response = client.post(path, content=b"not-json")
        assert response.status_code in (400, 422)

    limited = client.post(path, content=b"not-json")
    assert limited.status_code == 429
    assert "Retry-After" in limited.headers


# ---------------------------------------------------------------------------
# Transactions: provider-neutral wallet endpoints
# ---------------------------------------------------------------------------


def test_provider_wallet_endpoints_match_legacy_aliases(client, db, demo_admin, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "strong-auth-boundary-test-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-auth-boundary-password")
    from app.models.models import Cooperative
    from app.services.auth_service import create_access_token

    cooperative = db.query(Cooperative).filter(
        Cooperative.id == demo_admin.cooperative_id
    ).one()
    cooperative.wallet_account_id = "TENANT-WALLET-NEUTRAL"
    db.commit()
    get_settings.cache_clear()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': demo_admin.email})}"}

    try:
        with (
            patch(
                "app.services.providers.moolre_adapter.MoolrePaymentAdapter.account_status",
                new_callable=AsyncMock,
                return_value={"success": True, "balance": "5.00"},
            ),
            patch(
                "app.services.providers.moolre_adapter.MoolrePaymentAdapter.list_transactions",
                new_callable=AsyncMock,
                return_value={"success": True, "transactions": []},
            ),
        ):
            neutral_balance = client.get("/transactions/provider/wallet-balance", headers=headers)
            legacy_balance = client.get("/transactions/moolre/wallet-balance", headers=headers)
            neutral_list = client.get(
                "/transactions/provider/account-transactions", headers=headers
            )
            legacy_list = client.get(
                "/transactions/moolre/account-transactions", headers=headers
            )
    finally:
        monkeypatch.setenv("AUTH_ENABLED", "false")
        get_settings.cache_clear()

    assert neutral_balance.status_code == legacy_balance.status_code == 200
    assert neutral_balance.json() == legacy_balance.json()
    assert neutral_list.status_code == legacy_list.status_code == 200
    assert neutral_list.json() == legacy_list.json()
