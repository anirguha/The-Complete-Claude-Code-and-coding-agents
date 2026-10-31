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
