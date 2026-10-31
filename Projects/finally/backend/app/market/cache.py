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
