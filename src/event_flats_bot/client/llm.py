"""OpenAI-backed dialog brain for the client bot.

Each turn we send the model:
  - the conversation so far
  - the catalogue of districts (so it can map names → ids)
  - the current accumulated SearchCriteria
  - a strict JSON schema describing what it should return

The model decides one of two things:
  - "ask"   — needs more info, returns the next clarifying question
  - "search" — has enough to search; returns the updated criteria

The schema is enforced via OpenAI Structured Outputs (`response_format`
with `json_schema` + strict=true) so we never have to parse free text.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


REPAIRS = [
    "Евро-ремонт",
    "Хороший ремонт",
    "Средний",
    "Требует ремонта",
    "Коробка",
]


@dataclass
class SearchCriteria:
    district: int | None = None
    rooms_start: int | None = None
    rooms_end: int | None = None
    price_start: int | None = None
    price_end: int | None = None
    repair: str | None = None

    def as_query(self) -> dict[str, Any]:
        q: dict[str, Any] = {}
        if self.district is not None:
            q["district"] = self.district
        if self.rooms_start is not None:
            q["rooms_start"] = self.rooms_start
        if self.rooms_end is not None:
            q["rooms_end"] = self.rooms_end
        if self.price_start is not None:
            q["price_start"] = self.price_start
        if self.price_end is not None:
            q["price_end"] = self.price_end
        if self.repair is not None:
            q["repair"] = self.repair
        return q


@dataclass
class DialogResult:
    action: Literal["ask", "search"]
    message: str
    """The text the bot should send to the user verbatim."""
    criteria: SearchCriteria = field(default_factory=SearchCriteria)


SYSTEM_PROMPT = """\
Ты — дружелюбный консультант агентства недвижимости в Ташкенте. Помогаешь
клиенту подобрать квартиру из нашей базы.

Твоя работа за один ход:
  1) Понять, что клиент уже сказал.
  2) Решить: хватает ли данных для поиска (хотя бы район ИЛИ количество
     комнат ИЛИ потолок цены — какие-то фильтры) или нужно уточнить.
  3) Вернуть JSON по схеме.

Если нужно уточнить — задавай ОДИН короткий вопрос за раз, на русском,
без шаблонных формулировок. Не задавай вопросы, на которые клиент уже
ответил.

Если данных достаточно — заполни criteria. Поля, которых клиент не
называл, оставляй null. Цены — в долларах, целые числа.

Поле district — это ID района из списка. Если клиент назвал район
по-русски, найди соответствие по точному вхождению или похожему названию.

Поле repair — одно из: Евро-ремонт, Хороший ремонт, Средний, Требует
ремонта, Коробка. Если клиент сказал "хороший", "косметика" — нормализуй
к ближайшему варианту.

Если клиент пишет что-то не по теме — мягко верни разговор к подбору
квартиры одной фразой.
"""


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["ask", "search"],
            "description": (
                "ask = задать уточняющий вопрос; "
                "search = данных достаточно, искать сейчас"
            ),
        },
        "message": {
            "type": "string",
            "description": (
                "Текст ответа клиенту. Для action=ask — это вопрос. "
                "Для action=search — короткое подтверждение, что начинаем поиск."
            ),
        },
        "criteria": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "district": {
                    "type": ["integer", "null"],
                    "description": "ID района или null",
                },
                "rooms_start": {"type": ["integer", "null"]},
                "rooms_end": {"type": ["integer", "null"]},
                "price_start": {"type": ["integer", "null"]},
                "price_end": {"type": ["integer", "null"]},
                "repair": {
                    "type": ["string", "null"],
                    "enum": [*REPAIRS, None],
                },
            },
            "required": [
                "district",
                "rooms_start",
                "rooms_end",
                "price_start",
                "price_end",
                "repair",
            ],
        },
    },
    "required": ["action", "message", "criteria"],
}


class LLMService:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def build_districts_context(self, districts: list[dict[str, Any]]) -> str:
        rows = "\n".join(
            f"  - id={d['id']}, title={d['title']!r}"
            for d in districts
        )
        return f"Доступные районы:\n{rows}"

    async def next_turn(
        self,
        history: list[dict[str, str]],
        districts: list[dict[str, Any]],
        accumulated: SearchCriteria,
    ) -> DialogResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": self.build_districts_context(districts),
            },
            {
                "role": "system",
                "content": (
                    "Текущие накопленные критерии (используй и дополняй): "
                    + json.dumps(accumulated.as_query(), ensure_ascii=False)
                ),
            },
            *history,
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "dialog_turn",
                        "schema": RESPONSE_SCHEMA,
                        "strict": True,
                    },
                },
                temperature=0.3,
            )
        except Exception:
            logger.exception("OpenAI call failed")
            raise

        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        criteria_data = data.get("criteria") or {}
        criteria = SearchCriteria(
            district=criteria_data.get("district") or accumulated.district,
            rooms_start=criteria_data.get("rooms_start") or accumulated.rooms_start,
            rooms_end=criteria_data.get("rooms_end") or accumulated.rooms_end,
            price_start=criteria_data.get("price_start") or accumulated.price_start,
            price_end=criteria_data.get("price_end") or accumulated.price_end,
            repair=criteria_data.get("repair") or accumulated.repair,
        )

        return DialogResult(
            action=data.get("action", "ask"),
            message=data.get("message") or "Расскажите чуть подробнее, что вы ищете?",
            criteria=criteria,
        )

    async def close(self) -> None:
        await self._client.close()
