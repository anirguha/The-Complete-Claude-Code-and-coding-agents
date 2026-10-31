import pytest

from app.db import Database


@pytest.fixture
def db(tmp_path) -> Database:
    database = Database(str(tmp_path / "finally.db"))
    database.init()
    return database


@pytest.fixture
def conn(db):
    """A connection whose writes commit when the test ends."""
    with db.connection() as connection:
        yield connection


@pytest.fixture
def frozen_clock(monkeypatch):
    """Give every row the same timestamp, to exercise the ordering tie-break."""
    monkeypatch.setattr("app.db.repository._utc_now", lambda: "2026-01-01T00:00:00.000000+00:00")
