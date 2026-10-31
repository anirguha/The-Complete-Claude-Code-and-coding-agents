"""The LLM's output: the schema we request, and the tolerant parser we apply.

These are deliberately two things. `AssistantReply` goes to the provider as a
strict JSON schema, where every field must be required, so it has no defaults.
`parse_reply` then treats whatever comes back as untrusted: omitted arrays are
fine, and a bad item stays in the list so it can be reported as one failed action
instead of discarding the whole reply.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel
from pydantic_core import from_json


class TradeInstruction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistInstruction(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class AssistantReply(BaseModel):
    """The `response_format` sent to the LLM."""

    message: str
    trades: list[TradeInstruction]
    watchlist_changes: list[WatchlistInstruction]


class ReplyParseError(ValueError):
    """The reply is unusable as a whole. Its text never contains the reply itself."""


@dataclass
class ParsedReply:
    message: str
    trades: list[Any] = field(default_factory=list)  # unvalidated items
    watchlist_changes: list[Any] = field(default_factory=list)


def _items(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ReplyParseError(f"{key} is not an array")
    return value


def parse_reply(content: object) -> ParsedReply:
    """Raise ReplyParseError unless `content` is a JSON object with a usable message."""
    if not isinstance(content, str):
        raise ReplyParseError("the reply has no text")
    try:
        # Unlike json.loads, this refuses NaN and lone surrogates, neither of
        # which could be stored or sent on to the browser.
        data = from_json(content, allow_inf_nan=False)
    except ValueError:
        raise ReplyParseError("the reply is not valid JSON") from None
    if not isinstance(data, dict):
        raise ReplyParseError("the reply is not a JSON object")
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ReplyParseError("the reply has no message")
    return ParsedReply(message, _items(data, "trades"), _items(data, "watchlist_changes"))
