"""Real responses, checked field by field against the types the frontend compiles against.

`frontend/src/lib/types.ts` and `api.ts` are parsed rather than copied, so a change
on either side of the wire fails here. Fields must match exactly in both directions.
"""

import re
from pathlib import Path
from typing import Any

import pytest

from .conftest import read_stream

FRONTEND_LIB = Path(__file__).parents[3] / "frontend" / "src" / "lib"
TYPES_SOURCE = (FRONTEND_LIB / "types.ts").read_text()
API_SOURCE = (FRONTEND_LIB / "api.ts").read_text()


def _parse_types(source: str) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    interfaces: dict[str, dict[str, str]] = {}
    for name, parent, body in re.findall(
        r"export interface (\w+)(?: extends (\w+))? \{(.*?)\n\}", source, re.DOTALL
    ):
        fields = dict(interfaces[parent]) if parent else {}
        fields.update(re.findall(r"^\s*(\w+): ([^;]+);", body, re.MULTILINE))
        interfaces[name] = fields
    aliases = dict(re.findall(r"export type (\w+) = ([^;]+);", source))
    return interfaces, aliases


INTERFACES, ALIASES = _parse_types(TYPES_SOURCE)


def _problems(value: Any, ts_type: str, path: str) -> list[str]:
    ts_type = ts_type.strip()
    if ts_type in ALIASES:
        return _problems(value, ALIASES[ts_type], path)
    if " | " in ts_type:
        options = [_problems(value, option, path) for option in ts_type.split(" | ")]
        return [] if any(not found for found in options) else [f"{path}: {value!r} is not {ts_type}"]
    if ts_type.endswith("[]"):
        if not isinstance(value, list):
            return [f"{path}: expected an array, got {value!r}"]
        return [p for i, item in enumerate(value) for p in _problems(item, ts_type[:-2], f"{path}[{i}]")]
    if ts_type in INTERFACES:
        if not isinstance(value, dict):
            return [f"{path}: expected {ts_type}, got {value!r}"]
        fields = INTERFACES[ts_type]
        found = [f"{path}.{k}: not in the frontend type {ts_type}" for k in value.keys() - fields.keys()]
        found += [f"{path}.{k}: missing from the response" for k in fields.keys() - value.keys()]
        for key in fields.keys() & value.keys():
            found += _problems(value[key], fields[key], f"{path}.{key}")
        return found
    if ts_type.startswith('"'):
        return [] if value == ts_type.strip('"') else [f"{path}: {value!r} is not {ts_type}"]
    checks = {
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if ts_type not in checks:
        raise AssertionError(f"This parser does not understand the type {ts_type!r} at {path}")
    return [] if checks[ts_type](value) else [f"{path}: {value!r} is not {ts_type}"]


def conforms(value: Any, ts_type: str) -> None:
    assert _problems(value, ts_type, ts_type) == []


def _wrapped(path: str) -> tuple[str, str]:
    """The envelope api.ts expects for `path`, e.g. ("snapshots", "Snapshot")."""
    match = re.search(
        r"request<\{ (\w+): (\w+)\[\] \}>\(\"" + re.escape(path) + r"\"\)", API_SOURCE
    )
    assert match, f"api.ts no longer reads {path} the way this test expects"
    return match[1], match[2]


def test_the_parser_read_the_types_it_needs():
    for name in ("PriceTick", "Portfolio", "Position", "TradeResponse", "ChatResponse"):
        assert INTERFACES[name]
    assert set(INTERFACES["ChatResponse"]) == {"message", "trades", "watchlist_changes"}
    assert _problems({"ticker": "A"}, "WatchlistItem", "x") != []
    assert _problems({"ticker": "A", "price": None, "more": 1}, "WatchlistItem", "x") != []
    assert _problems({"ticker": "A", "price": None}, "WatchlistItem", "x") == []


def test_portfolio_empty_and_with_positions(client):
    conforms(client.get("/api/portfolio").json(), "Portfolio")
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    body = client.get("/api/portfolio").json()
    assert body["positions"]
    conforms(body, "Portfolio")


def test_trade_accepts_what_the_ticket_sends(client):
    # TradeBar sends Number("5"), which JSON encodes as the integer 5.
    for quantity in (5, 0.5):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": quantity, "side": "buy"}
        )
        assert response.status_code == 200, response.text
        conforms(response.json(), "TradeResponse")


def test_history_watchlist_and_chat_history_envelopes(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    client.post("/api/chat", json={"message": "add PYPL"})
    client.post("/api/chat", json={"message": "hello"})
    for path in ("/api/portfolio/history", "/api/watchlist", "/api/chat/history"):
        key, item_type = _wrapped(path)
        body = client.get(path).json()
        assert list(body) == [key]
        assert body[key], f"{path} should have data here"
        conforms(body[key], f"{item_type}[]")


def test_snapshot_times_parse_in_the_browser(client):
    """Date.parse needs ISO-8601 with a zone, or the chart silently reads local time."""
    recorded = client.get("/api/portfolio/history").json()["snapshots"][0]["recorded_at"]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|\+00:00)", recorded)


def test_watchlist_add_and_remove(client):
    added = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert added.status_code == 200
    conforms(added.json(), "WatchlistItem")
    assert added.json()["ticker"] == "PYPL"
    # encodeURIComponent leaves the dot in class shares alone.
    assert client.post("/api/watchlist", json={"ticker": "BRK.B"}).status_code == 200
    assert client.delete("/api/watchlist/BRK.B").json() == {"ticker": "BRK.B", "removed": True}


@pytest.mark.parametrize(
    "message",
    ["buy 1 AAPL", "buy 99999 NVDA", "sell 1 NFLX", "add PYPL", "add NOT-A-TICKER", "remove DIS", "hi"],
)
def test_chat_response_for_every_kind_of_turn(client, message):
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200
    conforms(response.json(), "ChatResponse")
    stored = client.get("/api/chat/history").json()["messages"]
    conforms(stored, "StoredChatMessage[]")
    assert stored[-1]["actions"] == {
        "trades": response.json()["trades"],
        "watchlist_changes": response.json()["watchlist_changes"],
    }


def test_stream_payload(client):
    event = read_stream(client)["events"][0]
    assert event
    for tick in event.values():
        conforms(tick, "PriceTick")


@pytest.mark.parametrize(
    "call, status",
    [
        (lambda c: c.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1e7, "side": "buy"}), 400),
        (lambda c: c.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"}), 400),
        (lambda c: c.post("/api/portfolio/trade", json={"ticker": "1!", "quantity": 1, "side": "buy"}), 400),
        (lambda c: c.post("/api/watchlist", json={"ticker": "NOPE-1"}), 400),
        (lambda c: c.delete("/api/watchlist/DIS"), 404),
    ],
)
def test_business_errors_are_a_readable_detail_string(client, call, status):
    """errorMessage() in api.ts shows `detail` as is, so it must be a non-empty string."""
    response = call(client)
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str) and response.json()["detail"]


def test_validation_errors_carry_the_msg_the_frontend_reads(client):
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"][0]["msg"], str)


def test_static_export_is_served_and_cannot_shadow_the_api(tmp_path, monkeypatch, run_app):
    static = tmp_path / "export"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>FinAlly</title>")
    monkeypatch.setenv("STATIC_DIR", str(static))
    with run_app() as client:
        page = client.get("/")
        assert page.status_code == 200 and "FinAlly" in page.text
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/portfolio").json()["cash_balance"] == 10000.0
        unknown = client.get("/api/nope")
        assert unknown.status_code == 404
        assert unknown.headers["content-type"].startswith("application/json")
