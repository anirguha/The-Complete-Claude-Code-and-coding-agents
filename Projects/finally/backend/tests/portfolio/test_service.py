import asyncio

import pytest

from app import db as repo
from app.market import InvalidTickerError, MarketDataUnavailableError
from app.portfolio import NotFoundError, PortfolioService, ServiceError, UnavailableError


def read(db, function, *args):
    with db.connection() as conn:
        return function(conn, *args)


def watchlist(db) -> list[str]:
    return read(db, repo.list_watchlist)


def assert_nothing_changed(db, snapshots_before: int = 0) -> None:
    assert read(db, repo.get_cash) == 10000.0
    assert read(db, repo.list_positions) == []
    assert read(db, repo.list_trades) == []
    assert len(read(db, repo.list_snapshots)) == snapshots_before


class TestBuy:
    async def test_returns_trade_and_updates_cash_position_and_log(self, service, source, db):
        source.set_price("AAPL", 190.25)
        trade = await service.execute_trade("AAPL", "buy", 10)
        assert set(trade) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
        assert (trade["ticker"], trade["side"], trade["quantity"], trade["price"]) == (
            "AAPL",
            "buy",
            10.0,
            190.25,
        )
        assert read(db, repo.get_cash) == 8097.5
        position = read(db, repo.get_position, "AAPL")
        assert (position["quantity"], position["avg_cost"]) == (10.0, 190.25)
        assert [t["id"] for t in read(db, repo.list_trades)] == [trade["id"]]

    async def test_ticker_is_normalized(self, service, db):
        trade = await service.execute_trade("  aapl ", "buy", 1)
        assert trade["ticker"] == "AAPL"
        assert read(db, repo.get_position, "AAPL") is not None

    async def test_weighted_average_cost(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        source.set_price("AAPL", 130.0)
        await service.execute_trade("AAPL", "buy", 5)
        position = read(db, repo.get_position, "AAPL")
        assert (position["quantity"], position["avg_cost"]) == (15.0, 110.0)

    async def test_average_cost_rounds_to_four_decimals(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 1)
        source.set_price("AAPL", 100.01)
        await service.execute_trade("AAPL", "buy", 2)
        assert read(db, repo.get_position, "AAPL")["avg_cost"] == 100.0067

    async def test_exactly_all_cash_is_allowed(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 100)
        assert read(db, repo.get_cash) == 0.0

    async def test_insufficient_cash(self, service, source, db):
        source.set_price("AAPL", 100.0)
        with pytest.raises(ServiceError, match="Insufficient cash"):
            await service.execute_trade("AAPL", "buy", 100.01)
        assert_nothing_changed(db)

    async def test_buy_too_small_to_cost_a_cent_is_rejected(self, service, source, db):
        source.set_price("AAPL", 1.0)
        with pytest.raises(ServiceError, match="below one cent"):
            await service.execute_trade("AAPL", "buy", 0.0001)
        assert_nothing_changed(db)


class TestSell:
    async def test_partial_sell_keeps_avg_cost(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        source.set_price("AAPL", 150.0)
        await service.execute_trade("AAPL", "sell", 4)
        position = read(db, repo.get_position, "AAPL")
        assert (position["quantity"], position["avg_cost"]) == (6.0, 100.0)
        assert read(db, repo.get_cash) == 9600.0

    async def test_sell_at_a_loss(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        source.set_price("AAPL", 80.0)
        trade = await service.execute_trade("AAPL", "sell", 10)
        assert trade["price"] == 80.0
        assert read(db, repo.get_cash) == 9800.0
        assert service.get_portfolio()["total_value"] == 9800.0

    async def test_closing_deletes_the_row(self, service, source, db):
        await service.execute_trade("AAPL", "buy", 1.2346)
        await service.execute_trade("AAPL", "sell", 1.2346)
        assert read(db, repo.get_position, "AAPL") is None
        assert service.get_portfolio()["positions"] == []

    async def test_float_residue_closes_the_position(self, service, db):
        for _ in range(3):
            await service.execute_trade("AAPL", "buy", 0.1)
        await service.execute_trade("AAPL", "sell", 0.3)
        assert read(db, repo.get_position, "AAPL") is None

    async def test_selling_more_than_owned(self, service, db):
        await service.execute_trade("AAPL", "buy", 5)
        cash = read(db, repo.get_cash)
        with pytest.raises(ServiceError, match="Insufficient shares"):
            await service.execute_trade("AAPL", "sell", 5.0001)
        assert read(db, repo.get_position, "AAPL")["quantity"] == 5.0
        assert read(db, repo.get_cash) == cash
        assert len(read(db, repo.list_trades)) == 1

    async def test_selling_with_no_position(self, service, db):
        with pytest.raises(ServiceError, match="Insufficient shares"):
            await service.execute_trade("AAPL", "sell", 1)
        assert_nothing_changed(db)


class TestValidation:
    @pytest.mark.parametrize(
        "quantity", [0, -1, -0.5, float("nan"), float("inf"), "10", None, True]
    )
    async def test_bad_quantity(self, service, db, quantity):
        with pytest.raises(ServiceError, match="greater than 0"):
            await service.execute_trade("AAPL", "buy", quantity)
        assert_nothing_changed(db)

    async def test_quantity_that_rounds_to_zero(self, service, db):
        with pytest.raises(ServiceError, match="too small"):
            await service.execute_trade("AAPL", "buy", 0.00004)
        assert_nothing_changed(db)

    async def test_over_precise_quantity_is_rounded(self, service, source, db):
        source.set_price("AAPL", 100.0)
        trade = await service.execute_trade("AAPL", "buy", 1.23456)
        assert trade["quantity"] == 1.2346
        assert read(db, repo.get_position, "AAPL")["quantity"] == 1.2346
        assert read(db, repo.get_cash) == 9876.54

    @pytest.mark.parametrize("side", ["hold", "BUY", ""])
    async def test_bad_side(self, service, db, side):
        with pytest.raises(ServiceError, match="Invalid side"):
            await service.execute_trade("AAPL", side, 1)
        assert_nothing_changed(db)

    @pytest.mark.parametrize("ticker", ["", "123", "TOOLONG", "A B"])
    async def test_bad_ticker(self, service, db, ticker):
        with pytest.raises(ServiceError, match="Invalid ticker"):
            await service.execute_trade(ticker, "buy", 1)
        assert_nothing_changed(db)
        assert "A B" not in watchlist(db)

    async def test_no_price_available(self, service, source, db):
        source.default_price = None
        with pytest.raises(ServiceError, match="No price available for ZZZZ"):
            await service.execute_trade("zzzz", "buy", 1)
        assert_nothing_changed(db)
        assert "ZZZZ" not in source.get_tickers()


class TestPortfolioValuation:
    async def test_fresh_portfolio(self, service):
        assert service.get_portfolio() == {
            "cash_balance": 10000.0,
            "total_value": 10000.0,
            "positions_value": 0,
            "unrealized_pnl": 0,
            "positions": [],
        }

    async def test_pnl_math(self, service, source):
        source.set_price("AAPL", 100.0)
        source.set_price("MSFT", 200.0)
        await service.execute_trade("AAPL", "buy", 10)
        await service.execute_trade("MSFT", "buy", 5)
        source.set_price("AAPL", 112.5)
        source.set_price("MSFT", 175.0)

        portfolio = service.get_portfolio()
        assert portfolio["cash_balance"] == 8000.0
        assert portfolio["positions_value"] == 2000.0
        assert portfolio["total_value"] == 10000.0
        assert portfolio["unrealized_pnl"] == 0.0
        assert portfolio["positions"] == [
            {
                "ticker": "AAPL",
                "quantity": 10.0,
                "avg_cost": 100.0,
                "current_price": 112.5,
                "market_value": 1125.0,
                "unrealized_pnl": 125.0,
                "pnl_percent": 12.5,
                "weight": 0.5625,
            },
            {
                "ticker": "MSFT",
                "quantity": 5.0,
                "avg_cost": 200.0,
                "current_price": 175.0,
                "market_value": 875.0,
                "unrealized_pnl": -125.0,
                "pnl_percent": -12.5,
                "weight": 0.4375,
            },
        ]

    async def test_current_price_falls_back_to_avg_cost(self, service, source, cache):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        cache.remove("AAPL")
        row = service.get_portfolio()["positions"][0]
        assert row["current_price"] == 100.0
        assert row["unrealized_pnl"] == 0.0


class TestSnapshots:
    async def test_trade_records_a_snapshot_at_the_new_value(self, service, source, db):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        history = service.get_history()
        assert len(history) == 1
        assert history[0]["total_value"] == 10000.0
        assert set(history[0]) == {"total_value", "recorded_at"}

    async def test_record_snapshot_uses_live_prices(self, service, source):
        source.set_price("AAPL", 100.0)
        await service.execute_trade("AAPL", "buy", 10)
        source.set_price("AAPL", 110.0)
        assert service.record_snapshot()["total_value"] == 10100.0

    async def test_history_is_limited_and_oldest_first(self, service):
        for _ in range(5):
            service.record_snapshot()
        everything = service.get_history()
        latest = service.get_history(limit=2)
        assert len(latest) == 2
        assert latest == everything[-2:]
        assert [s["recorded_at"] for s in everything] == sorted(
            s["recorded_at"] for s in everything
        )


class TestWatchlist:
    async def test_list_has_prices(self, service, source, db):
        source.set_price("AAPL", 190.0)
        rows = service.list_watchlist()
        assert [r["ticker"] for r in rows] == watchlist(db)
        assert {"ticker": "AAPL", "price": 190.0} in rows

    async def test_add_normalizes_and_starts_feed(self, service, source, db):
        result = await service.add_watchlist(" pypl ")
        assert result == {"ticker": "PYPL", "price": 100.0}
        assert "PYPL" in watchlist(db)
        assert "PYPL" in source.get_tickers()

    async def test_add_is_idempotent(self, service, db):
        first = await service.add_watchlist("PYPL")
        second = await service.add_watchlist("PYPL")
        assert first == second
        assert watchlist(db).count("PYPL") == 1

    async def test_add_without_a_price_yet(self, service, source):
        source.default_price = None
        assert await service.add_watchlist("PYPL") == {"ticker": "PYPL", "price": None}

    async def test_add_malformed_ticker(self, service, db):
        with pytest.raises(ServiceError, match="Invalid ticker"):
            await service.add_watchlist("123")
        assert "123" not in watchlist(db)

    async def test_add_unknown_to_source_changes_nothing(self, service, source, db):
        source.add_errors["ZZZZ"] = InvalidTickerError("Unknown ticker: ZZZZ")
        with pytest.raises(ServiceError, match="Unknown ticker") as caught:
            await service.add_watchlist("ZZZZ")
        assert not isinstance(caught.value, (NotFoundError, UnavailableError))
        assert "ZZZZ" not in watchlist(db)

    async def test_add_during_source_outage(self, service, source, db):
        source.add_errors["PYPL"] = MarketDataUnavailableError("down")
        with pytest.raises(UnavailableError, match="down"):
            await service.add_watchlist("PYPL")
        assert "PYPL" not in watchlist(db)

    async def test_database_failure_on_add_leaves_no_stray_feed(
        self, service, source, db, monkeypatch
    ):
        def fail(*_, **__):
            raise RuntimeError("disk full")

        monkeypatch.setattr(repo, "add_watchlist", fail)
        with pytest.raises(RuntimeError, match="disk full"):
            await service.add_watchlist("PYPL")
        assert "PYPL" not in source.get_tickers()

    async def test_remove(self, service, source, cache, db):
        assert await service.remove_watchlist("aapl") == {"ticker": "AAPL", "removed": True}
        assert "AAPL" not in watchlist(db)
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None

    @pytest.mark.parametrize("ticker", ["ZZZZ", "123"])
    async def test_remove_absent(self, service, ticker):
        with pytest.raises(NotFoundError, match="not on the watchlist"):
            await service.remove_watchlist(ticker)


class TestTrackedTickers:
    """Each transition of: tracked = watchlist + open positions."""

    async def test_union_of_watchlist_and_positions(self, service, db):
        await service.execute_trade("PYPL", "buy", 1)
        await service.remove_watchlist("PYPL")
        with db.connection() as conn:
            assert set(service._tracked(conn)) == {*repo.list_watchlist(conn), "PYPL"}
        assert "PYPL" in service.tracked_tickers()

    async def test_removing_a_held_ticker_keeps_its_feed_and_price(self, service, source, cache, db):
        source.set_price("AAPL", 123.0)
        await service.execute_trade("AAPL", "buy", 1)
        await service.remove_watchlist("AAPL")
        assert "AAPL" not in watchlist(db)
        assert "AAPL" in source.get_tickers()
        assert cache.get_price("AAPL") == 123.0
        assert service.get_portfolio()["positions"][0]["current_price"] == 123.0

    async def test_closing_an_unwatched_position_stops_its_feed(self, service, source, cache, db):
        await service.execute_trade("AAPL", "buy", 1)
        await service.remove_watchlist("AAPL")
        await service.execute_trade("AAPL", "sell", 1)
        assert "AAPL" not in source.get_tickers()
        assert cache.get("AAPL") is None
        assert "AAPL" not in watchlist(db)

    async def test_partly_selling_an_unwatched_position_keeps_it_unwatched(
        self, service, source, db
    ):
        await service.execute_trade("AAPL", "buy", 2)
        await service.remove_watchlist("AAPL")
        await service.execute_trade("AAPL", "sell", 1)
        assert "AAPL" in source.get_tickers()
        assert "AAPL" not in watchlist(db)

    async def test_closing_a_watched_position_keeps_its_feed(self, service, source, db):
        await service.execute_trade("AAPL", "buy", 1)
        await service.execute_trade("AAPL", "sell", 1)
        assert "AAPL" in source.get_tickers()
        assert "AAPL" in watchlist(db)

    async def test_buying_an_unwatched_ticker_adds_it(self, service, source, db):
        assert "PYPL" not in source.get_tickers()
        trade = await service.execute_trade("PYPL", "buy", 1)
        assert trade["price"] == 100.0
        assert "PYPL" in source.get_tickers()
        assert "PYPL" in watchlist(db)

    async def test_buying_a_held_unwatched_ticker_adds_it_back(self, service, db):
        await service.execute_trade("AAPL", "buy", 1)
        await service.remove_watchlist("AAPL")
        await service.execute_trade("AAPL", "buy", 1)
        assert "AAPL" in watchlist(db)

    async def test_failed_buy_of_unwatched_leaves_no_feed(self, service, source, cache, db):
        with pytest.raises(ServiceError, match="Insufficient cash"):
            await service.execute_trade("PYPL", "buy", 1000)
        assert "PYPL" not in source.get_tickers()
        assert cache.get("PYPL") is None
        assert "PYPL" not in watchlist(db)

    async def test_failed_sell_of_unwatched_leaves_no_feed(self, service, source, db):
        with pytest.raises(ServiceError, match="Insufficient shares"):
            await service.execute_trade("PYPL", "sell", 1)
        assert "PYPL" not in source.get_tickers()
        assert "PYPL" not in watchlist(db)

    async def test_failed_trade_on_a_watched_ticker_keeps_its_feed(self, service, source):
        with pytest.raises(ServiceError):
            await service.execute_trade("AAPL", "buy", 1000)
        assert "AAPL" in source.get_tickers()

    async def test_no_price_on_a_watched_ticker_keeps_its_feed(self, service, source, cache):
        cache.remove("AAPL")
        with pytest.raises(ServiceError, match="No price available for AAPL"):
            await service.execute_trade("AAPL", "buy", 1)
        assert "AAPL" in source.get_tickers()

    async def test_trade_with_source_outage(self, service, source, db):
        source.add_errors["PYPL"] = MarketDataUnavailableError("down")
        with pytest.raises(UnavailableError, match="down"):
            await service.execute_trade("PYPL", "buy", 1)
        assert_nothing_changed(db)
        assert "PYPL" not in source.get_tickers()

    async def test_trade_of_ticker_unknown_to_source(self, service, source, db):
        source.add_errors["ZZZZ"] = InvalidTickerError("Unknown ticker: ZZZZ")
        with pytest.raises(ServiceError, match="Unknown ticker"):
            await service.execute_trade("ZZZZ", "buy", 1)
        assert_nothing_changed(db)

    async def test_failed_feed_removal_does_not_fail_the_request_and_heals(
        self, service, source, db
    ):
        source.remove_errors.append(RuntimeError("source hiccup"))
        assert (await service.remove_watchlist("AAPL"))["removed"] is True
        assert "AAPL" not in watchlist(db)
        assert "AAPL" in source.get_tickers()  # the stray feed, until the next change

        await service.remove_watchlist("MSFT")
        assert "AAPL" not in source.get_tickers()
        assert "MSFT" not in source.get_tickers()

    async def test_feed_removal_failure_does_not_hide_the_trade_error(self, service, source):
        source.remove_errors.append(RuntimeError("source hiccup"))
        with pytest.raises(ServiceError, match="Insufficient cash"):
            await service.execute_trade("PYPL", "buy", 1000)


class TestAtomicity:
    @pytest.mark.parametrize(
        "failing", ["insert_snapshot", "insert_trade", "add_watchlist", "upsert_position"]
    )
    async def test_failure_at_any_step_rolls_everything_back(
        self, service, source, cache, db, monkeypatch, failing
    ):
        def fail(*_, **__):
            raise RuntimeError("boom")

        monkeypatch.setattr(repo, failing, fail)
        with pytest.raises(RuntimeError, match="boom"):
            await service.execute_trade("PYPL", "buy", 1)
        monkeypatch.undo()

        assert_nothing_changed(db)
        assert "PYPL" not in watchlist(db)
        assert "PYPL" not in source.get_tickers()
        assert cache.get("PYPL") is None

    async def test_failed_sell_rolls_back(self, service, db, monkeypatch):
        await service.execute_trade("AAPL", "buy", 2)
        before = read(db, repo.get_cash), read(db, repo.get_position, "AAPL")["quantity"]

        def fail(*_, **__):
            raise RuntimeError("boom")

        monkeypatch.setattr(repo, "insert_snapshot", fail)
        with pytest.raises(RuntimeError, match="boom"):
            await service.execute_trade("AAPL", "sell", 2)
        monkeypatch.undo()

        assert (read(db, repo.get_cash), read(db, repo.get_position, "AAPL")["quantity"]) == before
        assert len(read(db, repo.list_trades)) == 1


class TestConcurrency:
    async def test_concurrent_buys_cannot_overdraw(self, service, source, db):
        source.set_price("AAPL", 100.0)
        results = await asyncio.gather(
            *(service.execute_trade("AAPL", "buy", 30) for _ in range(10)),
            return_exceptions=True,
        )
        filled = [r for r in results if isinstance(r, dict)]
        rejected = [r for r in results if isinstance(r, ServiceError)]
        assert (len(filled), len(rejected)) == (3, 7)
        assert read(db, repo.get_cash) == 1000.0
        assert read(db, repo.get_position, "AAPL")["quantity"] == 90.0

    async def test_balance_is_read_inside_the_transaction(self, db, cache, source):
        # Two services do not share a lock, so only the database can protect the cash.
        services = [PortfolioService(db, cache, source) for _ in range(4)]
        source.set_price("AAPL", 100.0)
        source.tickers.add("AAPL")
        results = await asyncio.gather(
            *(s.execute_trade("AAPL", "buy", 60) for s in services),
            return_exceptions=True,
        )
        assert sum(isinstance(r, dict) for r in results) == 1
        assert sum(isinstance(r, ServiceError) for r in results) == 3
        assert read(db, repo.get_cash) == 4000.0

    async def test_concurrent_sells_cannot_oversell(self, service, source, db):
        await service.execute_trade("AAPL", "buy", 10)
        results = await asyncio.gather(
            *(service.execute_trade("AAPL", "sell", 4) for _ in range(5)),
            return_exceptions=True,
        )
        assert sum(isinstance(r, dict) for r in results) == 2
        assert read(db, repo.get_position, "AAPL")["quantity"] == 2.0

    async def test_failing_trade_cannot_stop_a_concurrent_trades_feed(self, service, source, db):
        results = await asyncio.gather(
            service.execute_trade("PYPL", "buy", 1000),
            service.execute_trade("PYPL", "buy", 1),
            return_exceptions=True,
        )
        assert isinstance(results[0], ServiceError)
        assert isinstance(results[1], dict)
        assert "PYPL" in source.get_tickers()
        assert "PYPL" in watchlist(db)

    async def test_event_loop_runs_during_a_trade(self, service, db):
        """The transaction runs on a worker thread, so SSE keeps flowing."""
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0)

        task = asyncio.create_task(ticker())
        await service.execute_trade("AAPL", "buy", 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert ticks > 1


def test_errors_carry_their_message():
    error = UnavailableError("down")
    assert error.message == "down"
    assert isinstance(error, ServiceError) and isinstance(error, ValueError)
    assert isinstance(NotFoundError("x"), ServiceError)
