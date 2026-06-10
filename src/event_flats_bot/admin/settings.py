from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, Field

from ..core.settings import BaseBotSettings


class AdminSettings(BaseBotSettings):
    """Settings for the admin bot.

    Lives in the same .env as the client bot — fields are prefixed with
    ADMIN_ so the two bots don't fight over BOT_TOKEN.
    """

    bot_token: str = Field(
        ...,
        validation_alias=AliasChoices("ADMIN_BOT_TOKEN", "BOT_TOKEN"),
        description="Admin bot token from @BotFather",
    )
    webapp_url: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("ADMIN_WEBAPP_URL", "WEBAPP_URL"),
        description="Public HTTPS URL of the admin WebApp",
    )


def load_admin_settings() -> AdminSettings:
    return AdminSettings()  # type: ignore[call-arg]
