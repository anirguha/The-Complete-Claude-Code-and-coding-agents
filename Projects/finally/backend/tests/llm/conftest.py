import json
from types import SimpleNamespace

import httpx
import pytest

import app.llm  # noqa: F401  (sets LITELLM_LOCAL_MODEL_COST_MAP before anything imports litellm)
from app.db import Database
from app.llm import ChatService
from app.market import PriceCache
from app.portfolio import PortfolioService
from tests.portfolio.fakes import FakeSource

TEST_KEY = "sk-or-test-secret-key"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any HTTP request a test did not explicitly fake is a failure."""

    async def refuse_async(self, request, **kwargs):
        raise AssertionError(f"Unexpected network call to {request.url}")

    real_send = httpx.Client.send

    def refuse(self, request, **kwargs):
        if request.url.host == "testserver":  # TestClient: in-process ASGI, not a network call
            return real_send(self, request, **kwargs)
        raise AssertionError(f"Unexpected network call to {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", refuse_async)
    monkeypatch.setattr(httpx.Client, "send", refuse)


@pytest.fixture
def db(tmp_path) -> Database:
    database = Database(str(tmp_path / "finally.db"))
    database.init()
    return database


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def source(cache) -> FakeSource:
    return FakeSource(cache)


@pytest.fixture
async def portfolio(db, cache, source) -> PortfolioService:
    service = PortfolioService(db, cache, source)
    await source.start(service.tracked_tickers())
    return service


@pytest.fixture
def mock_chat(db, portfolio) -> ChatService:
    return ChatService(db, portfolio, environ={"LLM_MOCK": "true"})


@pytest.fixture
def live_chat(db, portfolio) -> ChatService:
    return ChatService(db, portfolio, environ={"OPENROUTER_API_KEY": TEST_KEY})


class FakeLLM:
    """Stands in for litellm.acompletion and records its arguments."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.content: object = json.dumps({"message": "ok", "trades": [], "watchlist_changes": []})
        self.error: Exception | None = None
        self.during_call = None  # optional coroutine function

    def reply(self, message="ok", trades=(), watchlist_changes=()) -> None:
        self.content = json.dumps(
            {"message": message, "trades": list(trades), "watchlist_changes": list(watchlist_changes)}
        )

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.during_call is not None:
            await self.during_call()
        if self.error is not None:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    fake = FakeLLM()
    monkeypatch.setattr("litellm.acompletion", fake)
    return fake
