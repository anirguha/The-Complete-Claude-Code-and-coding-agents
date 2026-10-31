"""Database class: path resolution, init, seeding, transactions, concurrency."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.db import (
    DEFAULT_CASH,
    DEFAULT_DB_PATH,
    DEFAULT_WATCHLIST,
    Database,
    add_watchlist,
    get_cash,
    insert_trade,
    list_positions,
    list_trades,
    list_watchlist,
    remove_watchlist,
    set_cash,
    upsert_position,
)

ALL_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


def table_names(db: Database) -> set[str]:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {row["name"] for row in rows}


def columns(db: Database, table: str) -> dict[str, sqlite3.Row]:
    with db.connection() as conn:
        return {row["name"]: row for row in conn.execute(f"PRAGMA table_info({table})")}


class TestPathResolution:
    def test_explicit_path_beats_env(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/from/env.db")
        assert Database("/explicit.db").path == "/explicit.db"

    def test_env_used_when_path_is_none(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/from/env.db")
        assert Database().path == "/from/env.db"

    def test_default_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("DB_PATH", raising=False)
        assert Database().path == DEFAULT_DB_PATH == "db/finally.db"

    def test_default_when_env_empty(self, monkeypatch):
        monkeypatch.setenv("DB_PATH", "")
        assert Database().path == DEFAULT_DB_PATH

    def test_accepts_pathlike(self, tmp_path):
        assert Database(tmp_path / "x.db").path == str(tmp_path / "x.db")

    def test_default_path_is_relative_to_working_directory(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DB_PATH", raising=False)
        monkeypatch.chdir(tmp_path)
        Database().init()
        assert (tmp_path / "db" / "finally.db").is_file()


class TestSchema:
    def test_creates_all_tables(self, db):
        assert table_names(db) == ALL_TABLES

    def test_creates_missing_parent_directories(self, tmp_path):
        path = tmp_path / "a" / "b" / "finally.db"
        Database(str(path)).init()
        assert path.is_file()

    @pytest.mark.parametrize("table", sorted(ALL_TABLES - {"users_profile"}))
    def test_user_id_defaults_to_default(self, db, table):
        assert columns(db, table)["user_id"]["dflt_value"] == "'default'"

    def test_users_profile_uses_id_as_user_key(self, db):
        cols = columns(db, "users_profile")
        assert "user_id" not in cols
        assert cols["id"]["pk"] == 1

    def test_expected_columns(self, db):
        assert set(columns(db, "users_profile")) == {"id", "cash_balance", "created_at"}
        assert set(columns(db, "watchlist")) == {"id", "user_id", "ticker", "added_at"}
        assert set(columns(db, "positions")) == {
            "id",
            "user_id",
            "ticker",
            "quantity",
            "avg_cost",
            "updated_at",
        }
        assert set(columns(db, "trades")) == {
            "id",
            "user_id",
            "ticker",
            "side",
            "quantity",
            "price",
            "executed_at",
        }
        assert set(columns(db, "portfolio_snapshots")) == {
            "id",
            "user_id",
            "total_value",
            "recorded_at",
        }
        assert set(columns(db, "chat_messages")) == {
            "id",
            "user_id",
            "role",
            "content",
            "actions",
            "created_at",
        }

    def test_watchlist_unique_per_user(self, conn):
        insert = "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, 'ZZZ', 't')"
        conn.execute(insert, ("1", "default"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("2", "default"))
        conn.execute(insert, ("3", "someone-else"))

    def test_positions_unique_per_user(self, conn):
        insert = (
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, 'ZZZ', 1, 1, 't')"
        )
        conn.execute(insert, ("1", "default"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("2", "default"))
        conn.execute(insert, ("3", "someone-else"))

    def test_trade_side_is_constrained(self, conn):
        with pytest.raises(sqlite3.IntegrityError):
            insert_trade(conn, "AAPL", "hold", 1, 100.0)


class TestSeed:
    def test_default_profile(self, conn):
        row = conn.execute("SELECT * FROM users_profile").fetchall()
        assert [r["id"] for r in row] == ["default"]
        assert row[0]["cash_balance"] == 10000.0 == DEFAULT_CASH
        assert row[0]["created_at"]

    def test_default_watchlist_in_order(self, conn):
        assert list_watchlist(conn) == [
            "AAPL",
            "GOOGL",
            "MSFT",
            "AMZN",
            "TSLA",
            "NVDA",
            "META",
            "JPM",
            "V",
            "NFLX",
        ]

    def test_seed_order_survives_identical_timestamps(self, tmp_path, frozen_clock):
        database = Database(str(tmp_path / "frozen.db"))
        database.init()
        with database.connection() as conn:
            assert list_watchlist(conn) == list(DEFAULT_WATCHLIST)

    def test_nothing_else_is_seeded(self, conn):
        for table in ("positions", "trades", "portfolio_snapshots", "chat_messages"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


class TestReinit:
    def test_preserves_user_data(self, db):
        with db.connection() as conn:
            set_cash(conn, 1234.56)
            add_watchlist(conn, "PYPL")
            remove_watchlist(conn, "AAPL")
            upsert_position(conn, "MSFT", 2.5, 400.0)
            insert_trade(conn, "MSFT", "buy", 2.5, 400.0)

        # A new instance mimics a restart against the same file.
        for database in (db, Database(db.path)):
            database.init()

        with db.connection() as conn:
            assert get_cash(conn) == 1234.56
            watchlist = list_watchlist(conn)
            assert "PYPL" in watchlist and "AAPL" not in watchlist
            assert len(watchlist) == 10
            assert [p["ticker"] for p in list_positions(conn)] == ["MSFT"]
            assert len(list_trades(conn)) == 1

    def test_deliberately_emptied_watchlist_stays_empty(self, db):
        with db.connection() as conn:
            for ticker in list_watchlist(conn):
                remove_watchlist(conn, ticker)
        db.init()
        with db.connection() as conn:
            assert list_watchlist(conn) == []

    def test_existing_empty_file_gets_tables_and_seed(self, tmp_path):
        path = tmp_path / "empty.db"
        path.touch()
        database = Database(str(path))
        database.init()
        assert table_names(database) == ALL_TABLES
        with database.connection() as conn:
            assert get_cash(conn) == DEFAULT_CASH
            assert list_watchlist(conn) == list(DEFAULT_WATCHLIST)

    def test_one_missing_table_is_recreated_without_touching_others(self, db):
        with db.connection() as conn:
            set_cash(conn, 500.0)
            upsert_position(conn, "AAPL", 1, 100.0)
            conn.execute("DROP TABLE trades")
        db.init()
        assert "trades" in table_names(db)
        with db.connection() as conn:
            assert get_cash(conn) == 500.0
            assert len(list_positions(conn)) == 1
            assert list_trades(conn) == []

    def test_missing_watchlist_table_is_reseeded(self, db):
        with db.connection() as conn:
            set_cash(conn, 500.0)
            conn.execute("DROP TABLE watchlist")
        db.init()
        with db.connection() as conn:
            assert list_watchlist(conn) == list(DEFAULT_WATCHLIST)
            assert get_cash(conn) == 500.0

    def test_missing_profile_table_is_reseeded_without_touching_watchlist(self, db):
        with db.connection() as conn:
            remove_watchlist(conn, "AAPL")
            conn.execute("DROP TABLE users_profile")
        db.init()
        with db.connection() as conn:
            assert get_cash(conn) == DEFAULT_CASH
            assert len(list_watchlist(conn)) == 9

    def test_failed_init_leaves_no_partial_schema(self, tmp_path, monkeypatch):
        database = Database(str(tmp_path / "partial.db"))

        def fail(*args, **kwargs):
            raise RuntimeError("seed failed")

        monkeypatch.setattr("app.db.database.seed_missing", fail)
        with pytest.raises(RuntimeError):
            database.init()
        assert table_names(database) == set()

        monkeypatch.undo()
        database.init()
        assert table_names(database) == ALL_TABLES


class TestConnection:
    def test_row_factory_wal_and_busy_timeout(self, db):
        with db.connection() as conn:
            assert isinstance(conn.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)
            assert conn.execute("SELECT 1 AS one").fetchone()["one"] == 1
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] > 0
        probe = sqlite3.connect(db.path)
        try:
            assert probe.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        finally:
            probe.close()

    def test_new_connection_per_use_closed_on_exit(self, db):
        with db.connection() as first:
            pass
        with db.connection() as second:
            assert second is not first
        with pytest.raises(sqlite3.ProgrammingError):
            first.execute("SELECT 1")

    def test_commits_on_clean_exit(self, db):
        with db.connection() as conn:
            set_cash(conn, 42.0)
        with db.connection() as conn:
            assert get_cash(conn) == 42.0

    def test_rolls_back_everything_on_exception(self, db):
        with pytest.raises(RuntimeError):
            with db.connection() as conn:
                set_cash(conn, 1.0)
                upsert_position(conn, "AAPL", 1, 100.0)
                insert_trade(conn, "AAPL", "buy", 1, 100.0)
                raise RuntimeError("boom")
        with db.connection() as conn:
            assert get_cash(conn) == DEFAULT_CASH
            assert list_positions(conn) == []
            assert list_trades(conn) == []

    def test_connection_is_closed_after_exception(self, db):
        with pytest.raises(RuntimeError):
            with db.connection() as conn:
                raise RuntimeError("boom")
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_uncommitted_writes_are_invisible_to_others(self, db):
        with db.connection() as writer:
            set_cash(writer, 1.0)
            probe = sqlite3.connect(db.path)
            try:
                seen = probe.execute("SELECT cash_balance FROM users_profile").fetchone()[0]
            finally:
                probe.close()
        assert seen == DEFAULT_CASH


class TestConcurrency:
    def test_concurrent_init_on_fresh_file(self, tmp_path):
        database = Database(str(tmp_path / "race.db"))
        workers = 8
        barrier = Barrier(workers)

        def init(_):
            barrier.wait()
            database.init()

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(init, range(workers)))

        with database.connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
            assert list_watchlist(conn) == list(DEFAULT_WATCHLIST)

    def test_concurrent_init_from_separate_instances(self, tmp_path):
        path = str(tmp_path / "race.db")
        workers = 8
        barrier = Barrier(workers)

        def init(_):
            barrier.wait()
            Database(path).init()

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(init, range(workers)))

        with Database(path).connection() as conn:
            assert list_watchlist(conn) == list(DEFAULT_WATCHLIST)

    def test_read_modify_write_loses_no_updates(self, db):
        """Parallel trades must each see the balance the previous one left."""
        workers, rounds = 8, 25

        def debit(_):
            for _ in range(rounds):
                with db.connection() as conn:
                    set_cash(conn, get_cash(conn) - 1.0)

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(debit, range(workers)))

        with db.connection() as conn:
            assert get_cash(conn) == DEFAULT_CASH - workers * rounds

    def test_concurrent_inserts_all_land(self, db):
        workers, rounds = 8, 25

        def trade(worker):
            for i in range(rounds):
                with db.connection() as conn:
                    insert_trade(conn, f"T{worker}", "buy", i + 1, 10.0)

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(trade, range(workers)))

        with db.connection() as conn:
            assert len(list_trades(conn, limit=1000)) == workers * rounds

    def test_concurrent_add_of_same_ticker_inserts_once(self, db):
        workers = 8
        barrier = Barrier(workers)

        def add(_):
            barrier.wait()
            with db.connection() as conn:
                return add_watchlist(conn, "PYPL")

        with ThreadPoolExecutor(workers) as pool:
            results = list(pool.map(add, range(workers)))

        assert results.count(True) == 1
        with db.connection() as conn:
            assert list_watchlist(conn).count("PYPL") == 1
