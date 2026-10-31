"""FastAPI application: wiring, lifespan and static file serving.

Run with ``uvicorn app.main:app``. Tests should call ``create_app(env_file=None)``.
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from .api import create_api_router, register_error_handlers
from .db import Database
from .llm import ChatService, create_chat_router
from .market import PriceCache, create_market_data_source
from .market.stream import create_stream_router
from .portfolio import PortfolioService

logger = logging.getLogger(__name__)

# An explicit path, never an upward search: that would find the repository-root .env.
ENV_FILE = Path(__file__).parents[2] / ".env"
SNAPSHOT_SECONDS = 30.0


class FrontendStaticFiles(StaticFiles):
    """Serves the frontend export, without answering unknown /api/* paths with HTML."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)


async def run_snapshots(portfolio: PortfolioService, interval: float) -> None:
    """Record the portfolio value every `interval` seconds until cancelled."""
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(portfolio.record_snapshot)
        except Exception:  # one bad snapshot must not end the history
            logger.exception("Could not record a portfolio snapshot")


def _record_first_snapshot(portfolio: PortfolioService) -> None:
    if not portfolio.get_history(limit=1):
        portfolio.record_snapshot()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    state = app.state
    snapshots = None
    await asyncio.to_thread(state.db.init)
    try:
        tickers = await asyncio.to_thread(state.portfolio.tracked_tickers)
        await state.source.start(tickers)
        await asyncio.to_thread(_record_first_snapshot, state.portfolio)
        snapshots = asyncio.create_task(
            run_snapshots(state.portfolio, state.snapshot_seconds), name="portfolio-snapshots"
        )
        yield
    finally:
        if snapshots is not None:
            snapshots.cancel()
            await asyncio.gather(snapshots, return_exceptions=True)
        await state.source.stop()


def _mount_frontend(app: FastAPI) -> None:
    static_dir = Path(os.environ.get("STATIC_DIR") or "static")
    if static_dir.is_dir():
        app.mount("/", FrontendStaticFiles(directory=static_dir, html=True), name="frontend")
    else:
        logger.warning(
            "No frontend export at %s: serving the API only, so / returns 404. "
            "Build the frontend and set STATIC_DIR to its output.",
            static_dir.resolve(),
        )


def create_app(
    env_file: Path | None = ENV_FILE, snapshot_seconds: float = SNAPSHOT_SECONDS
) -> FastAPI:
    """Build the app. Pass env_file=None to ignore any .env file."""
    if env_file is not None and Path(env_file).is_file():
        load_dotenv(env_file, override=False)

    db = Database()
    cache = PriceCache()
    source = create_market_data_source(cache)
    portfolio = PortfolioService(db, cache, source)

    app = FastAPI(title="FinAlly", lifespan=_lifespan)
    app.state.db = db
    app.state.cache = cache
    app.state.source = source
    app.state.portfolio = portfolio
    app.state.snapshot_seconds = snapshot_seconds

    register_error_handlers(app)
    app.include_router(create_api_router(portfolio, source))
    app.include_router(create_stream_router(cache))
    app.include_router(create_chat_router(ChatService(db, portfolio)))
    # Add new /api routers above this line: the mount at "/" catches everything after it.
    _mount_frontend(app)
    return app


def __getattr__(name: str) -> FastAPI:
    """Build `app` on first access, so importing create_app never reads the .env file."""
    if name == "app":
        instance = create_app(ENV_FILE)
        globals()["app"] = instance
        return instance
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
