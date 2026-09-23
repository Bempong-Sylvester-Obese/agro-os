"""Settings and Configuration"""
import os
from functools import lru_cache
from typing import ClassVar

from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"
_DEFAULT_ADMIN_PASSWORD = "demo1234"
_DEFAULT_DATABASE_URL = "postgresql://user:password@localhost:5432/agro_os"


def _running_on_render() -> bool:
    """Render injects RENDER=true into every service environment."""
    return os.getenv("RENDER", "").lower() in {"true", "1", "yes"}


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_env: str = "development"
    debug: bool = True
    secret_key: str = _DEFAULT_SECRET_KEY
    admin_password: str = _DEFAULT_ADMIN_PASSWORD
    cors_origins: str = ""
    auth_enabled: bool = False
    sentry_dsn: str = ""
    seed_demo_data: bool = False
    # When false, schema changes must run via Render pre-deploy / alembic CLI.
    # Production and Render default to false so uvicorn can bind before
    # migrations finish (avoids "no open ports" deploy failures on free tier,
    # where pre-deploy commands are skipped).
    auto_migrate_on_startup: bool = True
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_webhook_per_minute: int = 120
    rate_limit_sms_per_minute: int = 5
    rate_limit_dues_per_minute: int = 10

    # Staff session lifetime (#248). Access tokens are short-lived; the
    # frontend refreshes them silently via ``POST /auth/refresh``. Leave
    # ``access_token_expire_minutes`` at 0 to take the environment default:
    # 60 minutes in production, 7 days elsewhere (so local dev sessions
    # survive a laptop lid close). Production refuses anything above 24h.
    access_token_expire_minutes: int = 0
    refresh_token_expire_days: int = 14
    # Outbound staff email (invites, password resets). ``log`` writes the
    # link to the application log — the documented interim path until an
    # SMTP/API adapter is configured. ``smtp`` uses the smtp_* settings.
    email_provider: str = "log"
    email_from: str = "AgroOS <no-reply@agroos.app>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/agro_os"

    # Supabase (optional — for direct SDK use in future)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # AgroOS deployment
    agroos_base_url: str = ""
    webhook_callback_path: str = "/webhooks/payment"

    # Moolre API
    moolre_env: str = "sandbox"
    moolre_api_url: str = "https://sandbox.moolre.com"
    moolre_api_user: str = ""
    moolre_api_key: str = ""
    moolre_api_pubkey: str = ""
    moolre_api_vaskey: str = ""

    # Moolre Merchant / Account
    moolre_account_number: str = ""
    moolre_merchant_id: str = ""
    moolre_merchant_code: str = ""
    moolre_webhook_secret: str = ""
    moolre_ussd_secret: str = ""

    # Farmer-facing AgroOS USSD menu and USSDK hook verification
    agroos_ussd_code: str = "*919*4020#"
    ussdk_hook_secret: str = ""
    ussd_callback_secret: str = ""

    # Cooperative defaults
    default_currency: str = "GHS"
    default_sms_sender_id: str = "AgroOS"

    # Agro-AI
    agro_ai_model_path: str = "backend/model_artifacts/agro-ai-rf-v1.joblib"
    agro_ai_audit_log_path: str = "backend/logs/agro_ai_predictions.jsonl"
    agro_ai_require_artifact: bool = False
    wandb_project: str = "agro-os"
    wandb_entity: str = ""
    wandb_mode: str = "offline"

    @model_validator(mode="after")
    def validate_auth_credentials(self) -> "Settings":
        if not self.auth_enabled:
            return self
        if self.secret_key == _DEFAULT_SECRET_KEY or not self.secret_key.strip():
            raise ValueError("AUTH_ENABLED=true requires a non-default SECRET_KEY")
        if self.admin_password == _DEFAULT_ADMIN_PASSWORD or not self.admin_password.strip():
            raise ValueError("AUTH_ENABLED=true requires a non-default ADMIN_PASSWORD")
        return self

    @model_validator(mode="after")
    def disable_blocking_startup_on_render(self) -> "Settings":
        # Free-tier Render skips pre-deploy commands; blocking Alembic in
        # lifespan prevents uvicorn from binding and fails the deploy.
        if _running_on_render():
            self.auto_migrate_on_startup = False
            self.seed_demo_data = False
        return self

    @property
    def is_production(self) -> bool:
        """True for ``APP_ENV`` of ``production``/``prod`` in any casing.

        Every production gate (demo seed/reset, webhook secrets, insecure
        defaults) must use this rather than comparing ``app_env`` inline so a
        value like ``Production`` cannot slip past one check and not another.
        """
        return self.app_env.strip().lower() in ("production", "prod")

    PRODUCTION_ACCESS_TOKEN_MINUTES: ClassVar[int] = 60
    DEVELOPMENT_ACCESS_TOKEN_MINUTES: ClassVar[int] = 60 * 24 * 7
    MAX_PRODUCTION_ACCESS_TOKEN_MINUTES: ClassVar[int] = 60 * 24

    @property
    def effective_access_token_minutes(self) -> int:
        """Access-token lifetime actually used when signing JWTs."""
        if self.access_token_expire_minutes > 0:
            return self.access_token_expire_minutes
        if self.is_production:
            return self.PRODUCTION_ACCESS_TOKEN_MINUTES
        return self.DEVELOPMENT_ACCESS_TOKEN_MINUTES

    @model_validator(mode="after")
    def reject_insecure_production_settings(self) -> "Settings":
        if not self.is_production:
            return self
        if self.access_token_expire_minutes > self.MAX_PRODUCTION_ACCESS_TOKEN_MINUTES:
            raise ValueError(
                "APP_ENV=production requires ACCESS_TOKEN_EXPIRE_MINUTES <= "
                f"{self.MAX_PRODUCTION_ACCESS_TOKEN_MINUTES} (24h); use the refresh flow for longer sessions"
            )
        if self.email_provider not in ("log", "smtp"):
            raise ValueError("EMAIL_PROVIDER must be 'log' or 'smtp'")
        if self.email_provider == "smtp" and not self.smtp_host.strip():
            raise ValueError("EMAIL_PROVIDER=smtp requires SMTP_HOST")
        if self.secret_key == _DEFAULT_SECRET_KEY or not self.secret_key.strip():
            raise ValueError("APP_ENV=production requires a non-default SECRET_KEY")
        if not self.database_url.strip():
            raise ValueError("APP_ENV=production requires DATABASE_URL")
        if self.database_url == _DEFAULT_DATABASE_URL:
            raise ValueError("APP_ENV=production requires a non-default DATABASE_URL")
        if self.seed_demo_data:
            raise ValueError("APP_ENV=production cannot run with SEED_DEMO_DATA=true")
        if not self.auth_enabled:
            raise ValueError("APP_ENV=production requires AUTH_ENABLED=true")
        if not self.moolre_webhook_secret:
            raise ValueError("MOOLRE_WEBHOOK_SECRET must be set in production")
        # Prefer Render pre-deploy / release-phase migrations in production.
        self.auto_migrate_on_startup = False
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
