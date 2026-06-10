"""All-in-one menu for the admin bot.

The bot's job is to surface the WebApp; it doesn't carry any other UX.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ..settings import AdminSettings

router = Router(name="admin-menu")


def _webapp_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠 Открыть админ-панель",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, settings: AdminSettings) -> None:
    if settings.webapp_url:
        await message.answer(
            "Это служебный бот администратора Event Flats. "
            "Откройте панель кнопкой ниже или через ☰ слева внизу.",
            reply_markup=_webapp_kb(settings.webapp_url),
        )
    else:
        await message.answer(
            "Это служебный бот администратора. "
            "WebApp пока не сконфигурирован (WEBAPP_URL пуст)."
        )


@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: AdminSettings) -> None:
    if not settings.webapp_url:
        await message.answer(
            "WebApp не настроен. Задайте WEBAPP_URL в .env и перезапустите."
        )
        return
    await message.answer(
        "Откройте админ-панель внутри Telegram:",
        reply_markup=_webapp_kb(settings.webapp_url),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, settings: AdminSettings) -> None:
    await cmd_start(message, settings)
