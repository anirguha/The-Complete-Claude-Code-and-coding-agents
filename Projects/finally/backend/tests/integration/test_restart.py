"""Stopping the app and starting it again on the same DB_PATH."""

import pytest

from .conftest import DEFAULT_TICKERS, read_stream, streamed_tickers


def streamed_or_empty(client) -> set[str]:
    """With nothing tracked the stream sends no data, so ask the cache behind it."""
    return set(client.app.state.cache.get_all())


def test_everything_survives_a_restart(run_app, db_path):
    with run_app() as client:
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 2.5, "side": "buy"})
        client.post("/api/watchlist", json={"ticker": "PYPL"})
        client.delete("/api/watchlist/NFLX")
        client.post("/api/chat", json={"message": "buy 1 MSFT"})
        before = client.get("/api/portfolio").json()
        chat_before = client.get("/api/chat/history").json()
        watch_before = [w["ticker"] for w in client.get("/api/watchlist").json()["watchlist"]]
        history_before = client.get("/api/portfolio/history").json()["snapshots"]
    assert db_path.exists()

    with run_app() as client:
        after = client.get("/api/portfolio").json()
        assert after["cash_balance"] == before["cash_balance"]
        assert [(p["ticker"], p["quantity"], p["avg_cost"]) for p in after["positions"]] == [
            (p["ticker"], p["quantity"], p["avg_cost"]) for p in before["positions"]
        ]
        assert client.get("/api/chat/history").json() == chat_before
        assert [w["ticker"] for w in client.get("/api/watchlist").json()["watchlist"]] == watch_before
        history_after = client.get("/api/portfolio/history").json()["snapshots"]
        # Restarting does not rewrite or add to the recorded history.
        assert history_after == history_before


def test_restart_does_not_reseed_an_emptied_watchlist(run_app):
    with run_app() as client:
        for ticker in DEFAULT_TICKERS:
            assert client.delete(f"/api/watchlist/{ticker}").status_code == 200
    with run_app() as client:
        assert client.get("/api/watchlist").json() == {"watchlist": []}
        assert streamed_or_empty(client) == set()


def test_restart_does_not_reset_cash(run_app):
    with run_app() as client:
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    with run_app() as client:
        assert client.get("/api/portfolio").json()["cash_balance"] < 10000


def test_restart_keeps_prices_for_held_positions_off_the_watchlist(run_app):
    with run_app() as client:
        client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 2, "side": "buy"})
        client.delete("/api/watchlist/PYPL")
        client.delete("/api/watchlist/V")
        assert "PYPL" in streamed_tickers(client)

    with run_app() as client:
        tickers = streamed_tickers(client)
        assert "PYPL" in tickers  # held
        assert "V" not in tickers  # neither held nor watched
        events = read_stream(client, count=3)["events"]
        assert len({e["PYPL"]["timestamp"] for e in events}) == 3

        held = client.get("/api/portfolio").json()["positions"][0]
        live = client.app.state.cache.get_price("PYPL")
        assert held["ticker"] == "PYPL"
        assert live is not None
        assert held["current_price"] == pytest.approx(live, rel=0.02)

        # Still tradable, and closing it now ends the feed.
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 2, "side": "sell"}
        )
        assert response.status_code == 200, response.text
        assert "PYPL" not in streamed_tickers(client)
