import pytest

from app.market import PriceCache, create_market_data_source
from app.market.massive_client import DEFAULT_POLL_SECONDS, MassiveDataSource
from app.market.simulator import SimulatorDataSource


@pytest.mark.parametrize("env", [{}, {"MASSIVE_API_KEY": ""}, {"MASSIVE_API_KEY": "   "}])
def test_simulator_when_key_absent_or_blank(env):
    assert isinstance(create_market_data_source(PriceCache(), env), SimulatorDataSource)


def test_massive_when_key_set():
    src = create_market_data_source(PriceCache(), {"MASSIVE_API_KEY": "abc"})
    assert isinstance(src, MassiveDataSource)
    assert src._poll_seconds == DEFAULT_POLL_SECONDS


def test_poll_seconds_setting():
    src = create_market_data_source(
        PriceCache(), {"MASSIVE_API_KEY": "abc", "MASSIVE_POLL_SECONDS": "2.5"}
    )
    assert src._poll_seconds == 2.5


def test_blank_poll_seconds_uses_default():
    src = create_market_data_source(
        PriceCache(), {"MASSIVE_API_KEY": "abc", "MASSIVE_POLL_SECONDS": ""}
    )
    assert src._poll_seconds == DEFAULT_POLL_SECONDS


def test_reads_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "abc")
    assert isinstance(create_market_data_source(PriceCache()), MassiveDataSource)
    monkeypatch.delenv("MASSIVE_API_KEY")
    assert isinstance(create_market_data_source(PriceCache()), SimulatorDataSource)
