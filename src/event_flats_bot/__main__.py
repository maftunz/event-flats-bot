"""Entrypoint: ``python -m event_flats_bot`` or ``event-flats-bot``."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .api.backend import BackendClient
from .config import load_settings
from .handlers import search, start

logger = logging.getLogger(__name__)


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

    # Inject the backend client into every handler that asks for it.
    dp["backend"] = backend

    dp.include_router(start.router)
    dp.include_router(search.router)

    try:
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
