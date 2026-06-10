"""Run with `python -m event_flats_bot.client`."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from ..core.backend import BackendClient
from .handlers import chat
from .llm import LLMService
from .settings import ClientSettings, load_client_settings

logger = logging.getLogger(__name__)


async def _configure(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать новый подбор"),
            BotCommand(command="help", description="Как пользоваться"),
        ]
    )


async def _run() -> None:
    settings = load_client_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    backend = BackendClient(
        base_url=settings.backend_url,
        login=settings.backend_login,
        password=settings.backend_password,
    )
    llm = LLMService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["backend"] = backend
    dp["llm"] = llm
    dp["settings"] = settings
    dp.include_router(chat.router)

    try:
        await _configure(bot)
        logger.info("Client bot polling (model=%s)…", settings.openai_model)
        await dp.start_polling(bot)
    finally:
        await llm.close()
        await backend.close()
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


if __name__ == "__main__":
    main()
