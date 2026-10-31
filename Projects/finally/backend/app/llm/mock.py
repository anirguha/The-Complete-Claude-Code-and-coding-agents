"""Deterministic replies for LLM_MOCK=true. The table is in TEAM_CONTRACT.md."""

import re

from .schema import ParsedReply

DEFAULT_MESSAGE = "Mock response: I am FinAlly, your AI trading assistant."

_TRADE = re.compile(r"(buy|sell)\s+([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s+(\S+)", re.IGNORECASE)
_WATCHLIST = re.compile(r"(add|remove)\s+(\S+)", re.IGNORECASE)


def mock_reply(text: str) -> ParsedReply:
    """Build the reply. Actions then run exactly as an LLM's would."""
    text = text.strip()
    if match := _TRADE.fullmatch(text):
        side, quantity, ticker = match[1].lower(), match[2], match[3].upper()
        verb = "buying" if side == "buy" else "selling"
        return ParsedReply(
            f"Mock: {verb} {quantity} shares of {ticker}.",
            trades=[{"ticker": ticker, "side": side, "quantity": float(quantity)}],
        )
    if match := _WATCHLIST.fullmatch(text):
        action, ticker = match[1].lower(), match[2].upper()
        message = (
            f"Mock: adding {ticker} to your watchlist."
            if action == "add"
            else f"Mock: removing {ticker} from your watchlist."
        )
        return ParsedReply(message, watchlist_changes=[{"ticker": ticker, "action": action}])
    return ParsedReply(DEFAULT_MESSAGE)
