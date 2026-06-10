"""Free-text conversation flow.

State lives in the FSM as a JSON-serialisable blob:
  - history: list of {role, content}
  - criteria: dict version of SearchCriteria

We use MemoryStorage by default — fine for a single-process bot; swap to
Redis when the bot moves to multi-instance deployment.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ...core.backend import BackendClient
from ..llm import LLMService, SearchCriteria
from ..settings import ClientSettings

logger = logging.getLogger(__name__)

router = Router(name="client-chat")


WELCOME = (
    "👋 Здравствуйте! Я помогу подобрать квартиру в Ташкенте из нашей базы.\n\n"
    "Напишите свободным текстом, что вы ищете — район, количество комнат, "
    "бюджет, тип ремонта. Я уточню, чего не хватает, и пришлю подходящие "
    "варианты."
)


HELP = (
    "Просто опишите своими словами, что вам нужно. Примеры:\n"
    "• «2 комнаты, до 80 000»\n"
    "• «Чиланзар, евро-ремонт, 3 комнатная»\n"
    "• «нужна квартира на Мирзо-Улугбеке тысяч за сто»\n\n"
    "Команды:\n"
    "/start — начать сначала\n"
    "/help — это сообщение"
)


def _format_flat(flat: dict[str, Any]) -> str:
    price = f"${int(flat['price']):,}".replace(",", " ")
    landmark = f" · {flat['landmark']}" if flat.get("landmark") else ""
    area = f"\n📐 {flat['area']} м²" if flat.get("area") else ""
    return (
        f"<b>{flat['address']}{landmark}</b>\n"
        f"🛏 {flat['rooms_number']} комн · этаж "
        f"{flat['floor']}/{flat['floors_number']}{area}\n"
        f"🛠 {flat['repair']}\n"
        f"💵 <b>{price}</b>"
    )


def _truncate_history(
    history: list[dict[str, str]], turns: int
) -> list[dict[str, str]]:
    # Each "turn" = one user + one assistant message. Keep last 2*turns msgs.
    return history[-(turns * 2) :]


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_data({"history": [], "criteria": {}})
    await message.answer(WELCOME)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP)


@router.message()
async def on_text(
    message: Message,
    state: FSMContext,
    backend: BackendClient,
    llm: LLMService,
    settings: ClientSettings,
) -> None:
    if not message.text:
        return

    data = await state.get_data()
    history: list[dict[str, str]] = data.get("history", [])
    criteria_dict: dict[str, Any] = data.get("criteria", {})
    accumulated = SearchCriteria(**criteria_dict)

    history.append({"role": "user", "content": message.text})

    # Load districts once per conversation; cheap enough to refresh every turn
    # but we could cache. For a small bot, fine.
    try:
        districts = await backend.list_addresses()
    except Exception:
        logger.exception("Failed to load districts")
        await message.answer(
            "Не удаётся связаться с базой. Попробуйте через минуту."
        )
        return

    # Ask the model
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        result = await llm.next_turn(
            history=_truncate_history(history, settings.history_turns),
            districts=districts,
            accumulated=accumulated,
        )
    except Exception:
        logger.exception("LLM call failed")
        await message.answer(
            "Что-то у меня не получилось обработать запрос. Попробуйте "
            "перефразировать или начните заново через /start."
        )
        return

    history.append({"role": "assistant", "content": result.message})
    await state.update_data(
        history=_truncate_history(history, settings.history_turns),
        criteria=result.criteria.as_query(),
    )

    if result.action == "ask":
        await message.answer(result.message)
        return

    # action == "search"
    await message.answer(result.message)
    try:
        page = await backend.search_flats(**result.criteria.as_query())
    except Exception:
        logger.exception("Backend search failed")
        await message.answer(
            "Что-то сломалось при поиске. Попробуйте /start и заново."
        )
        return

    flats = page.get("data", [])
    total = page.get("meta", {}).get("total", 0)

    if not flats:
        await message.answer(
            "По текущим параметрам ничего не нашлось. "
            "Расширите критерии и напишите ещё раз."
        )
        return

    await message.answer(f"Нашёл <b>{total}</b> вариант(ов). Покажу первые 5:")
    for flat in flats[:5]:
        await message.answer(_format_flat(flat))

    await message.answer(
        "Хотите уточнить — район, цену, ремонт — просто напишите. "
        "Или /start чтобы начать новый подбор."
    )
