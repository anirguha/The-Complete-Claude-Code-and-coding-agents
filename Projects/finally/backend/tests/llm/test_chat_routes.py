"""POST /api/chat and GET /api/chat/history through the real app, in process."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm.routes import MAX_MESSAGE_CHARS
from app.main import create_app
from tests.portfolio.fakes import FakeSource

BACKEND = Path(__file__).parents[2]


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setattr("app.main.create_market_data_source", FakeSource)

    def make() -> TestClient:
        return TestClient(create_app(env_file=None))

    return make


@pytest.fixture
def client(make_client):
    with make_client() as test_client:
        yield test_client


def test_a_mock_buy_changes_the_portfolio_end_to_end(client):
    response = client.post("/api/chat", json={"message": "buy 10 AAPL"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "Mock: buying 10 shares of AAPL.",
        "trades": [
            {
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
                "status": "executed",
                "price": 100.0,
                "error": None,
            }
        ],
        "watchlist_changes": [],
    }
    portfolio = client.get("/api/portfolio").json()
    assert portfolio["cash_balance"] == 9000.0
    assert [p["ticker"] for p in portfolio["positions"]] == ["AAPL"]


def test_a_mock_sell_and_watchlist_changes_end_to_end(client):
    client.post("/api/chat", json={"message": "buy 10 AAPL"})

    assert client.post("/api/chat", json={"message": "sell 10 AAPL"}).status_code == 200
    assert client.get("/api/portfolio").json()["positions"] == []

    client.post("/api/chat", json={"message": "add PYPL"})
    assert "PYPL" in [w["ticker"] for w in client.get("/api/watchlist").json()["watchlist"]]

    client.post("/api/chat", json={"message": "remove PYPL"})
    assert "PYPL" not in [w["ticker"] for w in client.get("/api/watchlist").json()["watchlist"]]


def test_a_failed_action_is_still_a_200(client):
    response = client.post("/api/chat", json={"message": "sell 5 AAPL"})

    assert response.status_code == 200
    assert response.json()["trades"][0]["status"] == "failed"


@pytest.mark.parametrize(
    "body",
    [
        {"message": ""},
        {"message": "   "},
        {"message": "\n\t "},
        {"message": None},
        {"message": 5},
        {"message": ["hi"]},
        {},
        {"message": "x" * (MAX_MESSAGE_CHARS + 1)},
    ],
)
def test_bad_message_bodies_are_422_and_store_nothing(client, body):
    assert client.post("/api/chat", json=body).status_code == 422
    assert client.get("/api/chat/history").json() == {"messages": []}


def test_a_message_at_the_limit_is_accepted(client):
    assert client.post("/api/chat", json={"message": "x" * MAX_MESSAGE_CHARS}).status_code == 200


def test_a_lone_surrogate_in_the_message_does_not_break_the_request(client):
    response = client.post(
        "/api/chat",
        content=b'{"message": "hi \\ud800"}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200
    assert client.get("/api/chat/history").json()["messages"][0]["content"] == "hi ?"


def test_a_lone_surrogate_in_a_non_string_message_is_a_422(client):
    response = client.post(
        "/api/chat",
        content=b'{"message": ["\\ud800"]}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_history_has_the_contract_shape(client):
    client.post("/api/chat", json={"message": "buy 1 AAPL"})

    response = client.get("/api/chat/history")

    assert response.status_code == 200
    user, assistant = response.json()["messages"]
    assert set(user) == set(assistant) == {"role", "content", "actions", "created_at"}
    assert (user["role"], user["content"], user["actions"]) == ("user", "buy 1 AAPL", None)
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "Mock: buying 1 shares of AAPL."
    assert assistant["actions"]["trades"][0]["status"] == "executed"
    assert assistant["actions"]["watchlist_changes"] == []


def test_history_returns_the_latest_50_oldest_first(client):
    for number in range(30):
        client.post("/api/chat", json={"message": f"m{number}"})

    messages = client.get("/api/chat/history").json()["messages"]

    assert len(messages) == 50
    assert messages[0]["content"] == "m5"
    assert messages[-2]["content"] == "m29"
    assert messages[-1]["role"] == "assistant"


def test_history_survives_a_restart(make_client):
    with make_client() as first:
        first.post("/api/chat", json={"message": "hello"})
    with make_client() as second:
        assert len(second.get("/api/chat/history").json()["messages"]) == 2


def test_chat_routes_work_with_the_frontend_mounted(make_client, tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>frontend</html>")
    monkeypatch.setenv("STATIC_DIR", str(static))

    with make_client() as client:
        assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
        assert client.get("/api/chat/history").status_code == 200
        assert "frontend" in client.get("/").text


def test_no_key_and_no_mock_is_a_200_saying_not_configured(make_client, monkeypatch):
    monkeypatch.delenv("LLM_MOCK")

    with make_client() as client:
        response = client.post("/api/chat", json={"message": "hi"})

    assert response.status_code == 200
    assert response.json()["message"].startswith("LLM not configured")


def test_a_mock_buy_with_the_real_simulator(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    with TestClient(create_app(env_file=None)) as client:
        trade = client.post("/api/chat", json={"message": "buy 1 PYPL"}).json()["trades"][0]
        positions = client.get("/api/portfolio").json()["positions"]

    assert trade["status"] == "executed"
    assert trade["price"] > 0
    assert [p["ticker"] for p in positions] == ["PYPL"]


@pytest.mark.parametrize(("preset", "expected"), [(None, "True"), ("False", "False")])
def test_importing_the_app_is_lazy_and_sets_the_cost_map_flag(preset, expected):
    """Run fresh: litellm must not load with the app, and an existing setting must win."""
    env = {k: v for k, v in os.environ.items() if k != "LITELLM_LOCAL_MODEL_COST_MAP"}
    if preset is not None:
        env["LITELLM_LOCAL_MODEL_COST_MAP"] = preset
    code = (
        "import os, sys\n"
        "import app.main\n"
        "assert 'litellm' not in sys.modules, 'litellm was imported'\n"
        "print(os.environ['LITELLM_LOCAL_MODEL_COST_MAP'])\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
