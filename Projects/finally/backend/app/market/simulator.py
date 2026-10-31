"""The default market data source: correlated GBM prices with random events."""

import asyncio
import logging
import math
import random
import time
from collections.abc import Iterable

from .cache import PriceCache
from .interface import MarketDataSource
from .models import SourceStatus, normalize_ticker
from .seed_prices import CROSS_SECTOR_CORR, SECTOR_CORR, TickerParams, params_for

logger = logging.getLogger(__name__)

TICK_SECONDS = 0.5
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
EVENT_PROBABILITY = 0.0005  # per ticker, per tick
EVENT_SIZE_RANGE = (0.02, 0.05)


class GBMSimulator:
    """Pure price model: no clock, no I/O, deterministic for a given rng."""

    def __init__(
        self,
        tick_seconds: float = TICK_SECONDS,
        event_probability: float = EVENT_PROBABILITY,
        rng: random.Random | None = None,
    ) -> None:
        self._dt = tick_seconds / TRADING_SECONDS_PER_YEAR
        self._event_probability = event_probability
        self._rng = rng or random.Random()
        self._params: dict[str, TickerParams] = {}
        self._prices: dict[str, float] = {}

    def add_ticker(self, ticker: str) -> float:
        """Start simulating a ticker, if new, and return its current price."""
        if ticker not in self._prices:
            self._params[ticker] = params_for(ticker)
            self._prices[ticker] = self._params[ticker].seed_price
        return self._prices[ticker]

    def remove_ticker(self, ticker: str) -> None:
        self._params.pop(ticker, None)
        self._prices.pop(ticker, None)

    def step(self) -> dict[str, float]:
        """Advance every ticker by one tick and return the new prices."""
        gauss = self._rng.gauss
        market = gauss(0.0, 1.0)
        sectors = {name: gauss(0.0, 1.0) for name in SECTOR_CORR}
        for ticker, params in self._params.items():
            z = self._correlated_normal(params.sector, market, sectors)
            drift = (params.mu - 0.5 * params.sigma**2) * self._dt
            diffusion = params.sigma * math.sqrt(self._dt) * z
            self._prices[ticker] *= math.exp(drift + diffusion + self._event_return())
        return dict(self._prices)

    def _correlated_normal(
        self, sector: str | None, market: float, sectors: dict[str, float]
    ) -> float:
        """Mix shared and individual shocks into one standard normal.

        Two tickers correlate by the variance they share: CROSS_SECTOR_CORR
        from the market shock, plus the rest of SECTOR_CORR from a sector shock.
        """
        sector_corr = SECTOR_CORR[sector] if sector else CROSS_SECTOR_CORR
        z = math.sqrt(CROSS_SECTOR_CORR) * market
        if sector:
            z += math.sqrt(sector_corr - CROSS_SECTOR_CORR) * sectors[sector]
        return z + math.sqrt(1.0 - sector_corr) * self._rng.gauss(0.0, 1.0)

    def _event_return(self) -> float:
        """Return a log return of about +/-2-5% on the rare tick with an event, else 0."""
        if self._rng.random() >= self._event_probability:
            return 0.0
        size = self._rng.uniform(*EVENT_SIZE_RANGE)
        return size if self._rng.random() < 0.5 else -size


class SimulatorDataSource(MarketDataSource):
    """Runs a GBMSimulator in a background task and writes prices to the cache."""

    def __init__(
        self,
        cache: PriceCache,
        tick_seconds: float = TICK_SECONDS,
        simulator: GBMSimulator | None = None,
    ) -> None:
        self._cache = cache
        self._tick_seconds = tick_seconds
        self._simulator = simulator or GBMSimulator(tick_seconds=tick_seconds)
        self._tickers: set[str] = set()
        self._task: asyncio.Task[None] | None = None
        self._last_success_at: float | None = None
        self._last_error: str | None = None

    async def start(self, tickers: Iterable[str]) -> None:
        for ticker in tickers:
            await self.add_ticker(ticker)
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="market-simulator")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def add_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        if symbol not in self._tickers:
            self._tickers.add(symbol)
            # Priced now, so a ticker can be traded the moment it is added.
            self._cache.update(symbol, self._simulator.add_ticker(symbol))

    async def remove_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        self._tickers.discard(symbol)
        self._simulator.remove_ticker(symbol)
        self._cache.remove(symbol)

    def get_tickers(self) -> list[str]:
        return sorted(self._tickers)

    def status(self) -> SourceStatus:
        return SourceStatus(
            "simulator", "simulated", self._last_success_at, self._last_error
        )

    async def _run(self) -> None:
        while True:
            try:
                now = time.time()
                for ticker, price in self._simulator.step().items():
                    self._cache.update(ticker, price, now)
                self._last_success_at, self._last_error = now, None
            except Exception as exc:  # one bad tick must not end the price feed
                logger.exception("Simulator tick failed")
                self._last_error = str(exc)
            await asyncio.sleep(self._tick_seconds)
