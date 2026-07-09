import pytest

from app.config import Settings


def test_auth_disabled_allows_demo_defaults():
    settings = Settings(auth_enabled=False)
    assert settings.secret_key == "your-secret-key-change-in-production"
    assert settings.admin_password == "demo1234"


def test_auth_enabled_rejects_default_secret_key():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(auth_enabled=True, admin_password="strong-password")


def test_auth_enabled_rejects_default_admin_password():
    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        Settings(auth_enabled=True, secret_key="strong-secret-key")


def test_auth_enabled_accepts_non_default_credentials():
    settings = Settings(
        auth_enabled=True,
        secret_key="strong-secret-key",
        admin_password="strong-password",
    )
    assert settings.auth_enabled is True
