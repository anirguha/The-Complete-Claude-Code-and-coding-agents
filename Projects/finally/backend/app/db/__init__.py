"""SQLite persistence: the Database class and repository functions."""

from .database import DEFAULT_DB_PATH, Database
from .repository import (
    DEFAULT_USER_ID,
    add_watchlist,
    delete_position,
    get_cash,
    get_position,
    insert_chat_message,
    insert_snapshot,
    insert_trade,
    list_chat_messages,
    list_positions,
    list_snapshots,
    list_trades,
    list_watchlist,
    remove_watchlist,
    set_cash,
    upsert_position,
)
from .seed import DEFAULT_CASH, DEFAULT_WATCHLIST

__all__ = [
    "DEFAULT_CASH",
    "DEFAULT_DB_PATH",
    "DEFAULT_USER_ID",
    "DEFAULT_WATCHLIST",
    "Database",
    "add_watchlist",
    "delete_position",
    "get_cash",
    "get_position",
    "insert_chat_message",
    "insert_snapshot",
    "insert_trade",
    "list_chat_messages",
    "list_positions",
    "list_snapshots",
    "list_trades",
    "list_watchlist",
    "remove_watchlist",
    "set_cash",
    "upsert_position",
]
