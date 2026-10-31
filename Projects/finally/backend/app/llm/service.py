"""One chat turn: reply, run the actions, store and return the result."""

import asyncio
import logging
import math
import os
from collections.abc import Awaitable, Mapping
from typing import Any

from .. import db as repo
from ..db import Database
from ..portfolio import PortfolioService, ServiceError, UnavailableError
from .client import request_completion
from .mock import mock_reply
from .prompt import build_messages
from .schema import ParsedReply, parse_reply

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20
DISPLAY_HISTORY_LIMIT = 50
MAX_LOGGED_ERROR_CHARS = 500

NOT_CONFIGURED_MESSAGE = (
    "LLM not configured. Set OPENROUTER_API_KEY to enable the AI assistant, "
    "or LLM_MOCK=true for mock responses."
)
FAILURE_MESSAGE = (
    "Sorry, I could not get a response just now, so no trades or watchlist changes "
    "were made. Please try again."
)
# UnavailableError's own text can carry a raw upstream error.
MARKET_UNAVAILABLE_MESSAGE = "Market data is unavailable right now"
UNEXPECTED_ERROR_MESSAGE = "Something went wrong, so this action was not completed"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _finite_number(value: Any) -> float | None:
    """The value as a float, or None if it cannot be a quantity or be sent as JSON."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def _redacted(error: Exception, secret: str) -> str:
    return str(error).replace(secret, "[redacted]")[:MAX_LOGGED_ERROR_CHARS]


async def _attempt(action: Awaitable[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    """Return (result, None) or (None, error): one failure must not stop the other actions."""
    try:
        return await action, None
    except UnavailableError:
        return None, MARKET_UNAVAILABLE_MESSAGE
    except ServiceError as exc:
        return None, exc.message
    except Exception:
        logger.exception("Chat action failed unexpectedly")
        return None, UNEXPECTED_ERROR_MESSAGE


class ChatService:
    def __init__(
        self,
        db: Database,
        portfolio: PortfolioService,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._db = db
        self._portfolio = portfolio
        self._environ = os.environ if environ is None else environ
        # One turn at a time, so each prompt sees the results of the turn before it.
        self._turn_lock = asyncio.Lock()

    async def handle_message(self, text: str) -> dict[str, Any]:
        text = text.strip()
        async with self._turn_lock:
            history = await asyncio.to_thread(self._load_history_and_store_user, text)
            reply = await self._get_reply(text, history)
            trades = [await self._run_trade(item) for item in reply.trades]
            changes = [await self._run_watchlist_change(item) for item in reply.watchlist_changes]
            response = {"message": reply.message, "trades": trades, "watchlist_changes": changes}
            await self._store_reply(response)
        return response

    def list_history(self) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            messages = repo.list_chat_messages(conn, DISPLAY_HISTORY_LIMIT)
        return [
            {key: m[key] for key in ("role", "content", "actions", "created_at")} for m in messages
        ]

    # The reply

    async def _get_reply(self, text: str, history: list[dict[str, Any]]) -> ParsedReply:
        if self._environ.get("LLM_MOCK", "").strip().lower() == "true":
            return mock_reply(text)
        api_key = self._environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            logger.warning("Chat is unavailable: OPENROUTER_API_KEY is not set")
            return ParsedReply(NOT_CONFIGURED_MESSAGE)
        try:
            portfolio, watchlist = await asyncio.to_thread(self._load_context)
            messages = build_messages(portfolio, watchlist, history, text)
            return parse_reply(await request_completion(messages, api_key))
        except Exception as exc:
            # Only the type and redacted text: tracebacks could carry the request.
            logger.error("LLM request failed: %s: %s", type(exc).__name__, _redacted(exc, api_key))
            return ParsedReply(FAILURE_MESSAGE)

    def _load_context(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return self._portfolio.get_portfolio(), self._portfolio.list_watchlist()

    # The actions. Each item is untrusted LLM output.

    async def _run_trade(self, item: Any) -> dict[str, Any]:
        fields = item if isinstance(item, dict) else {}
        ticker = _text(fields.get("ticker")).strip().upper()
        side = _text(fields.get("side"))
        quantity = _finite_number(fields.get("quantity"))

        trade, error = None, None
        if not ticker:
            error = "The trade has no ticker"
        elif quantity is None:
            error = "The trade quantity is not a number"
        else:
            trade, error = await _attempt(self._portfolio.execute_trade(ticker, side, quantity))

        if trade is None:
            return {
                "ticker": ticker,
                "side": side,
                "quantity": quantity or 0,
                "status": "failed",
                "price": None,
                "error": error,
            }
        return {
            "ticker": trade["ticker"],
            "side": trade["side"],
            "quantity": trade["quantity"],
            "status": "executed",
            "price": trade["price"],
            "error": None,
        }

    async def _run_watchlist_change(self, item: Any) -> dict[str, Any]:
        fields = item if isinstance(item, dict) else {}
        ticker = _text(fields.get("ticker")).strip().upper()
        action = _text(fields.get("action"))

        result, error = None, None
        if not ticker:
            error = "The watchlist change has no ticker"
        elif action == "add":
            result, error = await _attempt(self._portfolio.add_watchlist(ticker))
        elif action == "remove":
            result, error = await _attempt(self._portfolio.remove_watchlist(ticker))
        else:
            error = f"Invalid watchlist action: {action!r}. Use 'add' or 'remove'"

        return {
            "ticker": result["ticker"] if result else ticker,
            "action": action,
            "status": "applied" if result else "failed",
            "error": error,
        }

    # Storage. These run in worker threads and hold the write lock throughout.

    def _load_history_and_store_user(self, text: str) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            history = repo.list_chat_messages(conn, HISTORY_LIMIT)
            repo.insert_chat_message(conn, "user", text)
        return history

    def _store_assistant(self, response: dict[str, Any]) -> None:
        actions = {key: response[key] for key in ("trades", "watchlist_changes")}
        with self._db.connection() as conn:
            repo.insert_chat_message(conn, "assistant", response["message"], actions)

    async def _store_reply(self, response: dict[str, Any]) -> None:
        try:
            await asyncio.to_thread(self._store_assistant, response)
        except Exception:
            # The actions already ran, so the user must still be told about them.
            logger.exception("Could not store the assistant's reply")
