import asyncio
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
    assert "/api/stream/prices" in app.openapi()["paths"]


async def test_endpoint_streams_prices_over_asgi():
    # Driven through raw ASGI: the stream never ends, and httpx's ASGI transport
    # would wait for the whole response body before returning.
    cache = PriceCache()
    cache.update("AAPL", 190.0, 1.0)
    app = FastAPI()
    app.include_router(create_stream_router(cache))
    messages = []
    got_event = asyncio.Event()

    async def receive():
        await asyncio.Event().wait()  # the client stays connected

    async def send(message):
        messages.append(message)
        if message.get("body"):
            got_event.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/stream/prices",
        "raw_path": b"/api/stream/prices",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "server": ("test", 80),
        "client": ("test", 1234),
    }
    task = asyncio.create_task(app(scope, receive, send))
    try:
        await asyncio.wait_for(got_event.wait(), timeout=5)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    start, body = messages[0], messages[1]["body"].decode()
    headers = dict(start["headers"])
    assert start["status"] == 200
    assert headers[b"content-type"].startswith(b"text/event-stream")
    assert headers[b"cache-control"] == b"no-cache"
    assert headers[b"x-accel-buffering"] == b"no"
    assert body.startswith("data: ") and body.endswith("\n\n")
    assert json.loads(body[len("data: "):])["AAPL"]["price"] == 190.0
