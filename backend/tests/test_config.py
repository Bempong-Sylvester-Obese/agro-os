import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "origin",
    [
        "https://agro-os-git-dev-sylvester-bempong.vercel.app",
        "https://agro-reo64wx52-sylvester-bempong.vercel.app",
    ],
)
def test_vercel_preview_origins_are_allowed(client, origin):
    response = client.options(
        "/auth/signup",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_auth_disabled_allows_demo_defaults(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    settings = Settings(_env_file=None)
    assert settings.secret_key == "your-secret-key-change-in-production"
    assert settings.admin_password == "demo1234"


def test_auth_enabled_rejects_default_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(_env_file=None, auth_enabled=True, admin_password="strong-password")


def test_auth_enabled_rejects_default_admin_password():
    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        Settings(auth_enabled=True, secret_key="strong-secret-key")


def test_production_rejects_default_database_url():
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings(app_env="production", secret_key="strong-secret-key", database_url="postgresql://user:password@localhost:5432/agro_os")


def test_production_requires_authentication():
    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="strong-secret-key",
            admin_password="strong-password",
            database_url="postgresql://user:password@db.example.com:5432/agro_os",
            auth_enabled=False,
        )
