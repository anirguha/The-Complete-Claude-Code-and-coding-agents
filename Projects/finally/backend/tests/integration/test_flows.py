"""Flows that cross components, through HTTP, against the real stack."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.llm.schema import ParsedReply

from .conftest import DEFAULT_TICKERS, read_stream, streamed_tickers


def portfolio(client):
    return client.get("/api/portfolio").json()


def watchlist(client):
    return [item["ticker"] for item in client.get("/api/watchlist").json()["watchlist"]]


def history(client):
    return client.get("/api/portfolio/history").json()["snapshots"]


def chat(client, message):
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200, response.text
    return response.json()


def trades_in_db(client):
    from app.db import list_trades

    with client.app.state.db.connection() as conn:
        return list_trades(conn)


def position(client, ticker):
    return next((p for p in portfolio(client)["positions"] if p["ticker"] == ticker), None)


# Fresh start


def test_fresh_start(client):
    assert watchlist(client) == DEFAULT_TICKERS
    state = portfolio(client)
    assert state["cash_balance"] == 10000.0
    assert state["total_value"] == 10000.0
    assert state["positions"] == []
    assert [s["total_value"] for s in history(client)] == [10000.0]
    assert client.get("/api/chat/history").json() == {"messages": []}
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["market"]["source"] == "simulator"
    # Every default ticker is priced straight away, before any tick.
    assert all(i["price"] > 0 for i in client.get("/api/watchlist").json()["watchlist"])


# Chat changes every part of the portfolio


def test_chat_buy_reaches_cash_positions_trades_snapshots_and_history(client):
    before = history(client)

    reply = chat(client, "buy 3 AAPL")

    assert reply["message"] == "Mock: buying 3 shares of AAPL."
    assert reply["watchlist_changes"] == []
    assert len(reply["trades"]) == 1
    trade = reply["trades"][0]
    assert (trade["ticker"], trade["side"], trade["quantity"]) == ("AAPL", "buy", 3.0)
    assert trade["status"] == "executed" and trade["error"] is None
    price = trade["price"]
    assert price > 0

    state = portfolio(client)
    assert state["cash_balance"] == pytest.approx(10000 - round(3 * price, 2), abs=0.001)
    held = position(client, "AAPL")
    assert held["quantity"] == 3.0
    assert held["avg_cost"] == price

    logged = trades_in_db(client)
    assert [(t["ticker"], t["side"], t["quantity"], t["price"]) for t in logged] == [
        ("AAPL", "buy", 3.0, price)
    ]

    after = history(client)
    assert len(after) == len(before) + 1
    assert after[-1]["total_value"] == pytest.approx(10000, rel=0.01)

    stored = client.get("/api/chat/history").json()["messages"]
    assert [(m["role"], m["content"]) for m in stored] == [
        ("user", "buy 3 AAPL"),
        ("assistant", reply["message"]),
    ]
    assert stored[0]["actions"] is None
    assert stored[1]["actions"] == {"trades": reply["trades"], "watchlist_changes": []}


def test_chat_sell_and_watchlist_commands(client):
    chat(client, "buy 2 MSFT")
    reply = chat(client, "sell 2 MSFT")
    assert reply["trades"][0]["status"] == "executed"
    assert position(client, "MSFT") is None

    assert chat(client, "add PYPL")["watchlist_changes"] == [
        {"ticker": "PYPL", "action": "add", "status": "applied", "error": None}
    ]
    assert "PYPL" in watchlist(client)
    assert "PYPL" in streamed_tickers(client)

    assert chat(client, "remove PYPL")["watchlist_changes"][0]["status"] == "applied"
    assert "PYPL" not in watchlist(client)
    assert "PYPL" not in streamed_tickers(client)


def test_chat_buy_of_an_unwatched_ticker_adds_it_and_starts_its_feed(client):
    reply = chat(client, "buy 1 PYPL")
    assert reply["trades"][0]["status"] == "executed"
    assert "PYPL" in watchlist(client)
    assert "PYPL" in streamed_tickers(client)


def test_failed_chat_trade_changes_nothing_and_is_reported(client):
    reply = chat(client, "buy 100000 NVDA")
    trade = reply["trades"][0]
    assert trade["status"] == "failed"
    assert trade["price"] is None
    assert "Insufficient cash" in trade["error"]
    state = portfolio(client)
    assert state["cash_balance"] == 10000.0 and state["positions"] == []
    assert trades_in_db(client) == []
    # Failing on a ticker nobody tracks must not leave a feed behind.
    assert chat(client, "buy 100000000 ZZZZ")["trades"][0]["status"] == "failed"
    assert "ZZZZ" not in streamed_tickers(client)
    assert "ZZZZ" not in watchlist(client)


def test_a_failed_action_does_not_block_the_ones_after_it(client, monkeypatch):
    """Mock mode gives one action per message, so only the reply is scripted here."""
    scripted = ParsedReply(
        "Several things at once.",
        trades=[
            {"ticker": "AAPL", "side": "buy", "quantity": 1_000_000},  # too expensive
            {"ticker": "MSFT", "side": "buy", "quantity": 1},
            {"ticker": "NOT-A-TICKER", "side": "buy", "quantity": 1},  # invalid
            {"ticker": "TSLA", "side": "sell", "quantity": 1},  # not held
            {"ticker": "JPM", "side": "buy", "quantity": 2},
        ],
        watchlist_changes=[
            {"ticker": "ZZZZZZZZ", "action": "add"},  # invalid
            {"ticker": "PYPL", "action": "add"},
            {"ticker": "DIS", "action": "remove"},  # not on the list
            {"ticker": "NFLX", "action": "remove"},
        ],
    )
    monkeypatch.setattr("app.llm.service.mock_reply", lambda _text: scripted)

    reply = chat(client, "do several things")

    assert [t["status"] for t in reply["trades"]] == [
        "failed",
        "executed",
        "failed",
        "failed",
        "executed",
    ]
    assert [c["status"] for c in reply["watchlist_changes"]] == [
        "failed",
        "applied",
        "failed",
        "applied",
    ]
    for action in reply["trades"] + reply["watchlist_changes"]:
        ok = action["status"] in ("executed", "applied")
        assert (action["error"] is None) == ok

    state = portfolio(client)
    assert sorted(p["ticker"] for p in state["positions"]) == ["JPM", "MSFT"]
    tickers = watchlist(client)
    assert "PYPL" in tickers and "NFLX" not in tickers
    stored = client.get("/api/chat/history").json()["messages"][-1]
    assert stored["actions"]["trades"] == reply["trades"]
    assert stored["actions"]["watchlist_changes"] == reply["watchlist_changes"]


# The tracked ticker rule, seen end to end


def test_removing_a_held_ticker_keeps_its_feed_and_valuation(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    assert client.delete("/api/watchlist/AAPL").status_code == 200

    assert "AAPL" not in watchlist(client)
    assert "AAPL" in streamed_tickers(client)
    # A live price, not the avg_cost fallback: it keeps moving and is still in the cache.
    events = read_stream(client, count=3)["events"]
    assert len({e["AAPL"]["timestamp"] for e in events}) == 3
    assert client.app.state.cache.get_price("AAPL") is not None


def test_removing_an_unheld_ticker_stops_its_feed(client):
    assert "V" in streamed_tickers(client)
    assert client.delete("/api/watchlist/V").status_code == 200
    assert "V" not in streamed_tickers(client)
    assert client.delete("/api/watchlist/V").status_code == 404


def test_closing_an_unwatched_position_stops_its_feed(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2, "side": "buy"})
    client.delete("/api/watchlist/AAPL")

    # A partial sale keeps it going, and selling does not put it back on the list.
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert "AAPL" in streamed_tickers(client)
    assert "AAPL" not in watchlist(client)

    response = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"}
    )
    assert response.status_code == 200
    assert "AAPL" not in streamed_tickers(client)
    assert "AAPL" not in watchlist(client)
    assert position(client, "AAPL") is None
    assert client.app.state.cache.get_price("AAPL") is None


def test_closing_a_watched_position_keeps_its_feed(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert "AAPL" in streamed_tickers(client)
    assert "AAPL" in watchlist(client)


# SSE


def test_stream_contract_and_live_prices(client):
    stream = read_stream(client, count=4)
    assert stream["status"] == 200
    assert stream["headers"]["content-type"].startswith("text/event-stream")
    events = stream["events"]
    assert set(events[0]) == set(DEFAULT_TICKERS)
    for event in events:
        for ticker, update in event.items():
            assert set(update) == {
                "ticker",
                "price",
                "previous_price",
                "timestamp",
                "change",
                "direction",
            }
            assert update["ticker"] == ticker
            assert update["direction"] in ("up", "down", "flat")
            assert update["change"] == pytest.approx(update["price"] - update["previous_price"])
    # Actually moving: ten tickers over several ticks cannot all stay put.
    first, last = events[0], events[-1]
    assert any(first[t]["price"] != last[t]["price"] for t in DEFAULT_TICKERS)
    assert all(last[t]["timestamp"] > first[t]["timestamp"] for t in DEFAULT_TICKERS)


def test_stream_matches_tracked_tickers_through_a_session(client):
    tracked = lambda: set(client.app.state.portfolio.tracked_tickers())  # noqa: E731
    assert streamed_tickers(client) == tracked()
    client.post("/api/watchlist", json={"ticker": "brk.b"})
    assert "BRK.B" in streamed_tickers(client)
    client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 1, "side": "buy"})
    client.delete("/api/watchlist/PYPL")
    client.delete("/api/watchlist/META")
    assert streamed_tickers(client) == tracked()
    assert "META" not in tracked() and "PYPL" in tracked()


# Money


def test_portfolio_totals_agree_with_their_rows(client):
    for ticker, quantity in (("AAPL", 1.5), ("JPM", 2), ("V", 0.25)):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": ticker, "quantity": quantity, "side": "buy"}
        )
        assert response.status_code == 200, response.text
    state = portfolio(client)
    assert sum(p["market_value"] for p in state["positions"]) == pytest.approx(
        state["positions_value"], abs=0.02
    )
    assert state["total_value"] == pytest.approx(
        state["cash_balance"] + state["positions_value"], abs=0.01
    )
    assert sum(p["weight"] for p in state["positions"]) == pytest.approx(1, abs=0.001)
    assert state["unrealized_pnl"] == pytest.approx(
        sum(p["unrealized_pnl"] for p in state["positions"]), abs=0.02
    )


def test_cash_is_conserved_across_buys_and_sells(client):
    for side, quantity in (("buy", 3), ("buy", 1.5), ("sell", 2), ("sell", 2.5)):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "NFLX", "quantity": quantity, "side": side}
        )
        assert response.status_code == 200, response.text
    expected = 10000.0
    for trade in trades_in_db(client):
        cost = round(trade["quantity"] * trade["price"], 2)
        expected += -cost if trade["side"] == "buy" else cost
    assert portfolio(client)["cash_balance"] == pytest.approx(expected, abs=0.001)
    assert position(client, "NFLX") is None


def test_concurrent_buys_never_overspend(client):
    """Each NVDA share costs about $800, so only some of these twenty can fill."""

    def buy(_):
        return client.post(
            "/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 1, "side": "buy"}
        )

    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(buy, range(20)))

    assert {r.status_code for r in responses} == {200, 400}
    filled = [r.json()["trade"] for r in responses if r.status_code == 200]
    cash = portfolio(client)["cash_balance"]
    assert cash >= 0
    assert cash == pytest.approx(10000 - sum(round(t["price"], 2) for t in filled), abs=0.001)
    assert position(client, "NVDA")["quantity"] == len(filled)
    assert len(trades_in_db(client)) == len(filled)


# Snapshots


def test_background_task_records_live_portfolio_value(run_app):
    with run_app(snapshot_seconds=0.1) as client:
        client.post("/api/portfolio/trade", json={"ticker": "TSLA", "quantity": 10, "side": "buy"})
        count = len(history(client))
        read_stream(client, count=3)  # lets a second or so pass on the app's own loop
        later = history(client)
        assert len(later) > count
        assert later[-1]["total_value"] == pytest.approx(10000, rel=0.05)
