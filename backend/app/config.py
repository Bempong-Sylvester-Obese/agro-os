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

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
