# Unified Market Data Interface

The Python API FinAlly uses to get stock prices: Massive when `MASSIVE_API_KEY` is set, otherwise a built-in simulator. Everything outside `backend/app/market/` uses this one interface and does not know which source is running.

- API research: [`MASSIVE_API.md`](MASSIVE_API.md)
- Simulator design: [`MARKET_SIMULATOR.md`](MARKET_SIMULATOR.md)

**Status:** Design, to be built in `backend/app/market/`. The code below comes from a prototype that passed 35 tests against a local imitation of the Massive API. It has not yet run against a live snapshot, because the available key has no snapshot access (see [Open risks](#open-risks)).

## Overview

```
                 create_market_data_source()
                 MASSIVE_API_KEY set and non-blank?
                       │                 │
                      yes                no
                       ▼                 ▼
             MassiveDataSource    SimulatorDataSource
                       │                 │
                       └───────┬─────────┘
                       writes  ▼
                          PriceCache
                               │ reads
              ┌────────────────┼─────────────────┐
              ▼                ▼                 ▼
         SSE stream     Portfolio value    Trade execution
```

Three rules hold it together:

1. **Sources push and consumers pull.** A source writes to the cache on its own schedule. Nothing asks a source for a price, so no request ever waits on the network.
2. **`PriceUpdate` is the only price type that leaves this package.** Massive's models stay inside `massive_client.py`.
3. **Only the factory reads the environment.** Everything else receives its settings as arguments, which keeps it easy to test.

## How the source is chosen

| `MASSIVE_API_KEY` | Plan | Source | Mode | What the user sees |
| ---------------- | ---------------------- | ------------------- | ----------- | ------------------------------------------ |
| Absent or blank | n/a | Simulator | `simulated` | Prices tick every 500ms |
| Set | Advanced | Massive | `live` | Real-time prices, every poll |
| Set | Starter or Developer | Massive | `live` | Prices delayed 15 minutes |
| Set | Basic (free) | Massive | `eod` | **Last close, which does not tick** |
| Set but invalid | n/a | Massive | `live` | **No prices**, error in `status()` |

The last two rows are deliberate decisions:

- **A free key shows real closing prices, not simulated ones.** `PLAN.md` says to use Massive when a key is present, and quietly showing made-up prices to someone who supplied a real key would be misleading. The price feed looks frozen, so the UI should show the mode, and the log says how to change it: unset the key to get the simulator, or upgrade.
- **An invalid key fails visibly.** It does not fall back to the simulator, for the same reason. The app keeps running and logs the error.

### Changes to the plan

`PLAN.md` Section 6 says the free tier can poll every 15 seconds. It cannot: Basic has no snapshot access and its data is end-of-day, so polling faster would return the same closing prices. Single-ticker requests don't help either, since 5 requests a minute cannot cover 10 tickers every 15 seconds. This design replaces that with `eod` mode, and uses a 5-second default for paid plans, whose calls are unlimited.

It also assumes these suggestions from `PLAN.md` Section 13, which are not yet formally accepted:

| Item | Assumed here |
| ---- | ---------------------------------------------------------------------- |
| 4 | Tracked tickers are the watchlist plus open positions |
| 5 | The simulator accepts any valid symbol, and Massive rejects unknown ones |
| 6 | A ticker with no price yet can't be traded |
| 8 | Prices are rounded to 2 decimals when written |
| 17 | The SSE payload is a JSON object keyed by ticker |
| 31 | Code lives under `backend/app/` |

Item 5 is extended to allow class-share symbols like `BRK.B`, which the Massive reference endpoint recognizes.

## Using it

```python
from app.market import PriceCache, create_market_data_source

# App startup, in the FastAPI lifespan handler
cache = PriceCache()
source = create_market_data_source(cache)
await source.start(["AAPL", "GOOGL", "MSFT"])  # watchlist plus open positions

# Read prices from anywhere
update = cache.get("AAPL")        # PriceUpdate, or None if there is no price yet
price = cache.get_price("AAPL")   # float, or None
everything = cache.get_all()      # dict[str, PriceUpdate]

# Change what is tracked
await source.add_ticker("pypl")   # case-insensitive
await source.remove_ticker("GOOGL")

# Report health
status = source.status()          # SourceStatus(source, mode, last_success_at, last_error)

# App shutdown
await source.stop()
```

### Integration rules

- **Removing from the watchlist.** Call `remove_ticker` only when the ticker has no open position, otherwise the portfolio can no longer be valued. Likewise, when a sale closes a position, remove the ticker if it isn't on the watchlist.
- **Trading.** Read the price from `cache.get_price()`. If it returns `None`, reject the trade with a 400 and "no price available".
- **Adding a ticker.** Map the errors to responses:

```python
from fastapi import HTTPException

from app.market import InvalidTickerError, MarketDataUnavailableError

try:
    await source.add_ticker(ticker)
except InvalidTickerError as error:
    raise HTTPException(status_code=400, detail=str(error))
except MarketDataUnavailableError as error:
    raise HTTPException(status_code=503, detail=str(error))
```

- **Health and UI.** Include `source.status()` in `GET /api/health`. When `mode` is `eod`, show a label such as "End-of-day prices" so a still price feed doesn't look like a bug. `live` may be delayed by 15 minutes, since the API doesn't report which plan a key has.

## Configuration

| Variable | Default | Effect |
| ---------------------- | -------- | ------------------------------------------------- |
| `MASSIVE_API_KEY` | not set | Selects Massive when set and non-blank |
| `MASSIVE_POLL_SECONDS` | `5` | Seconds between snapshot polls in `live` mode |

`MASSIVE_POLL_SECONDS` is new: add it to `.env.example`.

Dependencies for `backend/pyproject.toml`: `massive>=2.9,<3` and `tzdata`. The `tzdata` package is needed because slim Docker images may not include the time zone database.

## Code structure

```
backend/app/market/
├── __init__.py         # Public API
├── models.py           # PriceUpdate, SourceStatus, errors, normalize_ticker
├── cache.py            # PriceCache
├── interface.py        # MarketDataSource
├── factory.py          # create_market_data_source
├── massive_client.py   # MassiveDataSource
├── simulator.py        # GBMSimulator, SimulatorDataSource
├── seed_prices.py      # Simulator parameters
└── stream.py           # SSE endpoint
```

`simulator.py` and `seed_prices.py` are in [`MARKET_SIMULATOR.md`](MARKET_SIMULATOR.md). The rest follows.

### Public API: `__init__.py`

```python
"""Market data subsystem: one interface, two sources, one shared price cache."""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import (
    InvalidTickerError,
    MarketDataUnavailableError,
    PriceUpdate,
    SourceStatus,
    normalize_ticker,
)

__all__ = [
    "InvalidTickerError",
    "MarketDataSource",
    "MarketDataUnavailableError",
    "PriceCache",
    "PriceUpdate",
    "SourceStatus",
    "create_market_data_source",
    "normalize_ticker",
]
```

### Data types: `models.py`

```python
"""Data types and errors that cross the market data boundary."""

import re
from dataclasses import dataclass
from typing import Literal

Direction = Literal["up", "down", "flat"]
SourceMode = Literal["simulated", "live", "eod"]

_TICKER_RE = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")  # AAPL, V, BRK.B


class InvalidTickerError(ValueError):
    """The ticker is malformed, or the data source says it does not exist."""


class MarketDataUnavailableError(RuntimeError):
    """The source could not answer right now (network failure, rate limit)."""


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """The latest price for one ticker. Field names are the SSE wire format."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float  # Unix seconds
    change: float  # price - previous_price
    direction: Direction


@dataclass(frozen=True, slots=True)
class SourceStatus:
    """What a data source is doing, for /api/health and the UI."""

    source: Literal["simulator", "massive"]
    mode: SourceMode
    last_success_at: float | None = None  # Unix seconds
    last_error: str | None = None


def normalize_ticker(ticker: str) -> str:
    """Return the canonical uppercase symbol, or raise InvalidTickerError."""
    symbol = ticker.strip().upper()
    if not _TICKER_RE.fullmatch(symbol):
        raise InvalidTickerError(f"Invalid ticker: {ticker!r}")
    return symbol
```

### Price cache: `cache.py`

Ignoring data that isn't newer matters for polling: if a poll returns the same trade as last time, nothing changes, so the UI doesn't flash for a price that didn't move.

```python
"""In-memory store of the latest price per ticker."""

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Sources write here; SSE, valuation and trade execution read from here."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()  # FastAPI runs sync routes on worker threads
        self._version = 0

    def update(
        self, ticker: str, price: float, timestamp: float | None = None
    ) -> PriceUpdate:
        """Record a price, rounded to cents. Data not newer than the stored price is ignored."""
        ts = time.time() if timestamp is None else timestamp
        price = round(price, 2)
        with self._lock:
            current = self._prices.get(ticker)
            if current is not None and ts <= current.timestamp:
                return current
            previous = current.price if current else price
            if price > previous:
                direction = "up"
            elif price < previous:
                direction = "down"
            else:
                direction = "flat"
            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=previous,
                timestamp=ts,
                change=round(price - previous, 2),
                direction=direction,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        update = self.get(ticker)
        return update.price if update else None

    def get_all(self) -> dict[str, PriceUpdate]:
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            if self._prices.pop(ticker, None) is not None:
                self._version += 1

    @property
    def version(self) -> int:
        """Increases on every change, so SSE can skip ticks with nothing new."""
        with self._lock:
            return self._version
```

### The contract: `interface.py`

```python
"""The contract both market data sources implement."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .models import SourceStatus


class MarketDataSource(ABC):
    """Produces prices into a PriceCache on its own schedule.

    Prices are never returned from these methods. Read them from the cache.
    Tickers may be passed in any case; implementations normalize them.
    """

    @abstractmethod
    async def start(self, tickers: Iterable[str]) -> None:
        """Begin producing prices. Failures are reported through status(), not raised."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop producing prices. Safe to call more than once."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Track a ticker. Safe to repeat.

        Raises InvalidTickerError if it is malformed or does not exist, and
        MarketDataUnavailableError if that could not be checked right now.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and drop it from the cache. Safe to repeat."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the tracked tickers, sorted."""

    @abstractmethod
    def status(self) -> SourceStatus:
        """Return the source's current mode and health."""
```

### Source selection: `factory.py`

```python
"""Chooses the market data source from the environment."""

import logging
import os
from collections.abc import Mapping

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import DEFAULT_POLL_SECONDS, MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(
    cache: PriceCache, environ: Mapping[str, str] | None = None
) -> MarketDataSource:
    """Return Massive if MASSIVE_API_KEY is set and non-blank, else the simulator."""
    env = os.environ if environ is None else environ
    api_key = env.get("MASSIVE_API_KEY", "").strip()
    if not api_key:
        logger.info("MASSIVE_API_KEY not set: using the market simulator")
        return SimulatorDataSource(cache)
    poll_seconds = float(env.get("MASSIVE_POLL_SECONDS") or DEFAULT_POLL_SECONDS)
    logger.info("Using the Massive API, polling every %.1fs", poll_seconds)
    return MassiveDataSource(cache, api_key, poll_seconds)
```

### Massive source: `massive_client.py`

```python
"""Market data source backed by the Massive REST API."""

import asyncio
import json
import logging
import time
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from massive import RESTClient
from massive.exceptions import BadResponse
from massive.rest.models import TickerSnapshot
from urllib3.exceptions import HTTPError

from .cache import PriceCache
from .interface import MarketDataSource
from .models import (
    InvalidTickerError,
    MarketDataUnavailableError,
    SourceMode,
    SourceStatus,
    normalize_ticker,
)

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 5.0
EOD_REFRESH_SECONDS = 3600.0
MAX_BACKOFF_SECONDS = 60.0
EOD_PROBE_TICKER = "SPY"  # any always-traded ticker reveals the last trading day
EASTERN = ZoneInfo("America/New_York")

# Everything the client raises for a failed request. 429 and 5xx responses
# arrive as urllib3's MaxRetryError, not as BadResponse.
REQUEST_ERRORS = (BadResponse, HTTPError)


def to_unix_seconds(timestamp: float) -> float:
    """Convert a Massive timestamp, which may be in s, ms or ns, to Unix seconds."""
    if timestamp >= 1e17:
        return timestamp / 1e9
    if timestamp >= 1e11:
        return timestamp / 1e3
    return float(timestamp)


def trading_date(timestamp_ms: int) -> str:
    """Return the Eastern date of a daily bar, whichever end of the day it is stamped with."""
    return datetime.fromtimestamp(timestamp_ms / 1000, EASTERN).date().isoformat()


def parse_snapshot(snapshot: TickerSnapshot) -> tuple[float, float] | None:
    """Return (price, unix_seconds) from a snapshot, or None if it has no usable price.

    Plans differ in what they return: lastTrade needs the Developer plan or
    higher, so Starter prices come from the minute bar. Fields can also be
    missing or zero just after the daily reset, hence the fallbacks.
    """
    trade, minute = snapshot.last_trade, snapshot.min
    if trade and trade.price and trade.sip_timestamp:
        return trade.price, to_unix_seconds(trade.sip_timestamp)
    if minute and minute.close and minute.timestamp:
        return minute.close, to_unix_seconds(minute.timestamp)
    updated = to_unix_seconds(snapshot.updated) if snapshot.updated else time.time()
    for bar in (snapshot.day, snapshot.prev_day):
        if bar and bar.close:
            return bar.close, updated
    return None


def _error_body(exc: Exception) -> dict[str, Any]:
    """Parse a BadResponse, whose only content is the response body. It carries no status code."""
    try:
        body = json.loads(str(exc))
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def is_not_entitled(exc: Exception) -> bool:
    """True if the key is valid but its plan does not include this endpoint."""
    if not isinstance(exc, BadResponse):
        return False
    text = str(exc).lower()
    return "not_authorized" in text or "not entitled" in text


def is_not_found(exc: Exception) -> bool:
    return isinstance(exc, BadResponse) and _error_body(exc).get("status") == "NOT_FOUND"


class MassiveDataSource(MarketDataSource):
    """Polls Massive and writes prices to the cache.

    Starts in "live" mode, polling the multi-ticker snapshot. A key whose plan
    excludes snapshots (the free Basic plan) drops to "eod" mode: real closing
    prices from the daily market summary, refreshed hourly, that do not tick.
    """

    def __init__(
        self,
        cache: PriceCache,
        api_key: str,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        client: RESTClient | None = None,
    ) -> None:
        self._cache = cache
        self._poll_seconds = poll_seconds
        # No client retries: each one spends quota, and the poll loop retries anyway.
        self._client = client or RESTClient(
            api_key, connect_timeout=3.0, read_timeout=5.0, retries=0
        )
        self._tickers: set[str] = set()
        self._task: asyncio.Task[None] | None = None
        self._mode: SourceMode = "live"
        self._eod_date: str | None = None
        self._eod_closes: dict[str, tuple[float, float]] = {}
        self._last_success_at: float | None = None
        self._last_error: str | None = None

    async def start(self, tickers: Iterable[str]) -> None:
        self._tickers.update(normalize_ticker(t) for t in tickers)
        if self._task is None:
            # Polling starts in the background so a slow API cannot delay app startup.
            self._task = asyncio.create_task(self._run(), name="massive-poller")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def add_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        if symbol in self._tickers:
            return
        if symbol not in self._eod_closes:
            await self._require_exists(symbol)
        self._tickers.add(symbol)
        await self._price_new_ticker(symbol)

    async def remove_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        self._tickers.discard(symbol)
        self._cache.remove(symbol)

    def get_tickers(self) -> list[str]:
        return sorted(self._tickers)

    def status(self) -> SourceStatus:
        return SourceStatus(
            "massive", self._mode, self._last_success_at, self._last_error
        )

    async def _run(self) -> None:
        failures = 0
        while True:
            try:
                await self._refresh()
                self._last_success_at, self._last_error = time.time(), None
                failures = 0
            except REQUEST_ERRORS as exc:
                failures += 1
                self._last_error = str(exc)
                logger.warning("Massive request failed (%d): %s", failures, exc)
            except Exception as exc:  # one bad poll must not end the price feed
                failures += 1
                self._last_error = str(exc)
                logger.exception("Massive poll failed")
            await asyncio.sleep(self._delay(failures))

    def _delay(self, failures: int) -> float:
        if failures:
            return min(MAX_BACKOFF_SECONDS, self._poll_seconds * 2**failures)
        return EOD_REFRESH_SECONDS if self._mode == "eod" else self._poll_seconds

    async def _refresh(self) -> None:
        if self._mode == "live":
            try:
                await self._refresh_live()
                return
            except BadResponse as exc:
                if not is_not_entitled(exc):
                    raise
                logger.warning(
                    "This Massive plan has no snapshot access. Showing end-of-day "
                    "prices, which will not tick. Unset MASSIVE_API_KEY to use the "
                    "simulator, or upgrade to Stocks Starter or higher."
                )
                self._mode = "eod"
        await self._refresh_eod()

    async def _refresh_live(self) -> None:
        tickers = self.get_tickers()
        if not tickers:
            return
        snapshots = await asyncio.to_thread(
            self._client.get_snapshot_all, "stocks", tickers
        )
        for snapshot in snapshots:
            parsed = parse_snapshot(snapshot)
            # Re-check: the ticker may have been removed during the request.
            if parsed and snapshot.ticker in self._tickers:
                self._cache.update(snapshot.ticker, *parsed)

    async def _refresh_eod(self) -> None:
        probe = await asyncio.to_thread(
            self._client.get_previous_close_agg, EOD_PROBE_TICKER
        )
        if not probe:
            return
        date = trading_date(probe[0].timestamp)  # the client returns a list here
        if date != self._eod_date:
            bars = await asyncio.to_thread(self._client.get_grouped_daily_aggs, date)
            self._eod_closes = {
                bar.ticker: (bar.close, to_unix_seconds(bar.timestamp))
                for bar in bars
                if bar.close
            }
            self._eod_date = date
        for ticker in self.get_tickers():
            if ticker in self._eod_closes:
                self._cache.update(ticker, *self._eod_closes[ticker])

    async def _require_exists(self, symbol: str) -> None:
        try:
            await asyncio.to_thread(self._client.get_ticker_details, symbol)
        except REQUEST_ERRORS as exc:
            if is_not_found(exc):
                raise InvalidTickerError(f"Unknown ticker: {symbol}") from exc
            raise MarketDataUnavailableError(
                f"Could not check ticker {symbol}: {exc}"
            ) from exc

    async def _price_new_ticker(self, symbol: str) -> None:
        """Price a ticker now rather than at the next poll. On failure, the next poll covers it."""
        if symbol in self._eod_closes:
            self._cache.update(symbol, *self._eod_closes[symbol])
        elif self._mode == "live":
            try:
                snapshots = await asyncio.to_thread(
                    self._client.get_snapshot_all, "stocks", [symbol]
                )
            except REQUEST_ERRORS as exc:
                logger.warning("Could not price %s yet: %s", symbol, exc)
                return
            parsed = parse_snapshot(snapshots[0]) if snapshots else None
            if parsed and symbol in self._tickers:
                self._cache.update(symbol, *parsed)
```

How it behaves:

| Situation | Behaviour |
| --------------------------- | ------------------------------------------------------------------------------------ |
| First poll on a Basic key | Snapshot returns 403, so it moves to `eod` for good. Uses 3 requests of the 5 a minute |
| `eod` mode, each hour | 1 request to find the date, and 1 more only if the date has changed |
| Adding a ticker in `eod` | No request if the ticker is in the last daily summary, otherwise 1 request to validate |
| Adding a ticker in `live` | 2 requests: validate, then price it straight away |
| Network failure or 429 | Keeps the last prices and retries after 10, 20, 40, then 60 seconds at most |
| Ticker removed mid-request | Result ignored, so the ticker doesn't reappear |
| Invalid key | Logs, sets `last_error`, keeps retrying. The cache stays empty |
| Market closed | Polls continue, and unchanged data is ignored by the cache |

### SSE endpoint: `stream.py`

`GET /api/stream/prices`. The client uses the browser's native `EventSource`. Each event is the full set of tracked tickers, which also tells the client when a ticker has been removed.

```python
"""SSE endpoint: GET /api/stream/prices."""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .cache import PriceCache

STREAM_INTERVAL_SECONDS = 0.5


async def price_events(
    cache: PriceCache, interval: float = STREAM_INTERVAL_SECONDS
) -> AsyncIterator[str]:
    """Yield one SSE event per change: a JSON object keyed by ticker."""
    last_version = None
    while True:
        version = cache.version
        if version != last_version:
            last_version = version
            payload = {t: asdict(u) for t, u in cache.get_all().items()}
            yield f"data: {json.dumps(payload)}\n\n"
        else:
            yield ": keep-alive\n\n"  # comment line, ignored by EventSource
        await asyncio.sleep(interval)


def create_stream_router(cache: PriceCache) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices() -> StreamingResponse:
        return StreamingResponse(
            price_events(cache),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
```

Event format:

```
data: {"AAPL": {"ticker": "AAPL", "price": 190.12, "previous_price": 190.1, "timestamp": 1793304000.5, "change": 0.02, "direction": "up"}}
```

When nothing has changed, the stream sends a comment line instead, so the connection stays open and the client doesn't see a stale tick. This is the normal case in `eod` mode and between Massive polls.

## Daily change

`PriceUpdate` carries only the change since the previous update. As `PLAN.md` Section 13 item 7 suggests, the frontend works out "daily change %" from the first price it receives, labelled as change since session start. That works the same for both sources. Massive's `todaysChangePerc` is deliberately unused, because the simulator has no equivalent.

## Testing

Tests live in `backend/tests/market/`. These are the cases the prototype covered:

| Area | Cases |
| ----------- | ---------------------------------------------------------------------------------------- |
| Tickers | Normalization, and rejecting malformed symbols |
| Cache | Direction and change, rounding, ignoring older data, version counter, removal |
| Factory | Absent, empty and blank keys select the simulator. Set keys select Massive. Poll setting |
| Parsing | Timestamp units, Eastern dates, each price fallback, empty snapshots |
| Client | Real `massive` client over a fake transport, including which exception each failure raises |
| Massive | Live polling, move to `eod`, unknown tickers, invalid key, outage and recovery, backoff, removal during a request |
| SSE | Payload shape, keep-alive when idle |

For Massive tests, replace urllib3's wire call rather than mocking the client. Mocks would have hidden the two most important client behaviours: 429s raising `MaxRetryError`, and `get_previous_close_agg` returning a list despite its type hint. Simulator tests are in [`MARKET_SIMULATOR.md`](MARKET_SIMULATOR.md#testing).

## Open risks

1. **`live` mode has not run against the real snapshot endpoint.** Field parsing follows the docs and the client's models. Run the `curl` command in [`MASSIVE_API.md`](MASSIVE_API.md#still-unverified) with a Starter or higher key before relying on this mode.
2. **Moving to `eod` depends on the wording of a 403 body that hasn't been seen live.** If the wording differs, a Basic key would stay in `live` mode showing no prices, with the error in `status()`. The fix is one line in `is_not_entitled`.
3. **Starter may update only about once a minute,** if its only price source is the minute bar.
