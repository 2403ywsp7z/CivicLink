from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: Literal["demo", "production"] = "demo"
    app_name: str = "CivicLink"
    app_env: str = "development"
    secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://civiclink:civiclink@localhost:5432/civiclink"

    jwt_secret: str = "change-me-access"
    jwt_refresh_secret: str = "change-me-refresh"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    frontend_origin: str = "http://localhost:5173"
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    maps_provider: Literal["osm", "google", "mapbox"] = "osm"
    maps_api_key: str = ""

    storage_provider: Literal["local", "s3"] = "local"
    storage_endpoint: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "civiclink-media"
    storage_region: str = "us-east-1"
    storage_public_base_url: str = "http://localhost:8000/media"
    local_storage_path: str = "./uploads"

    email_provider: str = "console"
    email_api_key: str = ""
    email_from: str = "noreply@civiclink.local"
    sms_provider: str = "console"
    sms_api_key: str = ""
    otp_provider: str = "console"
    otp_api_key: str = ""

    ai_verification_provider: str = "local_metadata"
    ai_verification_api_key: str = ""
    ai_verification_endpoint: str = ""

    notification_providers: str = "inapp"

    emergency_data_provider: str = "none"
    emergency_data_api_key: str = ""
    emergency_data_endpoint: str = ""

    municipal_data_provider: str = "none"
    municipal_data_api_key: str = ""
    municipal_data_endpoint: str = ""

    rate_limit_default: str = "60/minute"
    rate_limit_auth: str = "10/minute"
    max_upload_mb: int = 25
    max_video_mb: int = 80

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
