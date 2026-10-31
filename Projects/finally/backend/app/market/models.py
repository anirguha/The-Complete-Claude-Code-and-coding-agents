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
