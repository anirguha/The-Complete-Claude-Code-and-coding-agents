import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

from fastapi import Request

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Path) -> sqlite3.Connection:
    # FastAPI may run a request's dependency and handler on different threadpool threads;
    # each connection still serves only one request at a time.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(path: Path) -> None:
    """Creates the database and any missing tables from schema.sql, keeping existing data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, committed if the handler succeeds."""
    with closing(connect(request.app.state.db_path)) as conn:
        with conn:
            yield conn
