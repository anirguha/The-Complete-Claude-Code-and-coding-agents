"""REST routes for health, portfolio and watchlist. Chat and SSE have their own routers."""

import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictFloat

from ..market import MarketDataSource
from ..portfolio import NotFoundError, PortfolioService, ServiceError, UnavailableError


class TradeRequest(BaseModel):
    ticker: str
    quantity: StrictFloat
    side: str  # checked by the service, so a bad value is a 400 and not a 422


class WatchlistRequest(BaseModel):
    ticker: str


def create_api_router(portfolio: PortfolioService, source: MarketDataSource) -> APIRouter:
    router = APIRouter(prefix="/api")

    # Plain `def` routes run on FastAPI's thread pool, so SQLite never blocks the event loop.

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "market": asdict(source.status())}

    @router.get("/portfolio")
    def get_portfolio() -> dict[str, Any]:
        return portfolio.get_portfolio()

    @router.post("/portfolio/trade")
    async def trade(request: TradeRequest) -> dict[str, Any]:
        result = await portfolio.execute_trade(request.ticker, request.side, request.quantity)
        return {"trade": result, "portfolio": await asyncio.to_thread(portfolio.get_portfolio)}

    @router.get("/portfolio/history")
    def history() -> dict[str, Any]:
        return {"snapshots": portfolio.get_history()}

    @router.get("/watchlist")
    def get_watchlist() -> dict[str, Any]:
        return {"watchlist": portfolio.list_watchlist()}

    @router.post("/watchlist")
    async def add_watchlist(request: WatchlistRequest) -> dict[str, Any]:
        return await portfolio.add_watchlist(request.ticker)

    @router.delete("/watchlist/{ticker}")
    async def remove_watchlist(ticker: str) -> dict[str, Any]:
        return await portfolio.remove_watchlist(ticker)

    return router


def register_error_handlers(app: FastAPI) -> None:
    def respond_with(status_code: int):
        async def handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status_code)

        return handler

    app.add_exception_handler(ServiceError, respond_with(400))
    app.add_exception_handler(NotFoundError, respond_with(404))
    app.add_exception_handler(UnavailableError, respond_with(503))
