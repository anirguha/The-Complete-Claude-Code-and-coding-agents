# FinAlly backend

FastAPI app, run with `uvicorn app.main:app`.

| Module           | Purpose                                                                        |
| ---------------- | ------------------------------------------------------------------------------ |
| `app/main.py`    | App wiring, lifespan, snapshot task, and serving the frontend export           |
| `app/api/`       | Portfolio, watchlist and health routes, and error handling                     |
| `app/db/`        | SQLite schema, seed data and repository functions                              |
| `app/portfolio/` | Trades, valuation, watchlist rules and snapshots                               |
| `app/llm/`       | Chat: LiteLLM through OpenRouter, mock mode, and running the requested actions |
| `app/market/`    | Simulator, Massive client, price cache and the SSE stream                      |

Market data design docs: `../planning/MASSIVE_API.md`, `../planning/MASSIVE_INTERFACE.md`, `../planning/MARKET_SIMULATOR.md`.

```bash
uv sync
uv run pytest
LLM_MOCK=true DB_PATH=/tmp/finally.db uv run uvicorn app.main:app --port 8010
uv run market_data_demo.py   # live terminal demo of the simulator; --help for options
```

| Variable               | Default         | Purpose                                                              |
| ---------------------- | --------------- | -------------------------------------------------------------------- |
| `DB_PATH`              | `db/finally.db` | SQLite file, relative to the working directory. Keep it off synced folders |
| `STATIC_DIR`           | `static`        | Frontend export. If missing, the API runs alone and a warning is logged |
| `OPENROUTER_API_KEY`   | none            | Enables chat. Without it, chat replies that the LLM is not configured |
| `LLM_MOCK`             | `false`         | `true` returns deterministic mock chat replies                       |
| `MASSIVE_API_KEY`      | none            | Real market data. Empty uses the simulator                           |
| `MASSIVE_POLL_SECONDS` | `5`             | Massive poll interval                                                |

The app reads these from the environment, and from `.env` in the project root if it exists.

Serve with `--timeout-graceful-shutdown 3`: an open SSE stream otherwise blocks shutdown.
