"""
NeuroGenix WarmUp — App Config / Settings
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "NeuroGenix WarmUp"
    app_version: str = "1.0.0"
    debug: bool = True
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./neurogenix_warmup.db"

    # JWT
    jwt_secret_key: str = "N3ur0G3n1xS3cr3tK3y_WarmUp_2025_ChangeMe!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # Super Admin
    super_admin_email: str = "admin@neurogenix.ai"
    super_admin_password: str = "Neurogenix@2025!"

    # Encryption
    encryption_key: str = "dGhpcyBpcyBhIDMyIGJ5dGUga2V5Zm9yd2FybXVw"

    # Uploads
    upload_dir: str = "uploads/logos"

    # Warmup schedule
    warmup_run_hour: int = 9
    warmup_run_minute: int = 0

    # Google OAuth (set GOOGLE_CLIENT_ID in .env after creating a Google Cloud project)
    google_client_id: str = ""
    google_client_secret: str = ""  # needed for Gmail API OAuth token exchange
    google_redirect_uri: str = "http://localhost:8000/mailboxes/oauth/google-callback"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    if s.database_url and s.database_url.startswith("postgres://"):
        s.database_url = s.database_url.replace("postgres://", "postgresql://", 1)
    return s


settings = get_settings()
