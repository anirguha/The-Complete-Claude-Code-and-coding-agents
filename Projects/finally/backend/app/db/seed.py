"""Default data for a fresh database."""

import sqlite3

from .repository import DEFAULT_USER_ID, _utc_now, add_watchlist

DEFAULT_CASH = 10000.0
DEFAULT_WATCHLIST = ("AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX")


def seed_missing(conn: sqlite3.Connection, watchlist_table_is_new: bool) -> None:
    """Fill in whatever a fresh database lacks, leaving user data alone.

    An empty watchlist on an initialized database means the user removed every
    ticker, so it is seeded only if its table is new or the profile is missing
    too. Call this after the schema has been applied.
    """
    profile_exists = (
        conn.execute("SELECT 1 FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)).fetchone()
        is not None
    )
    if not profile_exists:
        conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH, _utc_now()),
        )

    watchlist_is_empty = conn.execute("SELECT 1 FROM watchlist LIMIT 1").fetchone() is None
    if watchlist_is_empty and (watchlist_table_is_new or not profile_exists):
        for ticker in DEFAULT_WATCHLIST:
            add_watchlist(conn, ticker)
