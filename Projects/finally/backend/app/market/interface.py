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
