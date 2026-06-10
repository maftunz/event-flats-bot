"""Entrypoint: ``python -m event_flats_bot`` or ``event-flats-bot``."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    MenuButtonCommands,
    MenuButtonWebApp,
    WebAppInfo,
)

from .api.backend import BackendClient
from .config import Settings, load_settings
from .handlers import admin, search, start

logger = logging.getLogger(__name__)


async def _configure_bot(bot: Bot, settings: Settings) -> None:
    """One-shot setup that runs every start: commands list + menu button.

    Re-applying on each boot is cheap and keeps the bot's metadata in sync
    with whatever we ship in code without a manual BotFather step.
    """
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="admin", description="Открыть админ-панель"),
            BotCommand(command="help", description="Как пользоваться"),
        ]
    )

    if settings.webapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Админка",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        )
        logger.info("Chat menu button → WebApp at %s", settings.webapp_url)
    else:
        # Fallback to the standard commands menu if no WebApp URL configured
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("WEBAPP_URL not set, using default commands menu button")


async def _run() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    backend = BackendClient(
        base_url=settings.backend_url,
        login=settings.backend_login,
        password=settings.backend_password,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Inject the backend client and settings into every handler that asks for them.
    dp["backend"] = backend
    dp["settings"] = settings

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(search.router)

    try:
        await _configure_bot(bot, settings)
        logger.info("Starting polling…")
        await dp.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


if __name__ == "__main__":
    main()
