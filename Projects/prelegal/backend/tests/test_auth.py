import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.routers.auth import SESSION_COOKIE, hash_password, token_hash, verify_password
from tests.conftest import ALICE, sign_up_and_in

CREDENTIALS = {"email": ALICE["email"], "password": ALICE["password"]}


def test_passwords_are_salted_and_verified():
    first, second = hash_password("secret pass"), hash_password("secret pass")

    assert first != second
    assert first.startswith("scrypt$") and "secret pass" not in first
    assert verify_password("secret pass", first)
    assert not verify_password("wrong pass", first)
    assert not verify_password("secret pass", "not-a-hash")


def test_sign_up_creates_an_account_without_signing_in(client: TestClient):
    response = client.post("/api/auth/signup", json={**ALICE, "email": "Alice@Example.com", "name": "  Alice  "})

    assert response.status_code == 201
    assert response.json() == {"id": response.json()["id"], "email": "alice@example.com", "name": "Alice"}
    assert SESSION_COOKIE not in response.cookies
    assert client.get("/api/auth/me").status_code == 401


def test_sign_up_rejects_a_taken_email(client: TestClient):
    client.post("/api/auth/signup", json=ALICE)

    response = client.post("/api/auth/signup", json={**ALICE, "email": "ALICE@example.com", "name": "Other"})

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


@pytest.mark.parametrize(
    "body",
    [
        {**ALICE, "email": "not-an-email"},
        {**ALICE, "name": "   "},
        {**ALICE, "password": "short"},
        {"email": ALICE["email"], "name": "Alice"},
    ],
)
def test_sign_up_validates_input(client: TestClient, body: dict):
    assert client.post("/api/auth/signup", json=body).status_code == 422


def test_sign_in_starts_a_session(client: TestClient):
    client.post("/api/auth/signup", json=ALICE)

    response = client.post("/api/auth/signin", json={**CREDENTIALS, "email": "ALICE@example.com"})

    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "max-age=2592000" in cookie
    assert client.get("/api/auth/me").json() == response.json() == {
        "id": response.json()["id"],
        "email": "alice@example.com",
        "name": "Alice",
    }


@pytest.mark.parametrize(
    "credentials",
    [{**CREDENTIALS, "password": "wrong password"}, {**CREDENTIALS, "email": "nobody@example.com"}],
)
def test_sign_in_rejects_wrong_credentials_the_same_way(client: TestClient, credentials: dict):
    client.post("/api/auth/signup", json=ALICE)

    response = client.post("/api/auth/signin", json=credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert client.get("/api/auth/me").status_code == 401


def test_sessions_store_only_a_hash_of_the_token(signed_in: TestClient, db_path: Path):
    token = signed_in.cookies[SESSION_COOKIE]
    with sqlite3.connect(db_path) as conn:
        stored = [row[0] for row in conn.execute("SELECT token_hash FROM sessions")]
    assert stored == [token_hash(token)]


def test_sign_out_ends_the_session_everywhere(signed_in: TestClient, db_path: Path):
    token = signed_in.cookies[SESSION_COOKIE]

    assert signed_in.post("/api/auth/signout").status_code == 204

    signed_in.cookies.set(SESSION_COOKIE, token)
    assert signed_in.get("/api/auth/me").status_code == 401


def test_expired_unknown_or_missing_sessions_are_rejected(signed_in: TestClient, db_path: Path):
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
    assert signed_in.get("/api/auth/me").status_code == 401

    for value in ["made-up-token", ""]:
        signed_in.cookies.set(SESSION_COOKIE, value)
        assert signed_in.get("/api/auth/me").status_code == 401


def test_each_user_has_their_own_session(client: TestClient, static_dir: Path):
    bob = {"email": "bob@example.com", "name": "Bob", "password": "another password"}
    sign_up_and_in(client)
    with TestClient(client.app) as other:
        sign_up_and_in(other, bob)
        assert other.get("/api/auth/me").json()["name"] == "Bob"
    assert client.get("/api/auth/me").json()["name"] == "Alice"


def test_concurrent_sign_ups_all_succeed(client: TestClient):
    def sign_up(i: int) -> int:
        user = {"email": f"user{i}@example.com", "name": f"U{i}", "password": "password123"}
        return client.post("/api/auth/signup", json=user).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(sign_up, range(24))) == {201}
