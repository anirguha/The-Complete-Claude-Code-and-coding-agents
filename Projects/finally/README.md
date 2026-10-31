# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) is a Bloomberg-style trading terminal with an AI copilot. It streams live market data, lets you trade a simulated $10,000 portfolio, and includes a chat assistant that can analyze positions, execute trades, and manage your watchlist.

It is the capstone project for an agentic AI coding course, built entirely by coding agents.

## Features

- Live watchlist with price flashes and sparklines, streamed over SSE
- Detailed price chart for the selected ticker
- Market orders with instant fills, no fees, and fractional shares
- Portfolio heatmap, P&L chart, and positions table
- AI chat that executes trades and watchlist changes automatically
- No login or signup; data persists in SQLite

## Stack

| Layer       | Technology                                            |
| ----------- | ----------------------------------------------------- |
| Frontend    | Next.js (TypeScript, static export), Tailwind CSS     |
| Backend     | FastAPI, managed with `uv`                            |
| Database    | SQLite                                                |
| Market data | Built-in GBM simulator, or the Massive API with a key |
| AI          | LiteLLM → OpenRouter (Cerebras inference)             |
| Deployment  | Single Docker container                               |

## Run with Docker

You need Docker running. On macOS or Linux:

```bash
scripts/start_mac.sh   # build if needed, start, wait until healthy, open the browser
scripts/stop_mac.sh    # stop and remove the container; your data is kept
```

Then go to http://localhost:8000. To use another port, because 8000 is busy for example:

```bash
FINALLY_PORT=8030 scripts/start_mac.sh
```

`start_mac.sh` flags: `--build` rebuilds the image after a code change, and `--no-open` skips the browser. Running it again replaces the container.

On Windows PowerShell, use `scripts\start_windows.ps1` (`-Build`, `-NoOpen`, `$env:FINALLY_PORT`) and `scripts\stop_windows.ps1`. **The Windows scripts have not been run yet.**

The app is published on `127.0.0.1` only, because it has no login and its chat can place trades.

Your portfolio lives in the `finally-data` Docker volume. To start over at $10,000, stop the app and run `docker volume rm finally-data`.

## Configuration

The start script creates `.env` from `.env.example` the first time. Restart with the start script after editing it.

| Variable             | Purpose                                                                     |
| -------------------- | --------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY` | Enables AI chat. Without it the app runs, and chat says it is not configured |
| `MASSIVE_API_KEY`    | Optional. Real market data; empty uses the built-in simulator               |
| `LLM_MOCK`           | `true` returns deterministic mock chat replies, with no key or network      |

Docker reads `.env` literally, so do not quote values or put comments after them.

## Local development

Backend, from `backend/`, on a database outside any synced folder:

```bash
LLM_MOCK=true DB_PATH=/tmp/finally.db uv run uvicorn app.main:app --port 8010
```

Without a frontend export the backend serves the API only, and `/` returns 404. It logs a warning saying so. Either build the frontend and set `STATIC_DIR` to `frontend/out`, or run the frontend dev server, from `frontend/`:

```bash
npm install
BACKEND_URL=http://localhost:8010 npm run dev
```

## Tests

```bash
cd backend && uv run --frozen pytest   # backend unit and integration tests
cd frontend && npm test                # frontend unit tests
```

Browser tests need a running app with `LLM_MOCK=true`. They sell positions and change the watchlist, so run them against a throwaway volume, never `finally-data`:

```bash
docker run -d --name finally-e2e -v finally-e2e-data:/app/db -p 127.0.0.1:8031:8000 -e LLM_MOCK=true finally
E2E_BASE_URL=http://127.0.0.1:8031 E2E_REQUIRE_FRESH=1 test/run_e2e.sh
docker rm -f finally-e2e && docker volume rm finally-e2e-data
```

## Not yet exercised

Chat against the real LLM and market data from the real Massive API have not been run end to end; tests use mock mode and the simulator.

## Documentation

The specification is [`planning/PLAN.md`](planning/PLAN.md). [`planning/TEAM_CONTRACT.md`](planning/TEAM_CONTRACT.md) records the decisions that refine it, and wins where they disagree. [`planning/INTEGRATION_REPORT.md`](planning/INTEGRATION_REPORT.md) has the test results and known issues.
