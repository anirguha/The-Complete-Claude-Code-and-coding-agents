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

Run the commands below from `Projects/finally`, the directory containing this README. From a fresh clone:

```bash
git clone https://github.com/anirguha/The-Complete-Claude-Code-and-coding-agents.git
cd "The-Complete-Claude-Code-and-coding-agents/Projects/finally"
```

Install and start Docker Desktop (or Docker Engine on Linux), then confirm `docker info` succeeds. Docker builds the frontend and backend for you; host Python and Node.js installations are not required. No API keys are needed to try the simulator and manual trading.

On macOS or Linux:

```bash
scripts/start_mac.sh   # build if needed, start, wait until healthy, open the browser
```

The first start builds the image, creates `.env` if it is missing, and waits for the health check before opening the browser. Open http://localhost:8000 to use the app. New portfolios start with $10,000 in simulated cash.

To check the backend and inspect container logs:

```bash
curl --fail http://localhost:8000/api/health
docker logs --tail 50 finally
```

To use another port, because 8000 is busy for example:

```bash
FINALLY_PORT=8030 scripts/start_mac.sh
```

`start_mac.sh` flags: `--build` rebuilds the image after a code change, and `--no-open` skips the browser. Running it again replaces the container.

On Windows PowerShell, from the same project directory:

```powershell
.\scripts\start_windows.ps1
```

Use `-Build` to rebuild, `-NoOpen` to skip opening a browser, or set `$env:FINALLY_PORT = "8030"` before starting to change the port. **The Windows scripts have not been run yet.**

The app is published on `127.0.0.1` only, because it has no login and its chat can place trades.

When finished, run `scripts/stop_mac.sh` (PowerShell: `.\scripts\stop_windows.ps1`) to stop and remove the container while keeping your data.

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

Install Python 3.12 or newer, `uv`, and Node.js 22 or newer with npm. The following commands use a macOS/Linux shell and start from the project directory.

In terminal 1, install the backend dependencies and start the API:

```bash
cd backend
uv sync --frozen
LLM_MOCK=true MASSIVE_API_KEY= DB_PATH=/tmp/finally.db uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload --timeout-graceful-shutdown 3
```

This uses mock chat, simulated prices, and a SQLite database outside the checkout. Keep the database outside synced folders such as Google Drive. The shutdown timeout lets the backend stop even when a browser has an open price stream.

In terminal 2, starting from the project directory, install and run the frontend:

```bash
cd frontend
npm ci
BACKEND_URL=http://127.0.0.1:8010 npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open http://localhost:3000. The frontend proxies `/api/*` to the backend on port 8010. Check the API directly at http://127.0.0.1:8010/api/health or view its interactive docs at http://127.0.0.1:8010/docs. Stop both servers with Ctrl+C; `/tmp/finally.db` persists until removed or cleared by the operating system.

For real services during local development, copy `.env.example` to `backend/.env`, add your keys there, and remove `LLM_MOCK=true MASSIVE_API_KEY=` from the backend command. Direct backend runs load `backend/.env`; the Docker start scripts instead pass the project-level `.env` into the container. Exported environment variables take precedence over `backend/.env`.

To serve a production frontend export through FastAPI without Docker, stop the development servers, run `npm run build` in `frontend/`, then run this from `backend/`:

```bash
LLM_MOCK=true MASSIVE_API_KEY= DB_PATH=/tmp/finally.db STATIC_DIR=../frontend/out uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --timeout-graceful-shutdown 3
```

Open http://localhost:8010 for the complete app.

## Troubleshooting

- **Docker is unavailable:** start Docker Desktop or the Docker daemon and retry `docker info`.
- **Port already in use:** set `FINALLY_PORT` for Docker, or choose another backend/frontend port locally and update `BACKEND_URL` to match.
- **Backend `/` returns 404:** without a frontend export this is expected. Use the frontend dev server on port 3000, or build the frontend and set `STATIC_DIR` as shown above.
- **Chat is not configured:** add `OPENROUTER_API_KEY` to the appropriate environment file, or use `LLM_MOCK=true` for mock replies. Restart after changing configuration.
- **OpenRouter rejected the API key:** use a key created in your OpenRouter account; keys from other providers cannot authenticate with OpenRouter. For Docker, update the project `.env` and rerun the start script so the container receives the new key. `docker restart` alone retains the old environment. For local development, update `backend/.env` and restart the backend.
- **Docker start fails its health check:** inspect `docker logs --tail 50 finally`. After code changes, restart with `scripts/start_mac.sh --build` (PowerShell: `.\scripts\start_windows.ps1 -Build`).

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
