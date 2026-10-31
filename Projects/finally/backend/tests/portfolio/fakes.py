"""A market source with prices the test controls."""

import asyncio
from collections.abc import Iterable

from app.market import MarketDataSource, PriceCache, SourceStatus, normalize_ticker


class FakeSource(MarketDataSource):
    def __init__(self, cache: PriceCache, default_price: float | None = 100.0) -> None:
        self.cache = cache
        self.default_price = default_price
        self.tickers: set[str] = set()
        self.add_errors: dict[str, Exception] = {}
        self.remove_errors: list[Exception] = []
        self.start_calls: list[list[str]] = []
        self.stop_calls = 0
        self._clock = 0.0

    def set_price(self, ticker: str, price: float) -> None:
        self._clock += 1.0
        self.cache.update(ticker, price, self._clock)

    async def start(self, tickers: Iterable[str]) -> None:
        tickers = list(tickers)
        self.start_calls.append(tickers)
        for ticker in tickers:
            await self.add_ticker(ticker)

    async def stop(self) -> None:
        self.stop_calls += 1

    async def add_ticker(self, ticker: str) -> None:
        symbol = normalize_ticker(ticker)
        await asyncio.sleep(0)  # give other tasks a chance to interleave
        if symbol in self.add_errors:
            raise self.add_errors[symbol]
        if symbol not in self.tickers:
            self.tickers.add(symbol)
            if self.default_price is not None:
                self.set_price(symbol, self.default_price)

    async def remove_ticker(self, ticker: str) -> None:
        if self.remove_errors:
            raise self.remove_errors.pop()
        symbol = normalize_ticker(ticker)
        self.tickers.discard(symbol)
        self.cache.remove(symbol)

    def get_tickers(self) -> list[str]:
        return sorted(self.tickers)

    def status(self) -> SourceStatus:
        return SourceStatus("simulator", "simulated")
