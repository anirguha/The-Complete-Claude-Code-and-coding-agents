import json

from fastapi import FastAPI

from app.market import PriceCache
from app.market.stream import create_stream_router, price_events


async def test_first_event_has_payload_shape():
    cache = PriceCache()
    cache.update("AAPL", 190.0, 1.0)
    cache.update("AAPL", 190.5, 2.0)
    events = price_events(cache, interval=0.001)
    event = await anext(events)
    assert event.startswith("data: ") and event.endswith("\n\n")
    payload = json.loads(event[len("data: "):])
    assert payload == {
        "AAPL": {
            "ticker": "AAPL",
            "price": 190.5,
            "previous_price": 190.0,
            "timestamp": 2.0,
            "change": 0.5,
            "direction": "up",
        }
    }
    await events.aclose()


async def test_keep_alive_when_idle_then_data_on_change():
    cache = PriceCache()
    cache.update("AAPL", 1.0, 1.0)
    events = price_events(cache, interval=0.001)
    assert (await anext(events)).startswith("data: ")
    assert await anext(events) == ": keep-alive\n\n"
    cache.update("MSFT", 2.0, 1.0)
    event = await anext(events)
    assert set(json.loads(event[6:])) == {"AAPL", "MSFT"}
    await events.aclose()


async def test_removed_ticker_disappears():
    cache = PriceCache()
    cache.update("AAPL", 1.0, 1.0)
    cache.update("MSFT", 1.0, 1.0)
    events = price_events(cache, interval=0.001)
    await anext(events)
    cache.remove("MSFT")
    assert set(json.loads((await anext(events))[6:])) == {"AAPL"}
    await events.aclose()


async def test_empty_cache_sends_empty_object():
    events = price_events(PriceCache(), interval=0.001)
    assert await anext(events) == "data: {}\n\n"
    await events.aclose()


def test_router_route_registered():
    app = FastAPI()
    app.include_router(create_stream_router(PriceCache()))
    paths = {r.path for r in app.routes}
    assert "/api/stream/prices" in paths
