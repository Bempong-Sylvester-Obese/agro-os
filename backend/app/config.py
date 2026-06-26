"""Settings and Configuration"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "your-secret-key-change-in-production"

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
    wandb_project: str = "agro-os"
    wandb_entity: str = ""
    wandb_mode: str = "offline"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
