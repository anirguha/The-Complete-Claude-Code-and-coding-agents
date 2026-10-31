import dataclasses
import threading

import pytest

from app.market import InvalidTickerError, PriceCache, PriceUpdate, normalize_ticker


@pytest.mark.parametrize(
    "raw,expected",
    [("aapl", "AAPL"), (" msft ", "MSFT"), ("v", "V"), ("brk.b", "BRK.B")],
)
def test_normalize_ticker_ok(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "TOOLONG", "A1", "AA.", ".B", "A.BC", "A B", "A-B"])
def test_normalize_ticker_rejects_malformed(raw):
    with pytest.raises(InvalidTickerError):
        normalize_ticker(raw)


def test_invalid_ticker_is_value_error():
    assert issubclass(InvalidTickerError, ValueError)


def test_price_update_is_frozen():
    update = PriceUpdate("A", 1.0, 1.0, 1.0, 0.0, "flat")
    with pytest.raises(dataclasses.FrozenInstanceError):
        update.price = 2.0  # type: ignore[misc]


def test_first_update_is_flat():
    cache = PriceCache()
    u = cache.update("AAPL", 190.123, 100.0)
    assert u.price == 190.12
    assert u.previous_price == 190.12
    assert u.change == 0.0
    assert u.direction == "flat"


def test_direction_and_change():
    cache = PriceCache()
    cache.update("AAPL", 100.0, 1.0)
    up = cache.update("AAPL", 101.5, 2.0)
    assert (up.direction, up.change, up.previous_price) == ("up", 1.5, 100.0)
    down = cache.update("AAPL", 100.0, 3.0)
    assert (down.direction, down.change) == ("down", -1.5)
    flat = cache.update("AAPL", 100.0, 4.0)
    assert (flat.direction, flat.change) == ("flat", 0.0)


def test_rounds_to_cents():
    cache = PriceCache()
    assert cache.update("X", 10.006, 1.0).price == 10.01
    assert cache.get_price("X") == 10.01


def test_ignores_stale_and_equal_timestamps():
    cache = PriceCache()
    cache.update("AAPL", 100.0, 10.0)
    v = cache.version
    assert cache.update("AAPL", 200.0, 10.0).price == 100.0
    assert cache.update("AAPL", 200.0, 5.0).price == 100.0
    assert cache.version == v
    assert cache.get_price("AAPL") == 100.0


def test_default_timestamp_is_now():
    cache = PriceCache()
    u = cache.update("AAPL", 1.0)
    assert u.timestamp > 1_000_000_000


def test_get_missing():
    cache = PriceCache()
    assert cache.get("NOPE") is None
    assert cache.get_price("NOPE") is None
    assert cache.get_all() == {}


def test_get_all_returns_copy():
    cache = PriceCache()
    cache.update("A", 1.0, 1.0)
    snapshot = cache.get_all()
    snapshot.clear()
    assert "A" in cache.get_all()


def test_version_increments_and_remove():
    cache = PriceCache()
    assert cache.version == 0
    cache.update("A", 1.0, 1.0)
    assert cache.version == 1
    cache.remove("A")
    assert cache.version == 2
    assert cache.get("A") is None
    cache.remove("A")  # absent: no change
    assert cache.version == 2


def test_thread_safety():
    cache = PriceCache()

    def work(n):
        for i in range(200):
            cache.update(f"T{n}", 1.0 + i, float(i + 1))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert cache.version == 8 * 200
    assert all(cache.get_price(f"T{n}") == 200.0 for n in range(8))
