# event-flats-bot

Two Telegram bots that share a code base:

| Bot                  | Audience  | Job                                        | Entrypoint                       |
|----------------------|-----------|--------------------------------------------|----------------------------------|
| `event-flats-admin-bot`  | staff   | Opens the admin WebApp via menu button     | `python -m event_flats_bot.admin`  |
| `event-flats-client-bot` | clients | Natural-language search powered by OpenAI  | `python -m event_flats_bot.client` |

They share the Laravel backend client (`event_flats_bot.core.backend`)
and a common `.env` — namespaced via `ADMIN_*` / `CLIENT_*` / `OPENAI_*`
prefixes so the two never collide.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Fill in:
#   ADMIN_BOT_TOKEN, ADMIN_WEBAPP_URL
#   CLIENT_BOT_TOKEN, OPENAI_API_KEY
#   BACKEND_URL, BACKEND_LOGIN, BACKEND_PASSWORD
```

Then in two terminals:

```bash
python -m event_flats_bot.admin     # admin bot
python -m event_flats_bot.client    # client bot
```

(Or run them both via `docker compose up`.)

## Layout

```
src/event_flats_bot/
├── core/
│   ├── backend.py       — async httpx wrapper over /api/v1
│   └── settings.py      — BaseBotSettings (backend creds + log level)
├── admin/
│   ├── __main__.py      — admin bot polling loop
│   ├── settings.py      — AdminSettings (ADMIN_BOT_TOKEN, ADMIN_WEBAPP_URL)
│   └── handlers/menu.py — /start /admin /help, all forwarded to the WebApp
└── client/
    ├── __main__.py      — client bot polling loop
    ├── settings.py      — ClientSettings (CLIENT_BOT_TOKEN, OPENAI_*)
    ├── llm.py           — OpenAI structured-output dialog brain
    └── handlers/chat.py — free-text → LLM → search or clarify
```

## How the client bot thinks

Every user message hits `LLMService.next_turn(history, districts, accumulated)`,
which returns one of:

- `{action: "ask", message: "..."}` — needs more info, the message is the
  next clarifying question
- `{action: "search", message: "...", criteria: {...}}` — has enough; the
  bot calls `/api/v1/flats?...` with the criteria and sends back up to 5
  cards

The response is enforced via OpenAI Structured Outputs
(`response_format: json_schema, strict: true`) so we never have to parse
free text.

## Swapping the LLM provider

`LLMService` only depends on OpenAI's chat-completions interface. To point
at Azure OpenAI, an OpenAI-compatible gateway, or a self-hosted vLLM,
set `OPENAI_BASE_URL` in `.env`. To swap in Anthropic or Gemini, replace
the `_client.chat.completions.create` call in `client/llm.py` — the rest
of the bot doesn't care.
