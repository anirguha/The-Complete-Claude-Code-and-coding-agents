"""The mock table in TEAM_CONTRACT.md, row by row, through real portfolio execution."""

import pytest

from app.llm.mock import DEFAULT_MESSAGE, mock_reply
from app.llm.service import ChatService


async def test_buy_row_changes_the_portfolio(mock_chat, portfolio):
    response = await mock_chat.handle_message("buy 10 AAPL")

    assert response == {
        "message": "Mock: buying 10 shares of AAPL.",
        "trades": [
            {
                "ticker": "AAPL",
                "side": "buy",
                "quantity": 10,
                "status": "executed",
                "price": 100.0,
                "error": None,
            }
        ],
        "watchlist_changes": [],
    }
    state = portfolio.get_portfolio()
    assert state["cash_balance"] == 9000.0
    assert [p["ticker"] for p in state["positions"]] == ["AAPL"]


async def test_sell_row_changes_the_portfolio(mock_chat, portfolio):
    await portfolio.execute_trade("AAPL", "buy", 10)

    response = await mock_chat.handle_message("sell 4 AAPL")

    assert response["message"] == "Mock: selling 4 shares of AAPL."
    assert response["trades"][0]["status"] == "executed"
    assert response["trades"][0]["side"] == "sell"
    assert portfolio.get_portfolio()["positions"][0]["quantity"] == 6


async def test_add_row_changes_the_watchlist(mock_chat, portfolio):
    response = await mock_chat.handle_message("add PYPL")

    assert response == {
        "message": "Mock: adding PYPL to your watchlist.",
        "trades": [],
        "watchlist_changes": [
            {"ticker": "PYPL", "action": "add", "status": "applied", "error": None}
        ],
    }
    assert "PYPL" in [w["ticker"] for w in portfolio.list_watchlist()]


async def test_remove_row_changes_the_watchlist(mock_chat, portfolio):
    response = await mock_chat.handle_message("remove NFLX")

    assert response == {
        "message": "Mock: removing NFLX from your watchlist.",
        "trades": [],
        "watchlist_changes": [
            {"ticker": "NFLX", "action": "remove", "status": "applied", "error": None}
        ],
    }
    assert "NFLX" not in [w["ticker"] for w in portfolio.list_watchlist()]


async def test_default_row_has_no_actions(mock_chat):
    assert await mock_chat.handle_message("how am I doing?") == {
        "message": "Mock response: I am FinAlly, your AI trading assistant.",
        "trades": [],
        "watchlist_changes": [],
    }


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("BUY 2 aapl", "Mock: buying 2 shares of AAPL."),
        ("  Sell 2 aApL  ", "Mock: selling 2 shares of AAPL."),
        ("ADD pypl", "Mock: adding PYPL to your watchlist."),
        ("ReMoVe pypl", "Mock: removing PYPL from your watchlist."),
        ("buy   2 \t AAPL", "Mock: buying 2 shares of AAPL."),
    ],
)
def test_matching_is_case_insensitive_on_the_trimmed_message(text, message):
    assert mock_reply(text).message == message


@pytest.mark.parametrize(
    ("text", "quantity"), [("buy 2.5 AAPL", 2.5), ("buy .5 AAPL", 0.5), ("sell 0.0001 AAPL", 0.0001)]
)
def test_quantity_may_be_fractional(text, quantity):
    assert mock_reply(text).trades[0]["quantity"] == quantity


async def test_a_fractional_mock_buy_executes(mock_chat, portfolio):
    response = await mock_chat.handle_message("buy 2.5 AAPL")

    assert response["message"] == "Mock: buying 2.5 shares of AAPL."
    assert response["trades"][0]["quantity"] == 2.5
    assert portfolio.get_portfolio()["positions"][0]["quantity"] == 2.5


@pytest.mark.parametrize(
    "text",
    [
        "buy",
        "buy AAPL",
        "buy 10",
        "buy ten AAPL",
        "buy -5 AAPL",
        "buy 1e3 AAPL",
        "buy 5. AAPL",
        "buy 10 AAPL now",
        "please buy 10 AAPL",
        "buy 10 shares of AAPL",
        "sell AAPL",
        "add",
        "add AAPL please",
        "please add AAPL",
        "remove",
        "remove AAPL now",
        "buying 10 AAPL",
        "adds AAPL",
    ],
)
async def test_near_misses_fall_through_to_the_default(mock_chat, text):
    response = await mock_chat.handle_message(text)

    assert response["message"] == DEFAULT_MESSAGE
    assert response["trades"] == []
    assert response["watchlist_changes"] == []


async def test_failed_mock_actions_are_reported_in_the_action(mock_chat):
    sell = await mock_chat.handle_message("sell 5 AAPL")
    assert sell["message"] == "Mock: selling 5 shares of AAPL."
    assert sell["trades"][0]["status"] == "failed"
    assert sell["trades"][0]["price"] is None
    assert "Insufficient shares" in sell["trades"][0]["error"]

    remove = await mock_chat.handle_message("remove ZZZZ")
    assert remove["watchlist_changes"][0]["status"] == "failed"
    assert "not on the watchlist" in remove["watchlist_changes"][0]["error"]

    add = await mock_chat.handle_message("add NOT-A-TICKER")
    assert add["watchlist_changes"][0]["status"] == "failed"


async def test_an_absurdly_large_quantity_fails_cleanly(mock_chat):
    response = await mock_chat.handle_message(f"buy {'9' * 400} AAPL")

    assert response["trades"][0]["status"] == "failed"
    assert response["trades"][0]["quantity"] == 0


@pytest.mark.parametrize("flag", ["true", "TRUE", "True", " true "])
async def test_the_flag_is_case_insensitive_and_needs_no_key_or_network(db, portfolio, flag):
    chat = ChatService(db, portfolio, environ={"LLM_MOCK": flag})

    assert (await chat.handle_message("hello"))["message"] == DEFAULT_MESSAGE
