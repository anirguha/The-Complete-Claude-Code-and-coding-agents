import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import ALICE, sign_up_and_in


def test_health(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_accounts_and_sessions_survive_a_restart(db_path: Path, static_dir: Path):
    with TestClient(create_app(db_path, static_dir)) as client:
        sign_up_and_in(client)
        cookies = dict(client.cookies)

    with TestClient(create_app(db_path, static_dir), cookies=cookies) as client:
        assert client.get("/api/auth/me").json()["email"] == ALICE["email"]
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"users", "sessions", "documents"} <= tables


def test_serves_exported_frontend(client: TestClient):
    assert client.get("/").text == "<h1>home</h1>"
    assert client.get("/login/").text == "<h1>login</h1>"
    assert client.get("/login").text == "<h1>login</h1>"

    missing = client.get("/no-such-page")
    assert missing.status_code == 404
    assert missing.text == "<h1>not found</h1>"


def test_runs_without_exported_frontend(db_path: Path, tmp_path: Path):
    with TestClient(create_app(db_path, tmp_path / "missing")) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 404
