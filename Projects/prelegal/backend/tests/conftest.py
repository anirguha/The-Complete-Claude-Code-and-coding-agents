from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    """A stand-in for the exported frontend (built with trailingSlash, so pages are dir/index.html)."""
    out = tmp_path / "out"
    (out / "login").mkdir(parents=True)
    (out / "index.html").write_text("<h1>home</h1>")
    (out / "login" / "index.html").write_text("<h1>login</h1>")
    (out / "404.html").write_text("<h1>not found</h1>")
    return out


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "prelegal.db"


@pytest.fixture
def client(db_path: Path, static_dir: Path):
    with TestClient(create_app(db_path, static_dir)) as client:
        yield client


ALICE = {"email": "alice@example.com", "name": "Alice", "password": "correct horse battery"}


def sign_up_and_in(client: TestClient, user: dict = ALICE) -> TestClient:
    client.post("/api/auth/signup", json=user)
    client.post("/api/auth/signin", json={"email": user["email"], "password": user["password"]})
    return client


@pytest.fixture
def signed_in(client: TestClient) -> TestClient:
    return sign_up_and_in(client)
