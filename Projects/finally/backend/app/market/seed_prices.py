"""Starting prices and per-ticker model parameters for the simulator."""

import random
from dataclasses import dataclass

DEFAULT_MU = 0.05
DEFAULT_SIGMA = 0.25
UNKNOWN_SEED_RANGE = (50.0, 300.0)

CROSS_SECTOR_CORR = 0.3  # correlation between any two tickers in different sectors
SECTOR_CORR = {"tech": 0.6, "finance": 0.5}  # correlation within a sector


@dataclass(frozen=True, slots=True)
class TickerParams:
    seed_price: float
    mu: float = DEFAULT_MU  # annualized drift
    sigma: float = DEFAULT_SIGMA  # annualized volatility
    sector: str | None = None  # a key of SECTOR_CORR, or None for market-only


KNOWN_TICKERS: dict[str, TickerParams] = {
    "AAPL": TickerParams(190.0, 0.05, 0.22, "tech"),
    "GOOGL": TickerParams(175.0, 0.05, 0.25, "tech"),
    "MSFT": TickerParams(420.0, 0.05, 0.20, "tech"),
    "AMZN": TickerParams(185.0, 0.05, 0.28, "tech"),
    "NVDA": TickerParams(800.0, 0.08, 0.40, "tech"),
    "META": TickerParams(500.0, 0.05, 0.30, "tech"),
    "NFLX": TickerParams(600.0, 0.05, 0.35, "tech"),
    "TSLA": TickerParams(250.0, 0.03, 0.50),  # high vol, moves on its own
    "JPM": TickerParams(195.0, 0.04, 0.18, "finance"),
    "V": TickerParams(280.0, 0.04, 0.17, "finance"),
}


def params_for(ticker: str) -> TickerParams:
    """Return a ticker's parameters. An unknown ticker's seed depends only on its symbol."""
    known = KNOWN_TICKERS.get(ticker)
    if known is not None:
        return known
    return TickerParams(random.Random(ticker).uniform(*UNKNOWN_SEED_RANGE))
