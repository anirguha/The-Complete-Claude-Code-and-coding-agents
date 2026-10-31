import asyncio
import json
from types import SimpleNamespace as NS

import pytest
from massive.exceptions import BadResponse
from urllib3.exceptions import MaxRetryError

from app.market import InvalidTickerError, MarketDataSource, MarketDataUnavailableError, PriceCache
from app.market import massive_client as mc
from app.market.massive_client import MassiveDataSource, parse_snapshot

NOT_ENTITLED = json.dumps(
    {"status": "NOT_AUTHORIZED", "message": "You are not entitled to this data."}
)
NOT_FOUND = json.dumps({"status": "NOT_FOUND", "message": "Ticker not found."})
# 2026-10-29 16:00 Eastern in ms
EOD_MS = 1793304000000


def snap(ticker, trade=None, minute=None, day=None, prev=None, updated=None):
    return NS(
        ticker=ticker,
        last_trade=NS(price=trade[0], sip_timestamp=trade[1]) if trade else None,
        min=NS(close=minute[0], timestamp=minute[1]) if minute else None,
        day=NS(close=day) if day is not None else None,
        prev_day=NS(close=prev) if prev is not None else None,
        updated=updated,
    )


class FakeClient:
    def __init__(self):
        self.snapshots = {}
        self.snapshot_error = None
        self.details_error = None
        self.probe = [NS(timestamp=EOD_MS)]
        self.grouped = []
        self.calls = []

    def get_snapshot_all(self, market, tickers):
        self.calls.append(("snapshot", tuple(tickers)))
        if self.snapshot_error:
            raise self.snapshot_error
        return [self.snapshots[t] for t in tickers if t in self.snapshots]

    def get_previous_close_agg(self, ticker):
        self.calls.append(("prev", ticker))
        return self.probe

    def get_grouped_daily_aggs(self, date):
        self.calls.append(("grouped", date))
        return self.grouped

    def get_ticker_details(self, ticker):
        self.calls.append(("details", ticker))
        if self.details_error:
            raise self.details_error
        return NS(name=ticker)


def make(client=None, poll=0.01):
    cache = PriceCache()
    client = client or FakeClient()
    return MassiveDataSource(cache, "key", poll, client=client), cache, client


# ---------- pure helpers ----------

def test_to_unix_seconds_units():
    assert mc.to_unix_seconds(1_700_000_000) == 1_700_000_000
    assert mc.to_unix_seconds(1_700_000_000_000) == 1_700_000_000
    assert mc.to_unix_seconds(1_700_000_000_000_000_000) == 1_700_000_000


def test_trading_date_is_eastern():
    # 16:00 Eastern and 00:00 Eastern stamps both give the same date
    assert mc.trading_date(1793304000000) == "2026-10-29"
    assert mc.trading_date(1793246400000) == "2026-10-29"


def test_parse_prefers_trade():
    s = snap("A", trade=(10.0, 1_700_000_000_000_000_000), minute=(9.0, 1_700_000_000_000))
    assert parse_snapshot(s) == (10.0, 1_700_000_000.0)


def test_parse_falls_back_to_minute():
    s = snap("A", minute=(9.0, 1_700_000_000_000))
    assert parse_snapshot(s) == (9.0, 1_700_000_000.0)


def test_parse_zero_trade_falls_back():
    s = snap("A", trade=(0, 1_700_000_000_000_000_000), minute=(9.0, 1_700_000_000_000))
    assert parse_snapshot(s)[0] == 9.0


def test_parse_day_then_prev_day():
    s = snap("A", day=8.0, prev=7.0, updated=1_700_000_000_000_000_000)
    assert parse_snapshot(s) == (8.0, 1_700_000_000.0)
    s = snap("A", day=0, prev=7.0, updated=1_700_000_000_000_000_000)
    assert parse_snapshot(s)[0] == 7.0


def test_parse_without_updated_uses_now():
    price, ts = parse_snapshot(snap("A", prev=7.0))
    assert price == 7.0 and ts > 1_700_000_000


def test_parse_empty_snapshot():
    assert parse_snapshot(snap("A")) is None
    assert parse_snapshot(snap("A", day=0, prev=0)) is None


def test_error_classifiers():
    assert mc.is_not_entitled(BadResponse(NOT_ENTITLED))
    assert mc.is_not_entitled(BadResponse("You are not entitled"))
    assert not mc.is_not_entitled(BadResponse("Unknown API Key"))
    assert not mc.is_not_entitled(RuntimeError(NOT_ENTITLED))
    assert mc.is_not_found(BadResponse(NOT_FOUND))
    assert not mc.is_not_found(BadResponse("plain text"))
    assert not mc.is_not_found(BadResponse("[1]"))
    assert not mc.is_not_found(RuntimeError(NOT_FOUND))


def test_implements_interface():
    assert issubclass(MassiveDataSource, MarketDataSource)


def test_delay_logic():
    src, _, _ = make(poll=5.0)
    assert src._delay(0) == 5.0
    assert src._delay(1) == 10.0
    assert src._delay(2) == 20.0
    assert src._delay(10) == mc.MAX_BACKOFF_SECONDS
    src._mode = "eod"
    assert src._delay(0) == mc.EOD_REFRESH_SECONDS


# ---------- refresh logic (called directly, no timing) ----------

async def test_live_refresh_writes_cache():
    src, cache, client = make()
    client.snapshots = {
        "AAPL": snap("AAPL", trade=(190.5, 1_700_000_000_000_000_000)),
        "MSFT": snap("MSFT", minute=(420.0, 1_700_000_000_000)),
    }
    await src.start([])  # no tickers; stop the task immediately
    await src.stop()
    src._tickers.update({"AAPL", "MSFT", "GONE"})
    await src._refresh()
    assert cache.get_price("AAPL") == 190.5
    assert cache.get_price("MSFT") == 420.0
    assert cache.get("GONE") is None
    assert src.status().mode == "live"
    assert client.calls == [("snapshot", ("AAPL", "GONE", "MSFT"))]


async def test_live_refresh_no_tickers_makes_no_request():
    src, _, client = make()
    await src._refresh()
    assert client.calls == []


async def test_ticker_removed_during_request_is_not_resurrected():
    client = FakeClient()
    client.snapshots = {"AAPL": snap("AAPL", minute=(1.0, 1_700_000_000_000))}
    src, cache, _ = make(client)
    src._tickers.add("AAPL")
    original = client.get_snapshot_all

    def slow(market, tickers):
        result = original(market, tickers)
        src._tickers.discard("AAPL")  # removed while the request was in flight
        return result

    client.get_snapshot_all = slow
    await src._refresh()
    assert cache.get("AAPL") is None


async def test_moves_to_eod_when_not_entitled():
    client = FakeClient()
    client.snapshot_error = BadResponse(NOT_ENTITLED)
    client.grouped = [
        NS(ticker="AAPL", close=348.91, timestamp=EOD_MS),
        NS(ticker="ZERO", close=0, timestamp=EOD_MS),
    ]
    src, cache, _ = make(client)
    src._tickers.update({"AAPL", "ZERO", "MISSING"})
    await src._refresh()
    assert src.status().mode == "eod"
    assert cache.get_price("AAPL") == 348.91
    assert cache.get("ZERO") is None and cache.get("MISSING") is None
    assert ("grouped", "2026-10-29") in client.calls

    # Next refresh stays in eod, does not hit snapshots, does not refetch same date
    client.calls.clear()
    await src._refresh()
    assert client.calls == [("prev", "SPY")]


async def test_eod_refetches_when_date_changes():
    client = FakeClient()
    client.snapshot_error = BadResponse(NOT_ENTITLED)
    client.grouped = [NS(ticker="AAPL", close=1.0, timestamp=EOD_MS)]
    src, cache, _ = make(client)
    src._tickers.add("AAPL")
    await src._refresh()
    client.probe = [NS(timestamp=EOD_MS + 86_400_000)]
    client.grouped = [NS(ticker="AAPL", close=2.0, timestamp=EOD_MS + 86_400_000)]
    await src._refresh()
    assert cache.get_price("AAPL") == 2.0


async def test_eod_empty_probe_is_noop():
    client = FakeClient()
    client.probe = []
    src, cache, _ = make(client)
    src._mode = "eod"
    await src._refresh()
    assert cache.get_all() == {}


async def test_other_bad_response_propagates():
    client = FakeClient()
    client.snapshot_error = BadResponse('{"status":"ERROR","error":"Unknown API Key"}')
    src, _, _ = make(client)
    src._tickers.add("AAPL")
    with pytest.raises(BadResponse):
        await src._refresh()
    assert src.status().mode == "live"


# ---------- add / remove ----------

async def test_add_ticker_live_validates_and_prices():
    client = FakeClient()
    client.snapshots = {"PYPL": snap("PYPL", minute=(60.0, 1_700_000_000_000))}
    src, cache, _ = make(client)
    await src.add_ticker("pypl")
    assert src.get_tickers() == ["PYPL"]
    assert cache.get_price("PYPL") == 60.0
    assert [c[0] for c in client.calls] == ["details", "snapshot"]
    client.calls.clear()
    await src.add_ticker("PYPL")  # repeat: no requests
    assert client.calls == []


async def test_add_unknown_ticker_rejected():
    client = FakeClient()
    client.details_error = BadResponse(NOT_FOUND)
    src, _, _ = make(client)
    with pytest.raises(InvalidTickerError):
        await src.add_ticker("ZZZZQ")
    assert src.get_tickers() == []


async def test_add_ticker_unavailable():
    client = FakeClient()
    client.details_error = MaxRetryError(None, "/x")
    src, _, _ = make(client)
    with pytest.raises(MarketDataUnavailableError):
        await src.add_ticker("AAPL")
    client.details_error = BadResponse('{"status":"ERROR"}')
    with pytest.raises(MarketDataUnavailableError):
        await src.add_ticker("AAPL")
    assert src.get_tickers() == []


async def test_add_malformed_ticker():
    src, _, _ = make()
    with pytest.raises(InvalidTickerError):
        await src.add_ticker("bad ticker")


async def test_add_ticker_pricing_failure_is_tolerated():
    client = FakeClient()
    client.snapshot_error = MaxRetryError(None, "/x")
    src, cache, _ = make(client)
    await src.add_ticker("AAPL")
    assert src.get_tickers() == ["AAPL"]
    assert cache.get("AAPL") is None


async def test_add_ticker_with_empty_snapshot_result():
    src, cache, _ = make()
    await src.add_ticker("AAPL")
    assert cache.get("AAPL") is None


async def test_add_ticker_in_eod_uses_summary_without_requests():
    client = FakeClient()
    src, cache, _ = make(client)
    src._mode = "eod"
    src._eod_closes = {"AAPL": (348.91, 1_793_304_000.0)}
    await src.add_ticker("AAPL")
    assert cache.get_price("AAPL") == 348.91
    assert client.calls == []


async def test_add_ticker_in_eod_not_in_summary_validates_only():
    client = FakeClient()
    src, cache, _ = make(client)
    src._mode = "eod"
    await src.add_ticker("AAPL")
    assert [c[0] for c in client.calls] == ["details"]
    assert cache.get("AAPL") is None


async def test_remove_ticker():
    src, cache, _ = make()
    src._tickers.add("AAPL")
    cache.update("AAPL", 1.0, 1.0)
    await src.remove_ticker("aapl")
    await src.remove_ticker("AAPL")
    assert src.get_tickers() == []
    assert cache.get("AAPL") is None
    with pytest.raises(InvalidTickerError):
        await src.remove_ticker("")


# ---------- the polling task ----------

async def test_start_polls_and_stop_is_idempotent():
    client = FakeClient()
    client.snapshots = {"AAPL": snap("AAPL", trade=(10.0, 1_700_000_000_000_000_000))}
    src, cache, _ = make(client)
    await src.start(["aapl"])
    task = src._task
    await src.start(["AAPL"])
    assert src._task is task
    for _ in range(100):
        if cache.get_price("AAPL"):
            break
        await asyncio.sleep(0.01)
    assert cache.get_price("AAPL") == 10.0
    assert src.status().last_success_at is not None
    assert src.status().last_error is None
    await src.stop()
    await src.stop()


async def test_outage_and_recovery():
    client = FakeClient()
    client.snapshots = {"AAPL": snap("AAPL", trade=(10.0, 1_700_000_000_000_000_000))}
    client.snapshot_error = MaxRetryError(None, "/x", reason="429")
    src, cache, _ = make(client, poll=0.001)
    await src.start(["AAPL"])
    try:
        for _ in range(200):
            if src.status().last_error:
                break
            await asyncio.sleep(0.005)
        assert src.status().last_error
        assert cache.get("AAPL") is None
        client.snapshot_error = None
        for _ in range(400):
            if cache.get("AAPL"):
                break
            await asyncio.sleep(0.005)
        assert cache.get_price("AAPL") == 10.0
        assert src.status().last_error is None
    finally:
        await src.stop()


async def test_invalid_key_keeps_retrying_with_error_status():
    client = FakeClient()
    client.snapshot_error = BadResponse('{"status":"ERROR","error":"Unknown API Key"}')
    src, cache, _ = make(client, poll=0.001)
    await src.start(["AAPL"])
    try:
        for _ in range(200):
            if src.status().last_error:
                break
            await asyncio.sleep(0.005)
        assert "Unknown API Key" in src.status().last_error
        assert src.status().mode == "live"
        assert cache.get_all() == {}
    finally:
        await src.stop()


async def test_unexpected_exception_does_not_kill_task():
    client = FakeClient()
    client.snapshot_error = ValueError("weird")
    src, _, _ = make(client, poll=0.001)
    await src.start(["AAPL"])
    try:
        for _ in range(200):
            if src.status().last_error == "weird":
                break
            await asyncio.sleep(0.005)
        assert src.status().last_error == "weird"
        assert not src._task.done()
    finally:
        await src.stop()


def test_default_client_is_built_without_retries():
    src = MassiveDataSource(PriceCache(), "key")
    assert src._client is not None
