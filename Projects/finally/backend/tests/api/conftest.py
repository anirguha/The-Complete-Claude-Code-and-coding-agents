import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.portfolio.fakes import FakeSource


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    """Builds apps on a temp database and a fake source, ignoring any .env file."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "finally.db"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setattr("app.main.create_market_data_source", FakeSource)

    def make(**kwargs):
        return create_app(env_file=None, **kwargs)

    return make


@pytest.fixture
def client(make_app):
    with TestClient(make_app()) as test_client:
        yield test_client


@pytest.fixture
def source(client) -> FakeSource:
    return client.app.state.source
