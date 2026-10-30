# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) is a Bloomberg-style trading terminal with an AI copilot. It streams live market data, lets you trade a simulated $10,000 portfolio, and includes a chat assistant that can analyze positions, execute trades, and manage your watchlist.

It is the capstone project for an agentic AI coding course, built entirely by coding agents.

> **Status: planning.** Only the specification exists so far. The application code and the commands below are not built yet.

## Planned Features

- Live watchlist with price flashes and sparklines, streamed over SSE
- Detailed price chart for the selected ticker
- Market orders with instant fills, no fees, and fractional shares
- Portfolio heatmap, P&L chart, and positions table
- AI chat that executes trades and watchlist changes automatically
- No login or signup; data persists in SQLite

## Stack

| Layer       | Technology                                                 |
| ----------- | ---------------------------------------------------------- |
| Frontend    | Next.js (TypeScript, static export), Tailwind CSS          |
| Backend     | FastAPI, managed with `uv`                                 |
| Database    | SQLite                                                     |
| Market data | Built-in GBM simulator, or the Massive API with a key      |
| AI          | LiteLLM → OpenRouter (Cerebras inference)                  |
| Deployment  | Single Docker container on port 8000                       |

## Quick Start (Planned)

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=your-openrouter-api-key-here  # AI chat
MASSIVE_API_KEY=                                 # Optional: real market data; simulator if empty
LLM_MOCK=false                                   # Optional: true for deterministic mock responses
```

Then start the app and open http://localhost:8000:

```bash
./scripts/start_mac.sh       # macOS/Linux
./scripts/start_windows.ps1  # Windows PowerShell
```

Stop it with `stop_mac.sh` or `stop_windows.ps1`. Your data persists in a Docker volume.

## Documentation

The full specification is in [`planning/PLAN.md`](planning/PLAN.md), including the architecture, API, database schema, and testing strategy.
