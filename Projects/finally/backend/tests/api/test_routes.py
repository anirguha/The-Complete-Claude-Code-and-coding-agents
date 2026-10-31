import pytest

from app.market import InvalidTickerError, MarketDataUnavailableError

PORTFOLIO_KEYS = {"cash_balance", "total_value", "positions_value", "unrealized_pnl", "positions"}
POSITION_KEYS = {
    "ticker",
    "quantity",
    "avg_cost",
    "current_price",
    "market_value",
    "unrealized_pnl",
    "pnl_percent",
    "weight",
}
TRADE_KEYS = {"id", "ticker", "side", "quantity", "price", "executed_at"}


def buy(client, ticker="AAPL", quantity=10):
    return client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "quantity": quantity, "side": "buy"}
    )


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "market": {
            "source": "simulator",
            "mode": "simulated",
            "last_success_at": None,
            "last_error": None,
        },
    }


class TestPortfolio:
    def test_fresh(self, client):
        response = client.get("/api/portfolio")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == PORTFOLIO_KEYS
        assert body["cash_balance"] == 10000.0
        assert body["total_value"] == 10000.0
        assert body["positions"] == []

    def test_with_position(self, client, source):
        source.set_price("AAPL", 100.0)
        buy(client)
        source.set_price("AAPL", 110.0)
        body = client.get("/api/portfolio").json()
        assert body["cash_balance"] == 9000.0
        assert body["total_value"] == 10100.0
        assert body["unrealized_pnl"] == 100.0
        row = body["positions"][0]
        assert set(row) == POSITION_KEYS
        assert row["pnl_percent"] == 10.0
        assert row["weight"] == 1.0


class TestTrade:
    def test_buy(self, client, source):
        source.set_price("AAPL", 100.0)
        response = buy(client, "aapl", 2.5)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"trade", "portfolio"}
        assert set(body["trade"]) == TRADE_KEYS
        assert body["trade"]["ticker"] == "AAPL"
        assert body["trade"]["quantity"] == 2.5
        assert body["trade"]["price"] == 100.0
        assert set(body["portfolio"]) == PORTFOLIO_KEYS
        assert body["portfolio"]["cash_balance"] == 9750.0

    def test_sell_closes_position(self, client):
        buy(client)
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"}
        )
        assert response.status_code == 200
        assert response.json()["trade"]["side"] == "sell"
        assert response.json()["portfolio"]["positions"] == []

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            ({"ticker": "AAPL", "quantity": 1000, "side": "buy"}, "Insufficient cash"),
            ({"ticker": "AAPL", "quantity": 1, "side": "sell"}, "Insufficient shares"),
            ({"ticker": "AAPL", "quantity": 0, "side": "buy"}, "greater than 0"),
            ({"ticker": "AAPL", "quantity": -1, "side": "buy"}, "greater than 0"),
            ({"ticker": "AAPL", "quantity": 0.00001, "side": "buy"}, "too small"),
            ({"ticker": "AAPL", "quantity": 1, "side": "short"}, "Invalid side"),
            ({"ticker": "123", "quantity": 1, "side": "buy"}, "Invalid ticker"),
        ],
    )
    def test_business_rule_failures_are_400(self, client, body, message):
        response = client.post("/api/portfolio/trade", json=body)
        assert response.status_code == 400
        assert message in response.json()["detail"]

    def test_no_price_is_400(self, client, source):
        source.default_price = None
        response = buy(client, "ZZZZ", 1)
        assert response.status_code == 400
        assert response.json() == {"detail": "No price available for ZZZZ"}

    def test_source_outage_is_503(self, client, source):
        source.add_errors["PYPL"] = MarketDataUnavailableError("down")
        response = buy(client, "PYPL", 1)
        assert response.status_code == 503
        assert response.json() == {"detail": "down"}

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"ticker": "AAPL", "side": "buy"},
            {"ticker": "AAPL", "quantity": "ten", "side": "buy"},
            {"ticker": "AAPL", "quantity": "10", "side": "buy"},
            {"ticker": "AAPL", "quantity": True, "side": "buy"},
            {"ticker": 5, "quantity": 1, "side": "buy"},
        ],
    )
    def test_malformed_bodies_are_422(self, client, body):
        assert client.post("/api/portfolio/trade", json=body).status_code == 422

    def test_non_finite_quantity_is_rejected(self, client):
        response = client.post(
            "/api/portfolio/trade",
            content='{"ticker": "AAPL", "quantity": NaN, "side": "buy"}',
            headers={"content-type": "application/json"},
        )
        assert response.status_code in (400, 422)
        assert client.get("/api/portfolio").json()["cash_balance"] == 10000.0


class TestHistory:
    def test_shape_and_first_snapshot(self, client):
        response = client.get("/api/portfolio/history")
        assert response.status_code == 200
        snapshots = response.json()["snapshots"]
        assert len(snapshots) == 1
        assert set(snapshots[0]) == {"total_value", "recorded_at"}
        assert snapshots[0]["total_value"] == 10000.0

    def test_trade_adds_a_point(self, client):
        buy(client)
        assert len(client.get("/api/portfolio/history").json()["snapshots"]) == 2

    def test_capped_at_500(self, client):
        portfolio = client.app.state.portfolio
        for _ in range(505):
            portfolio.record_snapshot()
        assert len(client.get("/api/portfolio/history").json()["snapshots"]) == 500


class TestWatchlist:
    def test_get(self, client, source):
        source.set_price("AAPL", 190.0)
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        rows = response.json()["watchlist"]
        assert len(rows) == 10
        assert rows[0] == {"ticker": "AAPL", "price": 190.0}

    def test_add_is_idempotent(self, client):
        for _ in range(2):
            response = client.post("/api/watchlist", json={"ticker": "pypl"})
            assert response.status_code == 200
            assert response.json() == {"ticker": "PYPL", "price": 100.0}
        tickers = [r["ticker"] for r in client.get("/api/watchlist").json()["watchlist"]]
        assert tickers.count("PYPL") == 1

    def test_add_invalid_is_400(self, client):
        response = client.post("/api/watchlist", json={"ticker": "not valid"})
        assert response.status_code == 400
        assert "Invalid ticker" in response.json()["detail"]

    def test_add_unknown_to_source_is_400(self, client, source):
        source.add_errors["ZZZZ"] = InvalidTickerError("Unknown ticker: ZZZZ")
        assert client.post("/api/watchlist", json={"ticker": "ZZZZ"}).status_code == 400

    def test_add_during_outage_is_503(self, client, source):
        source.add_errors["PYPL"] = MarketDataUnavailableError("down")
        assert client.post("/api/watchlist", json={"ticker": "PYPL"}).status_code == 503

    def test_add_malformed_body_is_422(self, client):
        assert client.post("/api/watchlist", json={}).status_code == 422

    def test_remove(self, client):
        response = client.delete("/api/watchlist/aapl")
        assert response.status_code == 200
        assert response.json() == {"ticker": "AAPL", "removed": True}
        tickers = [r["ticker"] for r in client.get("/api/watchlist").json()["watchlist"]]
        assert "AAPL" not in tickers

    @pytest.mark.parametrize("ticker", ["ZZZZ", "123"])
    def test_remove_absent_is_404(self, client, ticker):
        response = client.delete(f"/api/watchlist/{ticker}")
        assert response.status_code == 404
        assert "not on the watchlist" in response.json()["detail"]

    def test_class_share_symbol_in_path(self, client):
        assert client.post("/api/watchlist", json={"ticker": "brk.b"}).status_code == 200
        assert client.delete("/api/watchlist/BRK.B").status_code == 200

    def test_held_ticker_keeps_streaming_after_removal(self, client):
        buy(client)
        client.delete("/api/watchlist/AAPL")
        assert "AAPL" in client.app.state.cache.get_all()
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"})
        assert "AAPL" not in client.app.state.cache.get_all()
