"""/admin command — opens the WebApp inside Telegram.

The WebApp itself enforces admin login (the backend rejects non-admin
JWTs with 403), so we don't gate the command here — anyone who knows
about it sees the button, but a non-admin can't actually use the UI.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ..config import Settings

router = Router(name="admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: Settings) -> None:
    if not settings.webapp_url:
        await message.answer(
            "Админ-панель пока не настроена: переменная WEBAPP_URL не задана.\n"
            "Задайте публичный HTTPS-URL WebApp в .env и перезапустите бот."
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠 Открыть админ-панель",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )
    await message.answer(
        "Откройте панель администратора прямо в Telegram. "
        "Внутри потребуется войти под учётной записью администратора.",
        reply_markup=kb,
    )
