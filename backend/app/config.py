"""Settings and Configuration"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"
_DEFAULT_ADMIN_PASSWORD = "demo1234"


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_env: str = "development"
    debug: bool = True
    secret_key: str = _DEFAULT_SECRET_KEY
    auth_enabled: bool = False
    admin_email: str = "admin@agroos.demo"
    admin_password: str = _DEFAULT_ADMIN_PASSWORD
    seed_demo_data: bool = False

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/agro_os"

    # Supabase (optional — for direct SDK use in future)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

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

    # Cooperative defaults
    default_currency: str = "GHS"
    default_sms_sender_id: str = "AgroOS"

    # Agro-AI
    agro_ai_model_path: str = "backend/model_artifacts/agro-ai-rf-v1.joblib"
    agro_ai_audit_log_path: str = "backend/logs/agro_ai_predictions.jsonl"
    agro_ai_require_artifact: bool = False
    sentry_dsn: str = ""
    wandb_project: str = "agro-os"
    wandb_entity: str = ""
    wandb_mode: str = "offline"

    @model_validator(mode="after")
    def reject_demo_auth_defaults_when_enabled(self) -> "Settings":
        if not self.auth_enabled:
            return self

        insecure = []
        if self.secret_key == _DEFAULT_SECRET_KEY:
            insecure.append("SECRET_KEY")
        if self.admin_password == _DEFAULT_ADMIN_PASSWORD:
            insecure.append("ADMIN_PASSWORD")
        if insecure:
            joined = " and ".join(insecure)
            raise ValueError(
                f"AUTH_ENABLED=true requires non-default credentials; set {joined} in .env"
            )
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
