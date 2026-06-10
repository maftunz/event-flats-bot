"""Shared base settings: backend URL + service-account credentials.

The admin and client bots each have their own subclass that adds a
BOT_TOKEN (and, for the client bot, OPENAI_*).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseBotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    backend_url: str = Field(..., description="Laravel API base URL with /api/v1")
    backend_login: str = Field(..., description="Service-account login/email")
    backend_password: str = Field(..., description="Service-account password")
    log_level: str = Field("INFO", description="Logging level")
