# FinAlly Team Contract

The shared contract for the agent team. `PLAN.md` is the product spec. Where the two disagree, this file wins. It settles the open items in `PLAN.md` Section 13, so do not re-decide them. If the contract is wrong or incomplete, make the smallest sensible choice, record it in the "Change log" at the end of this file, and mention it in your final report.

## Ground rules

- **Stay in your files.** Only edit the paths you own (see Ownership). Exception: the Integration Engineer may make minimal cross-component fixes.
- **Existing market code.** `backend/app/market/` exists, is committed, and passes its tests. It is the market data implementation, despite older doc wording. Build on it. Do not rewrite it.
- **Forbidden sources.** Never read, copy, or import from `finally/` at the repository root, `prelegal/finally/`, or git history.
- **No git commits, pushes, or branch changes.** Leave all work uncommitted in the working tree.
- **Secrets.** Never read, print, copy, or commit any `.env` file. The `.env` at the repository root (two levels above this project) is off limits. Use `LLM_MOCK=true` for all testing.
- **Tests are real.** Report actual results. Never skip, weaken, or delete a test to get a pass. Report what you could not verify.

## Environment notes

- This project lives on Google Drive. Keep SQLite databases out of the project tree during development and tests, because WAL files do not behave well on synced folders. Use `DB_PATH` pointing at `$TMPDIR` or a pytest `tmp_path`.
- Bash runs in a sandbox. Run `export UV_CACHE_DIR="$TMPDIR/uv-cache"` before `uv` commands. For npm, use `npm_config_cache="$TMPDIR/npm-cache"`. For Playwright, use `PLAYWRIGHT_BROWSERS_PATH="$TMPDIR/pw-browsers"`.
- Backend commands: `cd backend && uv run --frozen pytest`. Dependencies are already added and locked. Do not run `uv add` unless you truly need a new package, and record it in the change log if you do.
- Binding a local port may be blocked by the sandbox. If you get `EPERM`, retry that one command with the sandbox disabled and say so in your report.
- Network is filtered per command. When a host is denied, re-run with it in the Bash tool's `allowed_domains` (for example `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`, `cdn.playwright.dev`, `playwright.download.prss.microsoft.com`, and `registry-1.docker.io`).
- **Port 8000 on this machine is held by an unrelated container (`pm-pm-1`). Never stop, restart, or modify any container, image, or volume that is not FinAlly's.** For local runs use port 8010 or another free port. The app's default inside the container is still 8000; the host port is configurable through `FINALLY_PORT` in the start scripts (default 8000).
- Importing `litellm` fetches a price map from GitHub unless `LITELLM_LOCAL_MODEL_COST_MAP=True` is set first. `backend/app/llm/` must set it with `os.environ.setdefault` before importing `litellm`, so startup never depends on that network call.

## Ownership and build order

| Order | Agent                | Owns                                                                                                                  |
| ----- | -------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 1     | Database Engineer    | `backend/app/db/`, `backend/tests/db/`                                                                                |
| 1     | Frontend Engineer    | `frontend/`                                                                                                           |
| 2     | Backend Engineer     | `backend/app/main.py`, `backend/app/portfolio/`, `backend/app/api/`, `backend/tests/portfolio/`, `backend/tests/api/` |
| 3     | LLM Engineer         | `backend/app/llm/`, `backend/tests/llm/`; may add the chat router lines to `backend/app/main.py`                      |
| 4     | Integration Engineer | `test/`, `backend/tests/integration/`, `planning/INTEGRATION_REPORT.md`                                               |
| 5     | DevOps Engineer      | `Dockerfile`, `.dockerignore`, `scripts/`, `.env.example`, `.gitignore`, `db/.gitkeep`, `README.md`, `backend/README.md` |

## Settled decisions (PLAN.md Section 13)

| Item  | Decision                                                                                                                                                                                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 3     | Node 22 in the Dockerfile.                                                                                                                                                                                                     |
| 4, 32 | Tracked tickers = watchlist ∪ open positions. Removing a watched ticker stops its feed only if no position is held. Closing a position stops its feed only if it is not on the watchlist. SSE pushes every tracked ticker.     |
| 5     | Use `normalize_ticker` (uppercase, 1-5 letters, optional `.X` class such as `BRK.B`). The simulator accepts any valid symbol. Massive rejects symbols that do not exist.                                                       |
| 6     | No price available: 400 `"No price available for X"`. Trading a ticker not on the watchlist adds it to the watchlist automatically, once the trade succeeds.                                                                    |
| 7     | "Daily change %" is **session change**: measured from the first price the client received for that ticker. Label it `Session %` or similar.                                                                                    |
| 8     | Require `quantity > 0`. Round quantity to 4 decimals, then reject if it rounds to 0. Round cash and trade prices to 2 decimals and `avg_cost` to 4 at write time. A remaining quantity below 1e-6 means closed.                |
| 9     | Delete the position row when closed. Selling leaves `avg_cost` unchanged. Realized P&L is not tracked.                                                                                                                         |
| 10    | `users_profile.id` is the user id.                                                                                                                                                                                             |
| 11-12 | Chat response shape is below. Actions run independently and in order. Failures carry `error`. No second LLM call: the frontend shows failures inline.                                                                           |
| 13    | On any LLM failure (bad JSON, 30s timeout, API error): HTTP 200, friendly `message`, empty action arrays, error logged, and both the user message and the reply stored.                                                        |
| 14    | Send the last 20 messages as history.                                                                                                                                                                                          |
| 15    | Mock mode is defined below.                                                                                                                                                                                                    |
| 16    | Header total is computed on the client: cash + Σ(SSE price × quantity). Refetch `/api/portfolio` after each manual trade and after each chat response containing actions.                                                       |
| 17    | SSE payload is what `app/market/stream.py` already sends.                                                                                                                                                                      |
| 18    | The main chart shows ticks since page load. No history endpoint.                                                                                                                                                               |
| 19    | The app starts and runs without `OPENROUTER_API_KEY`. Without a key and with mock off, chat replies `"LLM not configured"` guidance with empty actions.                                                                         |
| 20    | `DB_PATH` env var, default `db/finally.db` relative to the working directory. WAL mode. Each trade is one transaction (cash, position, trade, snapshot).                                                                        |
| 21    | `/api/portfolio/history` returns at most the last 500 points, oldest first.                                                                                                                                                    |
| 22    | Register all `/api/*` routes before mounting static files at `/`.                                                                                                                                                              |
| 23    | Lightweight Charts for the main and P&L charts. Hand-rolled SVG sparklines. Heatmap is a small squarify function with absolutely positioned divs. No Recharts.                                                                  |
| 24    | **Keep prices** on `GET /api/watchlist`, as Section 8 specifies.                                                                                                                                                               |
| 25    | **Keep the Section 7 schema** (UUID primary keys plus UNIQUE constraints).                                                                                                                                                      |
| 26    | No `docker-compose.yml`.                                                                                                                                                                                                       |
| 27    | Playwright runs from the host against a running app with `LLM_MOCK=true`. No Playwright container. No automated SSE-resilience E2E scenario; cover the status dot logic in a frontend unit test.                                |
| 28    | Frontend unit tests target logic: P&L math, flash trigger, squarify, chat action rendering, connection status.                                                                                                                  |
| 29    | Massive mode is best effort and not covered by E2E.                                                                                                                                                                            |
| 30    | Initialize the database once, in the FastAPI lifespan handler.                                                                                                                                                                 |
| 31    | Schema and seed code live in `backend/app/db/`. Top-level `db/` is the runtime volume mount.                                                                                                                                    |
| 33    | The start script opens the browser by default on macOS; `--no-open` skips it.                                                                                                                                                  |

## Database API (`backend/app/db/`)

Synchronous stdlib `sqlite3`. Exported from `app.db`:

```python
class Database:
    def __init__(self, path: str | None = None): ...  # None -> DB_PATH env -> "db/finally.db"
    def init(self) -> None: ...  # Idempotent. Creates parent dir, tables, and seed data if missing.
    def connection(self) -> ContextManager[sqlite3.Connection]: ...
    # New connection per use, safe across threads. row_factory=sqlite3.Row, WAL, busy_timeout.
    # Commits on clean exit, rolls back on exception.
```

Repository functions take `conn` first and `user_id="default"` as the last keyword argument. Timestamps are UTC ISO-8601 strings generated inside these functions. Rows are returned as plain dicts.

```python
get_cash(conn) -> float
set_cash(conn, amount: float) -> None
list_watchlist(conn) -> list[str]                 # oldest first
add_watchlist(conn, ticker: str) -> bool          # True if inserted, False if already there
remove_watchlist(conn, ticker: str) -> bool       # True if removed
get_position(conn, ticker: str) -> dict | None    # {ticker, quantity, avg_cost, updated_at}
list_positions(conn) -> list[dict]                # ordered by ticker
upsert_position(conn, ticker: str, quantity: float, avg_cost: float) -> None
delete_position(conn, ticker: str) -> None
insert_trade(conn, ticker: str, side: str, quantity: float, price: float) -> dict  # {id, ticker, side, quantity, price, executed_at}
list_trades(conn, limit: int = 100) -> list[dict]           # newest first
insert_snapshot(conn, total_value: float) -> dict           # {id, total_value, recorded_at}
list_snapshots(conn, limit: int = 500) -> list[dict]        # latest `limit`, returned oldest first
insert_chat_message(conn, role: str, content: str, actions: dict | None = None) -> dict
list_chat_messages(conn, limit: int = 20) -> list[dict]     # latest `limit`, oldest first; `actions` decoded from JSON
```

## Service API (`backend/app/portfolio/service.py`)

```python
class ServiceError(ValueError):        # .message; business rule failures, mapped to HTTP 400
class NotFoundError(ServiceError):     # mapped to HTTP 404
class UnavailableError(ServiceError):  # wraps MarketDataUnavailableError, mapped to HTTP 503

class PortfolioService:
    def __init__(self, db: Database, cache: PriceCache, source: MarketDataSource): ...
    def get_portfolio(self) -> dict: ...                     # shape of GET /api/portfolio
    async def execute_trade(self, ticker: str, side: str, quantity: float) -> dict: ...  # the `trade` object below
    def list_watchlist(self) -> list[dict]: ...              # [{ticker, price}]
    async def add_watchlist(self, ticker: str) -> dict: ...  # {ticker, price}; idempotent
    async def remove_watchlist(self, ticker: str) -> dict: ...  # {ticker, removed: true}; NotFoundError if absent
    def record_snapshot(self) -> dict: ...
    def get_history(self, limit: int = 500) -> list[dict]: ...
    def tracked_tickers(self) -> list[str]: ...              # watchlist ∪ positions
```

`app/main.py` exposes `app` and `create_app()`. The lifespan handler: init the database, start the market source with `tracked_tickers()`, start the 30s snapshot task, and store services on `app.state` (`db`, `cache`, `source`, `portfolio`). Shutdown stops all of these cleanly.

Environment: read the `.env` at exactly `Path(__file__).parents[2] / ".env"` with `python-dotenv`, only if it exists and without overriding set variables. **Never use `find_dotenv` or any upward search**: it would pick up the repository-root `.env`. `STATIC_DIR` env var (default `static`, relative to the working directory) is the frontend export; mount it only if the directory exists.

## HTTP API

Business rule failures return 400, unknown resources 404, source outages 503, all with FastAPI's `{"detail": "message"}`. Malformed bodies return FastAPI's default 422.

```
GET  /api/health            200 {"status":"ok","market":{"source","mode","last_success_at","last_error"}}
GET  /api/stream/prices     SSE, one JSON object per event keyed by ticker:
                            {"AAPL":{"ticker","price","previous_price","timestamp","change","direction"}, ...}
                            timestamp is Unix seconds; direction is "up"|"down"|"flat"
GET  /api/portfolio         200 {"cash_balance","total_value","positions_value","unrealized_pnl",
                                 "positions":[{"ticker","quantity","avg_cost","current_price","market_value",
                                               "unrealized_pnl","pnl_percent","weight"}]}
                            current_price falls back to avg_cost if no price exists.
                            pnl_percent is 12.5 for 12.5%; weight is 0-1 of positions_value.
POST /api/portfolio/trade   body {"ticker","quantity","side"}; side "buy"|"sell"
                            200 {"trade":{"id","ticker","side","quantity","price","executed_at"},"portfolio":{...}}
GET  /api/portfolio/history 200 {"snapshots":[{"total_value","recorded_at"}]}
GET  /api/watchlist         200 {"watchlist":[{"ticker","price"}]}  price may be null
POST /api/watchlist         body {"ticker"}; 200 {"ticker","price"}; idempotent; invalid symbol 400
DELETE /api/watchlist/{t}   200 {"ticker","removed":true}; 404 if not on the watchlist
POST /api/chat              body {"message"}; 200 response below; blank message 422
GET  /api/chat/history      200 {"messages":[{"role","content","actions","created_at"}]}  latest 50, oldest first
```

Chat response (`actions` on stored assistant messages is `{"trades":[...],"watchlist_changes":[...]}` in the same shape):

```json
{
  "message": "...",
  "trades": [{ "ticker": "AAPL", "side": "buy", "quantity": 10, "status": "executed", "price": 191.2, "error": null }],
  "watchlist_changes": [{ "ticker": "PYPL", "action": "add", "status": "applied", "error": null }]
}
```

Trade `status` is `executed` or `failed` (`price` null on failure). Watchlist `status` is `applied` or `failed`; `action` is `add` or `remove`.

## LLM (`backend/app/llm/`)

Follow `.claude/skills/cerebras/SKILL.md`: model `openrouter/openai/gpt-oss-120b`, `extra_body={"provider":{"order":["cerebras"]}}`, `reasoning_effort="low"`, Pydantic `response_format`. Do not block the event loop (use `asyncio.to_thread` or `acompletion`). Timeout 30s.

```python
class ChatService:
    def __init__(self, db: Database, portfolio: PortfolioService, environ: Mapping[str,str] | None = None): ...
    async def handle_message(self, text: str) -> dict: ...  # the chat response
def create_chat_router(chat: ChatService) -> APIRouter: ...  # POST /api/chat, GET /api/chat/history
```

**Mock mode** (`LLM_MOCK=true`, case-insensitive; matching is case-insensitive against the whole trimmed message). No network, no key needed.

| User message             | Message returned                                         | Actions                 |
| ------------------------ | -------------------------------------------------------- | ----------------------- |
| `buy <qty> <TICKER>`     | `Mock: buying <qty> shares of <TICKER>.`                 | one buy trade           |
| `sell <qty> <TICKER>`    | `Mock: selling <qty> shares of <TICKER>.`                | one sell trade          |
| `add <TICKER>`           | `Mock: adding <TICKER> to your watchlist.`               | one watchlist add       |
| `remove <TICKER>`        | `Mock: removing <TICKER> from your watchlist.`           | one watchlist remove    |
| anything else            | `Mock response: I am FinAlly, your AI trading assistant.` | none                    |

## Frontend

Next.js + TypeScript, `output: 'export'`, Tailwind, produces `frontend/out`. All requests are same-origin to `/api/*`. Colors and layout per `PLAN.md` Sections 2 and 10. SSE delivers watchlist ∪ positions, so the watchlist panel must render only tickers from `/api/watchlist`.

### Stable test ids (the E2E suite depends on these)

```
header-total-value    header-cash    connection-status (data-status="connected|reconnecting|disconnected")
watchlist-row-{TICKER}    price-{TICKER}    watchlist-remove-{TICKER}    watchlist-add-input    watchlist-add-button
main-chart    main-chart-ticker    pnl-chart    heatmap    heatmap-cell-{TICKER}    position-row-{TICKER}
trade-ticker    trade-quantity    trade-buy    trade-sell    trade-error
chat-input    chat-send    chat-loading    chat-message (data-role="user|assistant")    chat-action (data-status)
```

`header-total-value` and `header-cash` show values formatted as `$10,000.00`.

## Change log

_Record contract changes here: date, agent, what changed, and why._

- 2026-10-31, Database Engineer: clarified the Database API; no signature changed. (1) `connection()` opens `BEGIN IMMEDIATE`, so read-check-write sequences such as trades cannot use a stale balance. It holds the write lock for the whole block: keep blocks short and **never `await` inside one**. (2) Repository writes enforce the Item 8 rounding themselves (cash, prices, `total_value` to 2 decimals; quantity and `avg_cost` to 4), and `insert_*` return the stored values. (3) `user_id` is keyword-only. (4) `get_cash` and `set_cash` raise `LookupError` for an unknown user. (5) Negative `limit` raises `ValueError`. (6) Tickers are stored as given: callers normalize first.
- 2026-10-31, Backend Engineer: (1) Item 6's auto-add applies to **buys only**. Selling an unwatched holding does not add it, because that would stop items 4 and 32 from ever ending its feed when the position closes. (2) A buy whose cost rounds to $0.00 is a 400, so shares cannot be free. (3) `DELETE /api/watchlist/{t}` with a malformed symbol is 404, not 400, since it cannot be on the watchlist. (4) `create_app(env_file=ENV_FILE, snapshot_seconds=30.0)`: tests must pass `env_file=None`. `app.main.app` is built on first access, so importing `create_app` reads no `.env`. (5) With static files mounted, an unknown method on a known API path (such as `PUT /api/watchlist`) returns a JSON 404 rather than 405.
- 2026-10-31, LLM Engineer: chat details the contract left open. (1) `POST /api/chat` messages are trimmed and limited to 4000 characters; over the limit is a 422. (2) Trades run before watchlist changes. (3) A reply with no usable `message`, or with `trades` or `watchlist_changes` that is not an array, fails as a whole and runs no actions. A bad item inside an array is one failed action. (4) A failed action echoes what the LLM sent, so `side` and `action` can hold other values, or `""`, when `status` is `failed`. An unusable `quantity` is reported as `0`, and a missing `ticker` as `""`. (5) An action hit by a market data outage reports a fixed message, not `UnavailableError`'s text, which can carry a raw upstream error. (6) History sent to the LLM adds an `[Action results: ...]` line to assistant turns, because the reply is written before its actions run. Stored and displayed content is unchanged. (7) Chat turns run one at a time per `ChatService`. (8) Mock `<TICKER>` is any single token, so `add NOT-A-TICKER` is a failed action and not the default row; the ticker is uppercased in the message and `<qty>` is echoed as typed.
- 2026-10-31, Integration Engineer: (1) **DevOps requirement:** the container's `uvicorn` command must pass `--timeout-graceful-shutdown 3`, because an open SSE stream otherwise blocks shutdown until `docker stop` kills the process (see `planning/INTEGRATION_REPORT.md`, defect 3). (2) The repository-root `.gitignore` has a `lib/` rule that ignored `frontend/src/lib/`; `frontend/.gitignore` now un-ignores it. (3) New test-only knobs: `E2E_BASE_URL` (default `http://localhost:8010`), `E2E_REQUIRE_FRESH=1` (fail rather than skip the first-launch test on a used database), and `E2E_SCREENSHOT_DIR`. The E2E suite sells all positions, so run it only on a throwaway volume.
- 2026-10-31, DevOps Engineer: (1) The start scripts publish on `127.0.0.1` only, not all interfaces, because the app has no login and chat can place trades. (2) The scripts pass `--stop-timeout 10` and `docker stop -t 10`, because this machine's Docker otherwise kills a container about 3s after SIGTERM, which beats uvicorn's 3s graceful shutdown (see `planning/INTEGRATION_REPORT.md`, Docker verification). (3) `.dockerignore` is an allow-list: only `backend/` and `frontend/` enter the build context. (4) `_mount_frontend` logs its missing-export message as a warning. Python's last-resort handler prints it, without uvicorn's `WARNING:` prefix.
