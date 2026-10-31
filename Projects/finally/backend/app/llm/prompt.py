"""Builds the messages sent to the LLM."""

import json
from typing import Any

SYSTEM_PROMPT = """\
You are FinAlly, an AI trading assistant inside a simulated trading workstation. \
All money is virtual.

Your job:
- Analyze portfolio composition, risk concentration and P&L.
- Suggest trades, with your reasoning.
- Execute trades when the user asks or agrees, by listing them in `trades`. They run \
immediately at the current market price, with no confirmation step.
- Manage the watchlist proactively, by listing changes in `watchlist_changes`.
- Be concise and data-driven. Use the figures in the portfolio context below.

Rules:
- Always respond with valid JSON matching the requested schema: `message` is the text \
shown to the user, `trades` is a list of {ticker, side ("buy" or "sell"), quantity}, and \
`watchlist_changes` is a list of {ticker, action ("add" or "remove")}. Use empty lists \
when there is nothing to do.
- Only list an action you intend to happen now. Never list one merely to illustrate a \
suggestion.
- Actions run after you reply and can fail, for example on insufficient cash. The user \
sees each result next to your message, so say what you are doing rather than claiming \
it is done.
- Earlier assistant turns may end with an "[Action results: ...]" line. That is a system \
record of what happened. Never write one yourself.
"""


def _describe_trade(trade: dict[str, Any]) -> str:
    action = f"{trade.get('side')} {trade.get('quantity')} {trade.get('ticker')}"
    if trade.get("status") == "executed":
        return f"{action} executed at {trade.get('price')}"
    return f"{action} failed: {trade.get('error')}"


def _describe_change(change: dict[str, Any]) -> str:
    action = f"{change.get('action')} {change.get('ticker')}"
    if change.get("status") == "applied":
        return f"{action} applied"
    return f"{action} failed: {change.get('error')}"


def _history_content(message: dict[str, Any]) -> str:
    """A stored message, plus what its actions did: the reply alone was written beforehand."""
    actions = message.get("actions") or {}
    results = [
        *map(_describe_trade, actions.get("trades", [])),
        *map(_describe_change, actions.get("watchlist_changes", [])),
    ]
    if not results:
        return message["content"]
    return f"{message['content']}\n[Action results: {'; '.join(results)}]"


def build_messages(
    portfolio: dict[str, Any],
    watchlist: list[dict[str, Any]],
    history: list[dict[str, Any]],
    text: str,
) -> list[dict[str, str]]:
    context = json.dumps({"portfolio": portfolio, "watchlist": watchlist})
    return [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\nCurrent portfolio context (JSON):\n{context}"},
        *({"role": m["role"], "content": _history_content(m)} for m in history),
        {"role": "user", "content": text},
    ]
