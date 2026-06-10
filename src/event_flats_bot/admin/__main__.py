"""Run with `python -m event_flats_bot.admin`."""

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

from .handlers import menu
from .settings import AdminSettings, load_admin_settings

logger = logging.getLogger(__name__)


async def _configure(bot: Bot, settings: AdminSettings) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="admin", description="Открыть админ-панель"),
            BotCommand(command="help", description="Помощь"),
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
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("WEBAPP_URL not set, using default commands menu button")


async def _run() -> None:
    settings = load_admin_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    dp.include_router(menu.router)

    try:
        await _configure(bot, settings)
        logger.info("Admin bot polling…")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


if __name__ == "__main__":
    main()
