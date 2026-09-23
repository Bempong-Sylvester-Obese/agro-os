"""Staff auth lifecycle: short access tokens, rotating refresh, email port (#248)."""

from datetime import datetime, timedelta

import pytest

from app.config import Settings, get_settings
from app.models.models import Cooperative, StaffRefreshToken, User
from app.services.auth_service import get_password_hash
from app.services.providers.factory import reset_providers


@pytest.fixture()
def auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "test-lifecycle-secret-key")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-lifecycle-admin-password")
    get_settings.cache_clear()
    reset_providers()
    yield
    get_settings.cache_clear()
    reset_providers()


def _coop_user(db, suffix: str = "1"):
    cooperative = Cooperative(
        name=f"Lifecycle {suffix}",
        currency="GHS",
        subscription_plan="growth",
        subscription_band="base",
        subscription_status="active",
        subscription_expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(cooperative)
    db.flush()
    user = User(
        email=f"admin-{suffix}@example.com",
        hashed_password=get_password_hash("password"),
        role="admin",
        cooperative_id=cooperative.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return cooperative, user


def test_production_defaults_to_sixty_minute_access_tokens():
    settings = Settings.model_construct(app_env="production", access_token_expire_minutes=0)
    assert settings.effective_access_token_minutes == 60
    settings = Settings.model_construct(app_env="development", access_token_expire_minutes=0)
    assert settings.effective_access_token_minutes == 60 * 24 * 7


def test_production_rejects_access_tokens_longer_than_a_day():
    with pytest.raises(ValueError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="strong-secret-key",
            admin_password="strong-password",
            database_url="postgresql://user:password@db.example.com:5432/agro_os",
            auth_enabled=True,
            moolre_webhook_secret="whsec",
            access_token_expire_minutes=60 * 24 * 7,
        )


def test_login_issues_rotating_refresh_token(client, db, auth_enabled):
    _coop_user(db)
    login = client.post("/auth/login", json={"email": "admin-1@example.com", "password": "password"})
    assert login.status_code == 200
    body = login.json()
    assert body["refresh_token"]
    assert body["expires_in"] > 0
    assert db.query(StaffRefreshToken).count() == 1


def test_refresh_rotates_and_rejects_replay(client, db, auth_enabled):
    _coop_user(db)
    first = client.post("/auth/login", json={"email": "admin-1@example.com", "password": "password"}).json()
    old = first["refresh_token"]
    refreshed = client.post("/auth/refresh", json={"refresh_token": old})
    assert refreshed.status_code == 200
    new = refreshed.json()["refresh_token"]
    assert new and new != old
    replay = client.post("/auth/refresh", json={"refresh_token": old})
    assert replay.status_code == 401
    # Replay of a rotated token revokes the family, so the new token dies too.
    assert client.post("/auth/refresh", json={"refresh_token": new}).status_code == 401


def test_logout_revokes_the_presented_refresh_token(client, db, auth_enabled):
    _coop_user(db)
    login = client.post("/auth/login", json={"email": "admin-1@example.com", "password": "password"}).json()
    assert client.post("/auth/logout", json={"refresh_token": login["refresh_token"]}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401


def test_password_change_revokes_other_sessions_and_issues_a_new_one(client, db, auth_enabled):
    _coop_user(db, "2")
    other = client.post("/auth/login", json={"email": "admin-2@example.com", "password": "password"}).json()
    login = client.post("/auth/login", json={"email": "admin-2@example.com", "password": "password"}).json()
    changed = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"new_password": "brand-new-password"},
    )
    assert changed.status_code == 200
    assert changed.json()["refresh_token"]
    assert client.post("/auth/refresh", json={"refresh_token": other["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": changed.json()["refresh_token"]}).status_code == 200


def test_invite_returns_a_link_when_email_is_logged(client, db, auth_enabled):
    coop, user = _coop_user(db, "3")
    login = client.post("/auth/login", json={"email": user.email, "password": "password"}).json()
    invited = client.post(
        "/auth/invite",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"email": "officer-3@example.com", "role": "finance_officer"},
    )
    assert invited.status_code == 201
    delivery = invited.json()["delivery"]
    assert delivery["channel"] == "log"
    assert delivery["delivered"] is False
    assert delivery["invite_link"]
    assert "/login?invite=" in delivery["invite_link"]


def test_password_reset_request_is_public_and_does_not_enumerate(client, db, auth_enabled):
    missing = client.post("/auth/password-reset-request", json={"email": "nobody@example.com"})
    assert missing.status_code == 200
    assert missing.json()["delivered"] is False
    _coop_user(db, "4")
    present = client.post("/auth/password-reset-request", json={"email": "admin-4@example.com"})
    assert present.status_code == 200
    assert present.json()["channel"] == "log"
