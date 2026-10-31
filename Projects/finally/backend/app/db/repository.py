"""Repository functions. Each takes an open connection and never commits.

The rounding rules from the team contract are enforced here, so every write
path gets them: cash, prices and portfolio values to 2 decimals, quantities and
``avg_cost`` to 4. Tickers are stored as given; callers normalize them first.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

DEFAULT_USER_ID = "default"

MONEY_DECIMALS = 2
QUANTITY_DECIMALS = 4
AVG_COST_DECIMALS = 4


def _utc_now() -> str:
    # Fixed-width microseconds keep these strings sorting chronologically.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _new_id() -> str:
    return str(uuid.uuid4())


def _check_limit(limit: int) -> None:
    # SQLite treats a negative LIMIT as "no limit".
    if limit < 0:
        raise ValueError(f"limit must not be negative: {limit}")


def get_cash(conn: sqlite3.Connection, *, user_id: str = DEFAULT_USER_ID) -> float:
    row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise LookupError(f"Unknown user: {user_id}")
    return row["cash_balance"]


def set_cash(conn: sqlite3.Connection, amount: float, *, user_id: str = DEFAULT_USER_ID) -> None:
    cursor = conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (round(amount, MONEY_DECIMALS), user_id),
    )
    if cursor.rowcount == 0:
        raise LookupError(f"Unknown user: {user_id}")


def list_watchlist(conn: sqlite3.Connection, *, user_id: str = DEFAULT_USER_ID) -> list[str]:
    rows = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
        (user_id,),
    ).fetchall()
    return [row["ticker"] for row in rows]


def add_watchlist(conn: sqlite3.Connection, ticker: str, *, user_id: str = DEFAULT_USER_ID) -> bool:
    cursor = conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (user_id, ticker) DO NOTHING",
        (_new_id(), user_id, ticker, _utc_now()),
    )
    return cursor.rowcount == 1


def remove_watchlist(
    conn: sqlite3.Connection, ticker: str, *, user_id: str = DEFAULT_USER_ID
) -> bool:
    cursor = conn.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    return cursor.rowcount == 1


def get_position(
    conn: sqlite3.Connection, ticker: str, *, user_id: str = DEFAULT_USER_ID
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
        "WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    return dict(row) if row is not None else None


def list_positions(conn: sqlite3.Connection, *, user_id: str = DEFAULT_USER_ID) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
        "WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_position(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    *,
    user_id: str = DEFAULT_USER_ID,
) -> None:
    conn.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (user_id, ticker) DO UPDATE SET "
        "quantity = excluded.quantity, avg_cost = excluded.avg_cost, "
        "updated_at = excluded.updated_at",
        (
            _new_id(),
            user_id,
            ticker,
            round(quantity, QUANTITY_DECIMALS),
            round(avg_cost, AVG_COST_DECIMALS),
            _utc_now(),
        ),
    )


def delete_position(
    conn: sqlite3.Connection, ticker: str, *, user_id: str = DEFAULT_USER_ID
) -> None:
    conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))


def insert_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    *,
    user_id: str = DEFAULT_USER_ID,
) -> dict[str, Any]:
    trade = {
        "id": _new_id(),
        "ticker": ticker,
        "side": side,
        "quantity": round(quantity, QUANTITY_DECIMALS),
        "price": round(price, MONEY_DECIMALS),
        "executed_at": _utc_now(),
    }
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (:id, :user_id, :ticker, :side, :quantity, :price, :executed_at)",
        {**trade, "user_id": user_id},
    )
    return trade


def list_trades(
    conn: sqlite3.Connection, limit: int = 100, *, user_id: str = DEFAULT_USER_ID
) -> list[dict[str, Any]]:
    _check_limit(limit)
    rows = conn.execute(
        "SELECT id, ticker, side, quantity, price, executed_at FROM trades "
        "WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def insert_snapshot(
    conn: sqlite3.Connection, total_value: float, *, user_id: str = DEFAULT_USER_ID
) -> dict[str, Any]:
    snapshot = {
        "id": _new_id(),
        "total_value": round(total_value, MONEY_DECIMALS),
        "recorded_at": _utc_now(),
    }
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (:id, :user_id, :total_value, :recorded_at)",
        {**snapshot, "user_id": user_id},
    )
    return snapshot


def list_snapshots(
    conn: sqlite3.Connection, limit: int = 500, *, user_id: str = DEFAULT_USER_ID
) -> list[dict[str, Any]]:
    _check_limit(limit)
    rows = conn.execute(
        "SELECT id, total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def insert_chat_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    actions: dict[str, Any] | None = None,
    *,
    user_id: str = DEFAULT_USER_ID,
) -> dict[str, Any]:
    message = {
        "id": _new_id(),
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": _utc_now(),
    }
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (:id, :user_id, :role, :content, :actions, :created_at)",
        {
            **message,
            "user_id": user_id,
            "actions": json.dumps(actions) if actions is not None else None,
        },
    )
    return message


def list_chat_messages(
    conn: sqlite3.Connection, limit: int = 20, *, user_id: str = DEFAULT_USER_ID
) -> list[dict[str, Any]]:
    _check_limit(limit)
    rows = conn.execute(
        "SELECT id, role, content, actions, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {**dict(row), "actions": json.loads(row["actions"]) if row["actions"] is not None else None}
        for row in reversed(rows)
    ]
