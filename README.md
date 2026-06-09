# event-flats-bot

Telegram bot for end customers. Skeleton without LLM — uses a step-by-step
FSM (rooms → district → price → results) and calls the Event Flats backend
under a service-account JWT.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # then fill BOT_TOKEN from @BotFather
python -m event_flats_bot
```

The bot expects the Event Flats backend to be reachable at `BACKEND_URL`
(default `http://127.0.0.1:8000/api/v1`) and logs in as the service
account defined in `BACKEND_LOGIN` / `BACKEND_PASSWORD`.

## Layout

```
src/event_flats_bot/
├── __main__.py       — entrypoint, builds the Bot/Dispatcher
├── config.py         — pydantic-settings loaded from env / .env
├── api/backend.py    — async httpx client around /api/v1, manages the JWT
├── services/search.py — extract_criteria() stub (LLM goes here later)
├── keyboards/search.py — inline keyboards
└── handlers/
    ├── start.py      — /start, /help, "About"
    └── search.py     — FSM-driven search flow
```

## Adding the LLM later

`services.search.extract_criteria` is the seam. Replace its body with a
provider call (OpenAI / Anthropic) that returns a `SearchCriteria`. The
`search` handler will call it on free-text messages and skip ahead in the
FSM when the LLM filled fields in.

The provider choice was deferred — see the project plan in
`event-flats-backend`.
