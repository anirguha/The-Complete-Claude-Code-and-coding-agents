"""SQLite connection management and schema initialization."""

import os
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

from .seed import seed_missing

DEFAULT_DB_PATH = "db/finally.db"
BUSY_TIMEOUT_SECONDS = 5.0


def _schema_statements() -> list[str]:
    """Split schema.sql, because executescript() would commit our transaction."""
    script = resources.files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
    statements: list[str] = []
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending)
            pending = ""
    return statements


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Switch to WAL, retrying by hand: the switch can ignore the busy timeout.

    That happens when several connections open a new file at once.
    """
    deadline = time.monotonic() + BUSY_TIMEOUT_SECONDS
    while True:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as error:
            # The low byte is the primary result code; extended BUSY codes share it.
            is_busy = error.sqlite_errorcode & 0xFF == sqlite3.SQLITE_BUSY
            if not is_busy or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


class Database:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        if path is None:
            path = os.environ.get("DB_PATH") or DEFAULT_DB_PATH
        self.path = os.fspath(path)

    def _connect(self) -> sqlite3.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None stops sqlite3 from opening transactions on its
        # own; connection() manages them explicitly.
        conn = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            _enable_wal(conn)
        except BaseException:
            conn.close()
            raise
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a new connection inside one transaction.

        Commits on clean exit and rolls back on exception. The transaction takes
        the write lock up front, so a read-check-write sequence such as a trade
        cannot act on a stale cash balance. Keep the block short and never await
        inside it: other connections wait on this lock.
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        """Create missing tables and seed data. Safe to call on every start."""
        with self.connection() as conn:
            watchlist_table_is_new = (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'watchlist'"
                ).fetchone()
                is None
            )
            for statement in _schema_statements():
                conn.execute(statement)
            seed_missing(conn, watchlist_table_is_new)
