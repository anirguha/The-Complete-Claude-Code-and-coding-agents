"""Tests for the SSE price stream."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


def test_create_stream_router_returns_independent_routers():
    first = create_stream_router(PriceCache())
    second = create_stream_router(PriceCache())

    assert first is not second
    assert [route.path for route in first.routes] == ["/api/stream/prices"]
    assert [route.path for route in second.routes] == ["/api/stream/prices"]


@pytest.mark.asyncio
async def test_generate_events_streams_prices_and_stops_on_disconnect():
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        is_disconnected=AsyncMock(side_effect=[False, False, True]),
    )
    events = _generate_events(cache, request, interval=0)

    assert await anext(events) == "retry: 1000\n\n"
    event = await anext(events)
    prices = json.loads(event.removeprefix("data: ").strip())
    assert prices["AAPL"]["price"] == 190.50

    with pytest.raises(StopAsyncIteration):
        await anext(events)
