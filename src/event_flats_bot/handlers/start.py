"""/start, /help and the about button."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from ..keyboards.search import main_menu_kb

router = Router(name="start")


WELCOME = (
    "👋 Здравствуйте! Я подберу для вас квартиру из нашей базы.\n\n"
    "Напишите, что вы ищете, или нажмите кнопку «Найти квартиру» — "
    "я задам несколько уточняющих вопросов."
)


ABOUT = (
    "Event Flats — каталог квартир в Ташкенте.\n"
    "Бот показывает только актуальные предложения из нашей базы. "
    "Связаться с собственником можно после уточнения деталей у менеджера."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "about")
async def on_about(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(ABOUT, reply_markup=main_menu_kb())
