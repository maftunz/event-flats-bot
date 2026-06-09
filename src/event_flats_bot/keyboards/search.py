"""Reusable inline keyboards for the search flow."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти квартиру", callback_data="search:start")],
            [InlineKeyboardButton(text="ℹ О сервисе", callback_data="about")],
        ]
    )


def rooms_kb() -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text=f"{n}", callback_data=f"search:rooms:{n}")
        for n in (1, 2, 3, 4)
    ]
    row2 = [InlineKeyboardButton(text="5+", callback_data="search:rooms:5")]
    row3 = [InlineKeyboardButton(text="Неважно", callback_data="search:rooms:any")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3])


def districts_kb(districts: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for d in districts:
        row.append(
            InlineKeyboardButton(text=d["title"], callback_data=f"search:district:{d['id']}")
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton(text="Любой район", callback_data="search:district:any")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def price_kb() -> InlineKeyboardMarkup:
    ranges = [
        ("до $50 000", "0-50000"),
        ("$50–80k", "50000-80000"),
        ("$80–120k", "80000-120000"),
        ("$120–200k", "120000-200000"),
        ("$200k+", "200000-0"),
        ("Неважно", "any"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"search:price:{code}")]
            for label, code in ranges
        ]
    )
