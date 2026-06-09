"""Search criteria extraction.

Right now this is a deterministic stub: it returns an empty criteria object
and the bot asks the user step-by-step via FSM. The LLM provider will be
plugged in here later — the public function signature won't change. The bot
will call ``extract_criteria(user_message)`` and get a structured
``SearchCriteria`` back, with whatever fields the LLM was able to figure out.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SearchCriteria:
    district: int | None = None
    rooms_start: int | None = None
    rooms_end: int | None = None
    price_start: int | None = None
    price_end: int | None = None
    repair: str | None = None

    def is_complete(self) -> bool:
        """Loose definition — enough to run a backend search."""
        return self.district is not None or (
            self.rooms_start is not None or self.price_end is not None
        )


async def extract_criteria(_message: str) -> SearchCriteria:
    """Stub. Returns empty criteria so the FSM handlers drive the conversation.

    When the LLM provider is added we'll replace the body with a call to it
    (e.g. an OpenAI / Anthropic structured-output call) and the rest of the
    code won't have to change.
    """
    return SearchCriteria()
