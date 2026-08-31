"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values come from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+asyncpg://deskly:deskly@db:5432/deskly"

    # Webhook shared secret used to verify HMAC-SHA256 signatures.
    webhook_secret: str = "change-me"

    # Max age (seconds) accepted for a webhook timestamp (replay protection, bonus).
    webhook_max_age_seconds: int = 300

    # CORS: comma-separated list of allowed origins for the frontend.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
