"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(..., description="Telegram bot token from @BotFather")
    backend_url: str = Field(..., description="Laravel API base URL with /api/v1")
    backend_login: str = Field(..., description="Service-account login/email")
    backend_password: str = Field(..., description="Service-account password")
    log_level: str = Field("INFO", description="Logging level")

    # Public HTTPS URL of the admin WebApp. When set, the bot exposes an
    # /admin command + a chat menu button that opens it inside Telegram.
    # Telegram rejects http:// URLs for WebApps, so this must be https.
    webapp_url: Optional[str] = Field(None, description="Public HTTPS URL of the admin WebApp")


def load_settings() -> Settings:
    """Singleton-style accessor — exits with a readable error if env is missing."""
    return Settings()  # type: ignore[call-arg]
