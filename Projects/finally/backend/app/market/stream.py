"""SSE endpoint: GET /api/stream/prices."""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .cache import PriceCache

STREAM_INTERVAL_SECONDS = 0.5


async def price_events(
    cache: PriceCache, interval: float = STREAM_INTERVAL_SECONDS
) -> AsyncIterator[str]:
    """Yield one SSE event per change: a JSON object keyed by ticker."""
    last_version = None
    while True:
        version = cache.version
        if version != last_version:
            last_version = version
            payload = {t: asdict(u) for t, u in cache.get_all().items()}
            yield f"data: {json.dumps(payload)}\n\n"
        else:
            yield ": keep-alive\n\n"  # comment line, ignored by EventSource
        await asyncio.sleep(interval)


def create_stream_router(cache: PriceCache) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices() -> StreamingResponse:
        return StreamingResponse(
            price_events(cache),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
