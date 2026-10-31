"""Repository functions: shapes, ordering, limits, rounding, user scoping."""

import inspect
import itertools
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest

import app.db as db_module
from app.db import (
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
from app.db.repository import _utc_now

REPOSITORY_FUNCTIONS = [
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
]


@pytest.fixture
def ticking_clock(monkeypatch):
    """Advance one second per call, with a clock independent of real time."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    counter = itertools.count()
    monkeypatch.setattr(
        "app.db.repository._utc_now",
        lambda: (start + timedelta(seconds=next(counter))).isoformat(timespec="microseconds"),
    )


@pytest.mark.parametrize("func", REPOSITORY_FUNCTIONS, ids=lambda f: f.__name__)
def test_signature_convention(func):
    params = list(inspect.signature(func).parameters.values())
    assert params[0].name == "conn"
    assert params[-1].name == "user_id"
    assert params[-1].default == "default"


def test_every_contract_function_is_exported():
    for func in REPOSITORY_FUNCTIONS:
        assert func.__name__ in db_module.__all__
    assert "Database" in db_module.__all__


class TestTimestamps:
    def test_utc_iso8601(self):
        parsed = datetime.fromisoformat(_utc_now())
        assert parsed.utcoffset() == timedelta(0)

    def test_fixed_width_even_on_a_whole_second(self, monkeypatch):
        class WholeSecond(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 0, 0, tzinfo=tz)

        monkeypatch.setattr("app.db.repository.datetime", WholeSecond)
        assert _utc_now() == "2026-01-01T00:00:00.000000+00:00"


class TestCash:
    def test_get_and_set(self, conn):
        assert get_cash(conn) == 10000.0
        set_cash(conn, 2500.5)
        assert get_cash(conn) == 2500.5

    def test_rounds_to_cents(self, conn):
        set_cash(conn, 100.126)
        assert get_cash(conn) == 100.13

    def test_returns_float(self, conn):
        set_cash(conn, 5)
        assert isinstance(get_cash(conn), float)

    def test_unknown_user_raises(self, conn):
        with pytest.raises(LookupError):
            get_cash(conn, user_id="ghost")
        with pytest.raises(LookupError):
            set_cash(conn, 1.0, user_id="ghost")


class TestWatchlist:
    def test_add_returns_true_then_false(self, conn):
        assert add_watchlist(conn, "PYPL") is True
        assert add_watchlist(conn, "PYPL") is False
        assert list_watchlist(conn).count("PYPL") == 1

    def test_remove_returns_true_then_false(self, conn):
        assert remove_watchlist(conn, "AAPL") is True
        assert remove_watchlist(conn, "AAPL") is False
        assert "AAPL" not in list_watchlist(conn)

    def test_oldest_first(self, conn, ticking_clock):
        conn.execute("DELETE FROM watchlist")  # Seed rows carry the real clock's time.
        for ticker in ("ZZZ", "AAA", "MMM"):
            add_watchlist(conn, ticker)
        assert list_watchlist(conn) == ["ZZZ", "AAA", "MMM"]

    def test_readd_moves_to_end(self, conn):
        remove_watchlist(conn, "AAPL")
        add_watchlist(conn, "AAPL")
        assert list_watchlist(conn)[-1] == "AAPL"

    def test_scoped_to_user(self, conn):
        assert list_watchlist(conn, user_id="other") == []
        assert add_watchlist(conn, "AAPL", user_id="other") is True
        assert list_watchlist(conn, user_id="other") == ["AAPL"]
        assert remove_watchlist(conn, "AAPL", user_id="other") is True
        assert "AAPL" in list_watchlist(conn)


class TestPositions:
    def test_get_missing_returns_none(self, conn):
        assert get_position(conn, "AAPL") is None

    def test_shape_is_plain_dict(self, conn):
        upsert_position(conn, "AAPL", 2.0, 190.5)
        position = get_position(conn, "AAPL")
        assert type(position) is dict
        assert set(position) == {"ticker", "quantity", "avg_cost", "updated_at"}
        assert position["ticker"] == "AAPL"
        assert position["quantity"] == 2.0
        assert position["avg_cost"] == 190.5

    def test_upsert_updates_in_place(self, conn, ticking_clock):
        upsert_position(conn, "AAPL", 1.0, 100.0)
        before = get_position(conn, "AAPL")
        upsert_position(conn, "AAPL", 3.0, 120.0)
        after = get_position(conn, "AAPL")
        assert (after["quantity"], after["avg_cost"]) == (3.0, 120.0)
        assert after["updated_at"] > before["updated_at"]
        assert len(list_positions(conn)) == 1

    def test_upsert_rounding(self, conn):
        upsert_position(conn, "AAPL", 0.3 - 0.1, 123.456789)
        position = get_position(conn, "AAPL")
        assert position["quantity"] == 0.2
        assert position["avg_cost"] == 123.4568

    def test_ordered_by_ticker(self, conn):
        for ticker in ("TSLA", "AAPL", "MSFT"):
            upsert_position(conn, ticker, 1.0, 1.0)
        assert [p["ticker"] for p in list_positions(conn)] == ["AAPL", "MSFT", "TSLA"]

    def test_delete(self, conn):
        upsert_position(conn, "AAPL", 1.0, 100.0)
        delete_position(conn, "AAPL")
        assert get_position(conn, "AAPL") is None
        delete_position(conn, "AAPL")  # Deleting nothing is not an error.

    def test_scoped_to_user(self, conn):
        upsert_position(conn, "AAPL", 1.0, 100.0)
        upsert_position(conn, "AAPL", 9.0, 900.0, user_id="other")
        assert get_position(conn, "AAPL")["quantity"] == 1.0
        assert get_position(conn, "AAPL", user_id="other")["quantity"] == 9.0
        delete_position(conn, "AAPL", user_id="other")
        assert get_position(conn, "AAPL") is not None
        assert list_positions(conn, user_id="other") == []


class TestTrades:
    def test_insert_returns_contract_shape(self, conn):
        trade = insert_trade(conn, "AAPL", "buy", 1.5, 190.0)
        assert set(trade) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
        uuid.UUID(trade["id"])
        assert list_trades(conn) == [trade]

    def test_insert_rounds_and_returns_stored_values(self, conn):
        trade = insert_trade(conn, "AAPL", "sell", 1.23456, 190.126)
        assert trade["quantity"] == 1.2346
        assert trade["price"] == 190.13
        assert list_trades(conn)[0] == trade

    def test_newest_first(self, conn, ticking_clock):
        ids = [insert_trade(conn, "AAPL", "buy", 1, 1.0)["id"] for _ in range(3)]
        assert [t["id"] for t in list_trades(conn)] == ids[::-1]

    def test_tie_break_is_insertion_order(self, conn, frozen_clock):
        ids = [insert_trade(conn, "AAPL", "buy", 1, 1.0)["id"] for _ in range(5)]
        assert [t["id"] for t in list_trades(conn)] == ids[::-1]

    def test_limit_keeps_newest(self, conn, ticking_clock):
        ids = [insert_trade(conn, "AAPL", "buy", 1, 1.0)["id"] for _ in range(5)]
        assert [t["id"] for t in list_trades(conn, limit=2)] == [ids[4], ids[3]]
        assert list_trades(conn, limit=0) == []

    def test_default_limit_is_100(self, conn):
        for _ in range(101):
            insert_trade(conn, "AAPL", "buy", 1, 1.0)
        assert len(list_trades(conn)) == 100

    def test_negative_limit_rejected(self, conn):
        with pytest.raises(ValueError):
            list_trades(conn, limit=-1)

    def test_scoped_to_user(self, conn):
        insert_trade(conn, "AAPL", "buy", 1, 1.0, user_id="other")
        assert list_trades(conn) == []
        assert len(list_trades(conn, user_id="other")) == 1


class TestSnapshots:
    def test_insert_returns_contract_shape(self, conn):
        snapshot = insert_snapshot(conn, 10000.126)
        assert set(snapshot) == {"id", "total_value", "recorded_at"}
        assert snapshot["total_value"] == 10000.13
        assert list_snapshots(conn) == [snapshot]

    def test_oldest_first(self, conn, ticking_clock):
        for value in (1.0, 2.0, 3.0):
            insert_snapshot(conn, value)
        assert [s["total_value"] for s in list_snapshots(conn)] == [1.0, 2.0, 3.0]

    def test_tie_break_is_insertion_order(self, conn, frozen_clock):
        for value in (1.0, 2.0, 3.0):
            insert_snapshot(conn, value)
        assert [s["total_value"] for s in list_snapshots(conn)] == [1.0, 2.0, 3.0]

    def test_limit_keeps_latest_returned_oldest_first(self, conn, ticking_clock):
        for value in (1.0, 2.0, 3.0, 4.0, 5.0):
            insert_snapshot(conn, value)
        assert [s["total_value"] for s in list_snapshots(conn, limit=2)] == [4.0, 5.0]
        assert list_snapshots(conn, limit=0) == []

    def test_default_limit_is_500(self, conn, ticking_clock):
        for i in range(501):
            insert_snapshot(conn, float(i))
        snapshots = list_snapshots(conn)
        assert len(snapshots) == 500
        assert snapshots[0]["total_value"] == 1.0
        assert snapshots[-1]["total_value"] == 500.0

    def test_negative_limit_rejected(self, conn):
        with pytest.raises(ValueError):
            list_snapshots(conn, limit=-1)

    def test_scoped_to_user(self, conn):
        insert_snapshot(conn, 1.0, user_id="other")
        assert list_snapshots(conn) == []
        assert len(list_snapshots(conn, user_id="other")) == 1


class TestChatMessages:
    ACTIONS = {
        "trades": [
            {
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
                "status": "executed",
                "price": 191.2,
                "error": None,
            }
        ],
        "watchlist_changes": [
            {"ticker": "PYPL", "action": "add", "status": "failed", "error": "café \"quoted\""}
        ],
    }

    def test_actions_round_trip(self, conn):
        returned = insert_chat_message(conn, "assistant", "Done.", self.ACTIONS)
        assert returned["actions"] == self.ACTIONS
        assert list_chat_messages(conn) == [returned]

    def test_actions_stored_as_json_text(self, conn):
        insert_chat_message(conn, "assistant", "Done.", self.ACTIONS)
        raw = conn.execute("SELECT actions FROM chat_messages").fetchone()["actions"]
        assert isinstance(raw, str)
        assert json.loads(raw) == self.ACTIONS

    def test_none_actions_stored_as_null(self, conn):
        insert_chat_message(conn, "user", "Hello")
        assert conn.execute("SELECT actions FROM chat_messages").fetchone()["actions"] is None
        assert list_chat_messages(conn)[0]["actions"] is None

    def test_empty_actions_stay_distinct_from_none(self, conn):
        insert_chat_message(conn, "assistant", "Nothing to do.", {})
        assert list_chat_messages(conn)[0]["actions"] == {}

    def test_shape(self, conn):
        message = insert_chat_message(conn, "user", "Hello")
        assert set(message) == {"id", "role", "content", "actions", "created_at"}
        uuid.UUID(message["id"])
        assert (message["role"], message["content"]) == ("user", "Hello")

    def test_role_is_constrained(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            insert_chat_message(conn, "system", "nope")

    def test_oldest_first(self, conn, ticking_clock):
        for text in ("one", "two", "three"):
            insert_chat_message(conn, "user", text)
        assert [m["content"] for m in list_chat_messages(conn)] == ["one", "two", "three"]

    def test_tie_break_is_insertion_order(self, conn, frozen_clock):
        for text in ("one", "two", "three"):
            insert_chat_message(conn, "user", text)
        assert [m["content"] for m in list_chat_messages(conn)] == ["one", "two", "three"]

    def test_limit_keeps_latest_returned_oldest_first(self, conn, ticking_clock):
        for text in ("one", "two", "three", "four"):
            insert_chat_message(conn, "user", text)
        assert [m["content"] for m in list_chat_messages(conn, limit=2)] == ["three", "four"]
        assert list_chat_messages(conn, limit=0) == []

    def test_default_limit_is_20(self, conn, ticking_clock):
        for i in range(21):
            insert_chat_message(conn, "user", str(i))
        messages = list_chat_messages(conn)
        assert len(messages) == 20
        assert messages[0]["content"] == "1"
        assert messages[-1]["content"] == "20"

    def test_negative_limit_rejected(self, conn):
        with pytest.raises(ValueError):
            list_chat_messages(conn, limit=-1)

    def test_scoped_to_user(self, conn):
        insert_chat_message(conn, "user", "Hello", user_id="other")
        assert list_chat_messages(conn) == []
        assert len(list_chat_messages(conn, user_id="other")) == 1
