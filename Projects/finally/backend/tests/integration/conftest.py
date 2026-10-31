"""The real thing: create_app, full lifespan, real simulator, real SQLite file, LLM_MOCK=true.

Nothing in the app is faked here. SSE is read by calling the ASGI app directly on
the event loop the lifespan runs on, because TestClient buffers a whole response
and would never return from an endless stream.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return path


@pytest.fixture
def run_app(db_path) -> Callable[..., Any]:
    """Start the app; each `with` is a full process lifetime as far as the app can tell."""

    @contextmanager
    def run(**kwargs: Any) -> Iterator[TestClient]:
        with TestClient(create_app(env_file=None, **kwargs)) as client:
            yield client

    return run


@pytest.fixture
def client(run_app) -> Iterator[TestClient]:
    with run_app() as test_client:
        yield test_client


async def _read_events(app: FastAPI, count: int, timeout: float) -> dict[str, Any]:
    enough = anyio.Event()
    result: dict[str, Any] = {"status": None, "headers": {}, "events": []}
    buffer = ""

    async def receive() -> dict[str, Any]:
        await enough.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal buffer
        if message["type"] == "http.response.start":
            result["status"] = message["status"]
            result["headers"] = {k.decode(): v.decode() for k, v in message["headers"]}
        elif message["type"] == "http.response.body":
            buffer += message.get("body", b"").decode()
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                if frame.startswith("data: "):
                    result["events"].append(json.loads(frame[len("data: ") :]))
                    if len(result["events"]) >= count:
                        enough.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/stream/prices",
        "raw_path": b"/api/stream/prices",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 1),
        "server": ("testserver", 80),
    }
    with anyio.fail_after(timeout):
        await app(scope, receive, send)
    return result


def read_stream(client: TestClient, count: int = 1, timeout: float = 10.0) -> dict[str, Any]:
    """Open GET /api/stream/prices, read `count` data events, disconnect."""
    return client.portal.call(_read_events, client.app, count, timeout)


def streamed_tickers(client: TestClient) -> set[str]:
    return set(read_stream(client)["events"][0])
