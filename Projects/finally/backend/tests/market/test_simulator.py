import asyncio
import math
import random
import statistics

import pytest

from app.market import InvalidTickerError, MarketDataSource, PriceCache
from app.market.seed_prices import KNOWN_TICKERS, UNKNOWN_SEED_RANGE, params_for
from app.market.simulator import (
    TRADING_SECONDS_PER_YEAR,
    GBMSimulator,
    SimulatorDataSource,
)

DT = 0.5 / TRADING_SECONDS_PER_YEAR


def _returns(simulator: GBMSimulator, tickers: list[str], n: int) -> dict[str, list[float]]:
    prev = simulator.step()
    out: dict[str, list[float]] = {t: [] for t in tickers}
    for _ in range(n):
        cur = simulator.step()
        for t in tickers:
            out[t].append(math.log(cur[t] / prev[t]))
        prev = cur
    return out


def _corr(a: list[float], b: list[float]) -> float:
    return statistics.correlation(a, b)


# ---------- seed params ----------

def test_known_tickers_cover_default_watchlist():
    assert set(KNOWN_TICKERS) == {
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX",
    }


def test_unknown_params_deterministic_and_in_range():
    a, b = params_for("PYPL"), params_for("PYPL")
    assert a == b
    assert UNKNOWN_SEED_RANGE[0] <= a.seed_price <= UNKNOWN_SEED_RANGE[1]
    assert a.sector is None
    assert params_for("ZZZZ").seed_price != a.seed_price


# ---------- GBMSimulator ----------

def test_add_returns_seed_and_is_idempotent():
    sim = GBMSimulator(rng=random.Random(1))
    assert sim.add_ticker("AAPL") == 190.0
    sim.step()
    assert sim.add_ticker("AAPL") != 190.0  # not reset


def test_remove_ticker():
    sim = GBMSimulator(rng=random.Random(1))
    sim.add_ticker("AAPL")
    sim.remove_ticker("AAPL")
    sim.remove_ticker("AAPL")
    assert sim.step() == {}


def test_determinism():
    def run(seed):
        s = GBMSimulator(rng=random.Random(seed))
        for t in ("AAPL", "TSLA", "JPM"):
            s.add_ticker(t)
        for _ in range(100):
            last = s.step()
        return last

    assert run(5) == run(5)
    assert run(5) != run(6)


def test_prices_stay_positive():
    sim = GBMSimulator(rng=random.Random(2), event_probability=0.05)
    sim.add_ticker("TSLA")
    for _ in range(5000):
        assert sim.step()["TSLA"] > 0


def test_full_default_watchlist_steps():
    sim = GBMSimulator(event_probability=0.0, rng=random.Random(3))
    for t in KNOWN_TICKERS:
        sim.add_ticker(t)
    for _ in range(100):
        prices = sim.step()
    assert set(prices) == set(KNOWN_TICKERS)
    assert all(p > 0 and p != KNOWN_TICKERS[t].seed_price for t, p in prices.items())


def test_sigma_matches_target():
    sim = GBMSimulator(event_probability=0.0, rng=random.Random(7))
    sim.add_ticker("AAPL")
    rets = _returns(sim, ["AAPL"], 200_000)["AAPL"]
    measured = statistics.stdev(rets) / math.sqrt(DT)
    assert measured == pytest.approx(KNOWN_TICKERS["AAPL"].sigma, rel=0.02)


def test_correlations():
    sim = GBMSimulator(event_probability=0.0, rng=random.Random(11))
    for t in ("AAPL", "MSFT", "JPM", "V", "TSLA"):
        sim.add_ticker(t)
    r = _returns(sim, ["AAPL", "MSFT", "JPM", "V", "TSLA"], 100_000)
    assert _corr(r["AAPL"], r["MSFT"]) == pytest.approx(0.6, abs=0.02)
    assert _corr(r["JPM"], r["V"]) == pytest.approx(0.5, abs=0.02)
    assert _corr(r["AAPL"], r["JPM"]) == pytest.approx(0.3, abs=0.02)
    assert _corr(r["AAPL"], r["TSLA"]) == pytest.approx(0.3, abs=0.02)


def test_events_rate_and_size():
    prob = 0.0005
    sim = GBMSimulator(event_probability=prob, rng=random.Random(13))
    n = 400_000
    events = [sim._event_return() for _ in range(n)]
    hits = [e for e in events if e != 0.0]
    assert len(hits) / n == pytest.approx(prob, rel=0.15)
    assert all(0.02 <= abs(e) <= 0.05 for e in hits)
    ups = sum(1 for e in hits if e > 0)
    assert 0.35 < ups / len(hits) < 0.65


def test_no_events_when_probability_zero():
    sim = GBMSimulator(event_probability=0.0, rng=random.Random(1))
    assert all(sim._event_return() == 0.0 for _ in range(10_000))


# ---------- SimulatorDataSource ----------

async def test_implements_interface():
    assert issubclass(SimulatorDataSource, MarketDataSource)


async def test_start_fills_cache_before_returning():
    cache = PriceCache()
    src = SimulatorDataSource(cache, tick_seconds=0.01)
    await src.start(["aapl", "MSFT"])
    try:
        assert cache.get_price("AAPL") is not None
        assert cache.get_price("MSFT") is not None
        assert src.get_tickers() == ["AAPL", "MSFT"]
    finally:
        await src.stop()


async def test_prices_tick():
    cache = PriceCache()
    src = SimulatorDataSource(cache, tick_seconds=0.01)
    await src.start(["AAPL"])
    try:
        v = cache.version
        await asyncio.sleep(0.1)
        assert cache.version > v
        assert src.status().last_success_at is not None
        assert src.status().mode == "simulated"
        assert src.status().source == "simulator"
    finally:
        await src.stop()


async def test_add_remove_ticker():
    cache = PriceCache()
    src = SimulatorDataSource(cache, tick_seconds=0.01)
    await src.start(["AAPL"])
    try:
        await src.add_ticker("pypl")
        await src.add_ticker("PYPL")  # repeat is safe
        assert src.get_tickers() == ["AAPL", "PYPL"]
        assert cache.get_price("PYPL") is not None
        await src.remove_ticker("pypl")
        await src.remove_ticker("PYPL")
        assert src.get_tickers() == ["AAPL"]
        assert cache.get("PYPL") is None
        await asyncio.sleep(0.05)
        assert cache.get("PYPL") is None
    finally:
        await src.stop()


async def test_invalid_ticker():
    src = SimulatorDataSource(PriceCache())
    with pytest.raises(InvalidTickerError):
        await src.add_ticker("not valid!")
    with pytest.raises(InvalidTickerError):
        await src.remove_ticker("")


async def test_stop_twice_and_no_writes_after_stop():
    cache = PriceCache()
    src = SimulatorDataSource(cache, tick_seconds=0.01)
    await src.start(["AAPL"])
    await src.stop()
    await src.stop()
    v = cache.version
    await asyncio.sleep(0.05)
    assert cache.version == v


async def test_stop_without_start():
    await SimulatorDataSource(PriceCache()).stop()


async def test_start_twice_one_task():
    src = SimulatorDataSource(PriceCache(), tick_seconds=0.01)
    await src.start(["AAPL"])
    task = src._task
    await src.start(["MSFT"])
    try:
        assert src._task is task
        assert src.get_tickers() == ["AAPL", "MSFT"]
    finally:
        await src.stop()


async def test_error_recovery():
    class Flaky(GBMSimulator):
        calls = 0

        def step(self):
            Flaky.calls += 1
            if Flaky.calls == 1:
                raise RuntimeError("boom")
            return super().step()

    cache = PriceCache()
    src = SimulatorDataSource(cache, tick_seconds=0.01, simulator=Flaky(rng=random.Random(1)))
    await src.start(["AAPL"])
    try:
        await asyncio.sleep(0.1)
        assert Flaky.calls > 2
        assert src.status().last_error is None  # recovered
        assert src.status().last_success_at is not None
    finally:
        await src.stop()


async def test_error_is_recorded():
    class Broken(GBMSimulator):
        def step(self):
            raise RuntimeError("boom")

    src = SimulatorDataSource(PriceCache(), tick_seconds=0.01, simulator=Broken())
    await src.start(["AAPL"])
    try:
        await asyncio.sleep(0.05)
        assert src.status().last_error == "boom"
    finally:
        await src.stop()
