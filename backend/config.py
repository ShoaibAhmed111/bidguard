from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for BidGuard AI (sandbox vs API Setu production)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: Literal["SANDBOX", "PRODUCTION"] = "SANDBOX"
    SANDBOX_BASE_URL: str = "http://localhost:8000/api/v1/mock"
    API_SETU_BASE_URL: str = "https://apisetu.gov.in/api/v1"
    API_SETU_CLIENT_ID: str | None = None
    API_SETU_CLIENT_SECRET: str | None = None
    TURNOVER_TOLERANCE_PCT: float = 0.10
    MIN_NAME_MATCH_SIMILARITY: float = 0.85


settings = Settings()
