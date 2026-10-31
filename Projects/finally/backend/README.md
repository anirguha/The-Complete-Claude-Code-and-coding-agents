# FinAlly backend

Market data subsystem lives in `app/market/`. Design docs: `../planning/MASSIVE_API.md`,
`../planning/MASSIVE_INTERFACE.md`, `../planning/MARKET_SIMULATOR.md`.

```bash
uv sync
uv run pytest
```

Env: `MASSIVE_API_KEY` (optional; simulator if unset), `MASSIVE_POLL_SECONDS` (default 5).
