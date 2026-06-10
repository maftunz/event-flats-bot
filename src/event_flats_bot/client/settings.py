from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, Field

from ..core.settings import BaseBotSettings


class ClientSettings(BaseBotSettings):
    """Settings for the customer-facing bot. Shares the same .env file as
    the admin bot — CLIENT_/OPENAI_ prefixes keep the namespaces separate.
    """

    bot_token: str = Field(
        ...,
        validation_alias=AliasChoices("CLIENT_BOT_TOKEN", "BOT_TOKEN"),
        description="Client bot token from @BotFather",
    )

    # OpenAI / ChatGPT
    openai_api_key: str = Field(..., description="OpenAI API key (sk-...)")
    openai_model: str = Field(
        "gpt-4o-mini", description="OpenAI chat model to use"
    )
    openai_base_url: Optional[str] = Field(
        None,
        description="Optional custom base URL (Azure / proxy / self-hosted)",
    )

    # Conversation
    history_turns: int = Field(
        8, description="How many recent turns to keep per user"
    )


def load_client_settings() -> ClientSettings:
    return ClientSettings()  # type: ignore[call-arg]
