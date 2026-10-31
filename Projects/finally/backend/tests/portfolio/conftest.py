import pytest

from app.db import Database
from app.market import PriceCache
from app.portfolio import PortfolioService
from tests.portfolio.fakes import FakeSource


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
async def service(db, cache, source) -> PortfolioService:
    portfolio = PortfolioService(db, cache, source)
    await source.start(portfolio.tracked_tickers())
    return portfolio
