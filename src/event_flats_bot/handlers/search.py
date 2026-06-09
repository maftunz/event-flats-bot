"""Step-by-step search flow over an FSM.

Flow:
    rooms → district → price → results

When the LLM is added, the `extract_criteria` service will fill some fields
up-front from the user's free-text message and the FSM will only ask for what's
still missing.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..api.backend import BackendClient
from ..keyboards.search import districts_kb, main_menu_kb, price_kb, rooms_kb

logger = logging.getLogger(__name__)

router = Router(name="search")


class SearchSG(StatesGroup):
    rooms = State()
    district = State()
    price = State()


def _format_flat(flat: dict[str, Any]) -> str:
    price = f"${int(flat['price']):,}".replace(",", " ")
    landmark = f" · {flat['landmark']}" if flat.get("landmark") else ""
    area = f"\n📐 {flat['area']} м²" if flat.get("area") else ""
    return (
        f"<b>{flat['address']}{landmark}</b>\n"
        f"🛏 {flat['rooms_number']} комн · этаж {flat['floor']}/{flat['floors_number']}{area}\n"
        f"🛠 {flat['repair']}\n"
        f"💵 <b>{price}</b>"
    )


@router.callback_query(lambda c: c.data == "search:start")
async def on_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchSG.rooms)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Сколько комнат вам нужно?", reply_markup=rooms_kb()
        )


@router.callback_query(StateFilter(SearchSG.rooms), lambda c: (c.data or "").startswith("search:rooms:"))
async def on_rooms(
    callback: CallbackQuery,
    state: FSMContext,
    backend: BackendClient,
) -> None:
    assert callback.data
    raw = callback.data.split(":")[-1]
    if raw == "any":
        await state.update_data(rooms_start=None, rooms_end=None)
    elif raw == "5":
        await state.update_data(rooms_start=5, rooms_end=None)
    else:
        n = int(raw)
        await state.update_data(rooms_start=n, rooms_end=n)

    await callback.answer()
    await state.set_state(SearchSG.district)

    try:
        districts = await backend.list_addresses()
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to load districts")
        if callback.message:
            await callback.message.answer(
                f"Не получилось загрузить список районов: {e}.",
                reply_markup=main_menu_kb(),
            )
        return

    if callback.message:
        await callback.message.answer(
            "Какой район интересует?", reply_markup=districts_kb(districts)
        )


@router.callback_query(StateFilter(SearchSG.district), lambda c: (c.data or "").startswith("search:district:"))
async def on_district(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data
    raw = callback.data.split(":")[-1]
    if raw != "any":
        await state.update_data(district=int(raw))
    await callback.answer()

    await state.set_state(SearchSG.price)
    if callback.message:
        await callback.message.answer("Какой бюджет?", reply_markup=price_kb())


@router.callback_query(StateFilter(SearchSG.price), lambda c: (c.data or "").startswith("search:price:"))
async def on_price(
    callback: CallbackQuery,
    state: FSMContext,
    backend: BackendClient,
) -> None:
    assert callback.data
    raw = callback.data.split(":")[-1]
    if raw != "any":
        lo, hi = raw.split("-")
        await state.update_data(
            price_start=int(lo) or None,
            price_end=int(hi) or None,
        )
    await callback.answer("Ищу подходящие квартиры…")

    data = await state.get_data()
    await state.clear()

    if not callback.message:
        return

    try:
        result = await backend.search_flats(
            district=data.get("district"),
            rooms_start=data.get("rooms_start"),
            rooms_end=data.get("rooms_end"),
            price_start=data.get("price_start"),
            price_end=data.get("price_end"),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Backend search failed")
        await callback.message.answer(
            f"Ошибка при поиске: {e}. Попробуйте ещё раз позже.",
            reply_markup=main_menu_kb(),
        )
        return

    flats = result.get("data", [])
    total = result.get("meta", {}).get("total", 0)

    if not flats:
        await callback.message.answer(
            "По вашим параметрам ничего не нашлось. "
            "Попробуйте расширить критерии.",
            reply_markup=main_menu_kb(),
        )
        return

    await callback.message.answer(
        f"Нашёл {total} подходящих квартир. Первые из них:"
    )
    for flat in flats[:5]:
        await callback.message.answer(_format_flat(flat), parse_mode="HTML")

    await callback.message.answer(
        "Чтобы посмотреть подробности и связаться с менеджером, напишите номер "
        "квартиры или начните новый поиск.",
        reply_markup=main_menu_kb(),
    )


@router.message(StateFilter("*"))
async def on_free_text(message: Message, state: FSMContext) -> None:
    """Fallback: free-text → currently just nudges back to the menu.

    Later this is where the LLM will extract structured criteria from
    arbitrary messages and skip ahead in the FSM.
    """
    current = await state.get_state()
    if current is not None:
        await message.answer(
            "Я жду ответ на кнопках выше. Нажмите одну из них или /start, "
            "чтобы начать заново."
        )
        return
    await message.answer(
        "Я пока умею искать только по кнопкам. Нажмите «Найти квартиру».",
        reply_markup=main_menu_kb(),
    )
