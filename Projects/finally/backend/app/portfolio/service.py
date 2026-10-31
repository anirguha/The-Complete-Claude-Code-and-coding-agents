"""Trade execution, valuation and the tracked-ticker rule.

Tracked tickers are the watchlist plus open positions. The database decides
what is tracked; the market source follows it. A source can be told about a
ticker before the database changes (a trade needs a price first), so every
mutation ends by dropping feeds the database no longer justifies. That one step
covers failed trades, closed positions and removed tickers, and it repairs any
earlier removal that failed.
"""

import asyncio
import logging
import math
import sqlite3
from typing import Any

from .. import db as repo
from ..db import Database
from ..market import (
    InvalidTickerError,
    MarketDataSource,
    MarketDataUnavailableError,
    PriceCache,
    normalize_ticker,
)

logger = logging.getLogger(__name__)

QUANTITY_DECIMALS = 4
CLOSED_POSITION_EPSILON = 1e-6
DEFAULT_HISTORY_LIMIT = 500


class ServiceError(ValueError):
    """A business rule failure. Mapped to HTTP 400."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    """The resource does not exist. Mapped to HTTP 404."""


class UnavailableError(ServiceError):
    """The market source could not answer right now. Mapped to HTTP 503."""


def _normalize(ticker: str) -> str:
    try:
        return normalize_ticker(ticker)
    except InvalidTickerError as exc:
        raise ServiceError(str(exc)) from exc


def _validate_side(side: str) -> str:
    if side not in ("buy", "sell"):
        raise ServiceError(f"Invalid side: {side!r}. Use 'buy' or 'sell'")
    return side


def _validate_quantity(quantity: float) -> float:
    is_number = isinstance(quantity, (int, float)) and not isinstance(quantity, bool)
    if not is_number or not math.isfinite(quantity) or quantity <= 0:
        raise ServiceError("Quantity must be greater than 0")
    rounded = round(float(quantity), QUANTITY_DECIMALS)
    if rounded == 0:
        raise ServiceError("Quantity is too small: the minimum is 0.0001")
    return rounded


def _position_row(
    position: dict[str, Any], price: float, positions_value: float
) -> dict[str, Any]:
    quantity, avg_cost = position["quantity"], position["avg_cost"]
    market_value = quantity * price
    return {
        "ticker": position["ticker"],
        "quantity": quantity,
        "avg_cost": avg_cost,
        "current_price": price,
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(quantity * (price - avg_cost), 2),
        "pnl_percent": round((price - avg_cost) / avg_cost * 100, 2) if avg_cost else 0.0,
        "weight": round(market_value / positions_value, 4) if positions_value else 0.0,
    }


class PortfolioService:
    def __init__(self, db: Database, cache: PriceCache, source: MarketDataSource) -> None:
        self._db = db
        self._cache = cache
        self._source = source
        # Serializes changes that span the source and the database. The cash
        # check itself is protected by the database transaction.
        self._lock = asyncio.Lock()

    # Reads

    def get_portfolio(self) -> dict[str, Any]:
        with self._db.connection() as conn:
            cash = repo.get_cash(conn)
            positions = repo.list_positions(conn)

        # Price each position once, so the totals agree with the rows.
        priced = [(p, self._mark_price(p)) for p in positions]
        positions_value = sum(p["quantity"] * price for p, price in priced)
        unrealized_pnl = sum(p["quantity"] * (price - p["avg_cost"]) for p, price in priced)
        return {
            "cash_balance": cash,
            "total_value": round(cash + positions_value, 2),
            "positions_value": round(positions_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "positions": [_position_row(p, price, positions_value) for p, price in priced],
        }

    def list_watchlist(self) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            tickers = repo.list_watchlist(conn)
        return [{"ticker": t, "price": self._cache.get_price(t)} for t in tickers]

    def tracked_tickers(self) -> list[str]:
        with self._db.connection() as conn:
            return self._tracked(conn)

    def record_snapshot(self) -> dict[str, Any]:
        with self._db.connection() as conn:
            return repo.insert_snapshot(conn, self._total_value(conn))

    def get_history(self, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            snapshots = repo.list_snapshots(conn, limit)
        return [
            {"total_value": s["total_value"], "recorded_at": s["recorded_at"]} for s in snapshots
        ]

    # Changes

    async def execute_trade(self, ticker: str, side: str, quantity: float) -> dict[str, Any]:
        symbol = _normalize(ticker)
        _validate_side(side)
        shares = _validate_quantity(quantity)
        async with self._lock:
            try:
                await self._track(symbol)
                price = self._cache.get_price(symbol)
                if price is None:
                    raise ServiceError(f"No price available for {symbol}")
                return await asyncio.to_thread(self._apply_trade, symbol, side, shares, price)
            finally:
                await self._drop_untracked_feeds()

    async def add_watchlist(self, ticker: str) -> dict[str, Any]:
        symbol = _normalize(ticker)
        async with self._lock:
            try:
                await self._track(symbol)
                await asyncio.to_thread(self._insert_watchlist, symbol)
            except Exception:
                await self._drop_untracked_feeds()
                raise
        return {"ticker": symbol, "price": self._cache.get_price(symbol)}

    async def remove_watchlist(self, ticker: str) -> dict[str, Any]:
        try:
            symbol = normalize_ticker(ticker)
        except InvalidTickerError as exc:
            # A malformed symbol cannot be on the watchlist.
            raise NotFoundError(f"{ticker} is not on the watchlist") from exc
        async with self._lock:
            removed = await asyncio.to_thread(self._delete_watchlist, symbol)
            if not removed:
                raise NotFoundError(f"{symbol} is not on the watchlist")
            await self._drop_untracked_feeds()
        return {"ticker": symbol, "removed": True}

    # Market source

    async def _track(self, symbol: str) -> None:
        try:
            await self._source.add_ticker(symbol)
        except InvalidTickerError as exc:
            raise ServiceError(str(exc)) from exc
        except MarketDataUnavailableError as exc:
            raise UnavailableError(str(exc)) from exc

    async def _drop_untracked_feeds(self) -> None:
        """Make the source follow the database. Never raises: the user's change
        has already succeeded or failed by now, and the next change retries."""
        try:
            tracked = set(await asyncio.to_thread(self.tracked_tickers))
            for ticker in set(self._source.get_tickers()) - tracked:
                await self._source.remove_ticker(ticker)
        except Exception:
            logger.exception("Could not drop untracked market data feeds")

    # Database work. Each runs in a worker thread and holds the write lock
    # throughout, so none of these may await.

    def _apply_trade(self, ticker: str, side: str, quantity: float, price: float) -> dict[str, Any]:
        with self._db.connection() as conn:
            if side == "buy":
                self._apply_buy(conn, ticker, quantity, price)
            else:
                self._apply_sell(conn, ticker, quantity, price)
            trade = repo.insert_trade(conn, ticker, side, quantity, price)
            repo.insert_snapshot(conn, self._total_value(conn))
        return trade

    def _apply_buy(
        self, conn: sqlite3.Connection, ticker: str, quantity: float, price: float
    ) -> None:
        cost = round(quantity * price, 2)
        if cost <= 0:
            raise ServiceError("Trade value is below one cent")
        cash = repo.get_cash(conn)
        if cost > cash:
            raise ServiceError(f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}")
        position = repo.get_position(conn, ticker)
        held = position["quantity"] if position else 0.0
        held_cost = held * position["avg_cost"] if position else 0.0
        new_quantity = held + quantity
        repo.set_cash(conn, cash - cost)
        repo.upsert_position(conn, ticker, new_quantity, (held_cost + quantity * price) / new_quantity)
        repo.add_watchlist(conn, ticker)

    def _apply_sell(
        self, conn: sqlite3.Connection, ticker: str, quantity: float, price: float
    ) -> None:
        # Selling never adds to the watchlist: otherwise closing a position in
        # an unwatched ticker could not stop its feed.
        position = repo.get_position(conn, ticker)
        held = position["quantity"] if position else 0.0
        if quantity > held + CLOSED_POSITION_EPSILON:
            raise ServiceError(f"Insufficient shares of {ticker}: have {held:g}, need {quantity:g}")
        repo.set_cash(conn, repo.get_cash(conn) + round(quantity * price, 2))
        remaining = held - quantity
        if remaining < CLOSED_POSITION_EPSILON:
            repo.delete_position(conn, ticker)
        else:
            repo.upsert_position(conn, ticker, remaining, position["avg_cost"])

    def _insert_watchlist(self, ticker: str) -> None:
        with self._db.connection() as conn:
            repo.add_watchlist(conn, ticker)

    def _delete_watchlist(self, ticker: str) -> bool:
        with self._db.connection() as conn:
            return repo.remove_watchlist(conn, ticker)

    def _tracked(self, conn: sqlite3.Connection) -> list[str]:
        held = (p["ticker"] for p in repo.list_positions(conn))
        return sorted({*repo.list_watchlist(conn), *held})

    # Valuation

    def _mark_price(self, position: dict[str, Any]) -> float:
        price = self._cache.get_price(position["ticker"])
        return position["avg_cost"] if price is None else price

    def _total_value(self, conn: sqlite3.Connection) -> float:
        positions = repo.list_positions(conn)
        return repo.get_cash(conn) + sum(p["quantity"] * self._mark_price(p) for p in positions)
