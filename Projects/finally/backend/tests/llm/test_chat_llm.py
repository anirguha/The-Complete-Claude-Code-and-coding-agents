"""The real path with litellm.acompletion replaced: arguments, prompt, parsing, failures."""

import asyncio
import json
import logging

import pytest

from app import db as repo
from app.llm.client import EXTRA_BODY, MODEL
from app.llm.prompt import SYSTEM_PROMPT
from app.llm.schema import AssistantReply, ReplyParseError, parse_reply
from app.llm.service import FAILURE_MESSAGE, MARKET_UNAVAILABLE_MESSAGE, ChatService
from app.market import MarketDataUnavailableError
from tests.llm.conftest import TEST_KEY


def stored(db):
    with db.connection() as conn:
        return repo.list_chat_messages(conn, 100)


# The call


async def test_the_call_follows_the_cerebras_skill(live_chat, fake_llm):
    await live_chat.handle_message("hello")

    assert len(fake_llm.calls) == 1
    call = fake_llm.calls[0]
    assert call["model"] == MODEL == "openrouter/openai/gpt-oss-120b"
    assert call["extra_body"] == EXTRA_BODY == {"provider": {"order": ["cerebras"]}}
    assert call["reasoning_effort"] == "low"
    assert call["response_format"] is AssistantReply
    assert call["timeout"] == 30.0
    assert call["max_retries"] == 0
    assert call["api_key"] == TEST_KEY


async def test_the_key_is_read_at_call_time(db, portfolio, fake_llm):
    environ = {}
    chat = ChatService(db, portfolio, environ=environ)
    environ["OPENROUTER_API_KEY"] = TEST_KEY

    await chat.handle_message("hello")

    assert fake_llm.calls[0]["api_key"] == TEST_KEY


def test_the_requested_schema_is_valid_for_strict_providers():
    import litellm

    schema = litellm.utils.type_to_response_format_param(AssistantReply)["json_schema"]

    assert schema["strict"] is True
    assert set(schema["schema"]["required"]) == {"message", "trades", "watchlist_changes"}
    objects = [schema["schema"], *schema["schema"]["$defs"].values()]
    for definition in objects:
        assert definition["additionalProperties"] is False
        assert set(definition["required"]) == set(definition["properties"])
        assert not any("default" in prop for prop in definition["properties"].values())


# The prompt


async def test_the_system_prompt_has_the_persona_and_the_guidance(live_chat, fake_llm):
    await live_chat.handle_message("hello")

    system = fake_llm.calls[0]["messages"][0]
    assert system["role"] == "system"
    assert "FinAlly, an AI trading assistant" in system["content"]
    assert system["content"].startswith(SYSTEM_PROMPT)
    for phrase in ("risk concentration", "watchlist", "concise", "valid JSON", "Suggest trades"):
        assert phrase in system["content"]


async def test_the_prompt_contains_the_portfolio_context(live_chat, fake_llm, portfolio, source):
    await portfolio.execute_trade("AAPL", "buy", 10)
    source.set_price("AAPL", 110.0)
    source.set_price("TSLA", 222.5)

    await live_chat.handle_message("how am I doing?")

    system = fake_llm.calls[0]["messages"][0]["content"]
    context = json.loads(system.split("Current portfolio context (JSON):\n")[1])
    assert context["portfolio"]["cash_balance"] == 9000.0
    assert context["portfolio"]["total_value"] == 10100.0
    assert context["portfolio"]["unrealized_pnl"] == 100.0
    position = context["portfolio"]["positions"][0]
    assert position["ticker"] == "AAPL"
    assert position["quantity"] == 10
    assert position["unrealized_pnl"] == 100.0
    assert {"ticker": "TSLA", "price": 222.5} in context["watchlist"]


async def test_the_prompt_has_the_last_20_messages_then_the_new_one(db, live_chat, fake_llm):
    with db.connection() as conn:
        for number in range(30):
            repo.insert_chat_message(conn, "user" if number % 2 == 0 else "assistant", f"old {number}")

    await live_chat.handle_message("the new one")

    messages = fake_llm.calls[0]["messages"]
    assert len(messages) == 22  # system, 20 history, new
    assert [m["content"] for m in messages[1:21]] == [f"old {n}" for n in range(10, 30)]
    assert [m["role"] for m in messages[1:3]] == ["user", "assistant"]
    assert messages[-1] == {"role": "user", "content": "the new one"}


async def test_history_tells_the_llm_what_its_actions_did(live_chat, fake_llm):
    fake_llm.reply(
        "On it",
        trades=[
            {"ticker": "AAPL", "side": "buy", "quantity": 2},
            {"ticker": "TSLA", "side": "sell", "quantity": 2},
        ],
        watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
    )
    await live_chat.handle_message("do things")
    fake_llm.reply("ok")

    await live_chat.handle_message("did that work?")

    earlier = fake_llm.calls[1]["messages"][2]
    assert earlier["role"] == "assistant"
    assert earlier["content"].startswith("On it\n[Action results: ")
    assert "buy 2.0 AAPL executed at 100.0" in earlier["content"]
    assert "sell 2.0 TSLA failed: Insufficient shares" in earlier["content"]
    assert "add PYPL applied" in earlier["content"]


# Parsing and execution


async def test_actions_execute_and_the_response_has_the_contract_shape(live_chat, fake_llm, portfolio):
    fake_llm.reply(
        "Done",
        trades=[{"ticker": "aapl", "side": "buy", "quantity": 10}],
        watchlist_changes=[{"ticker": "pypl", "action": "add"}],
    )

    response = await live_chat.handle_message("buy and add")

    assert response == {
        "message": "Done",
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
        "watchlist_changes": [
            {"ticker": "PYPL", "action": "add", "status": "applied", "error": None}
        ],
    }
    assert portfolio.get_portfolio()["cash_balance"] == 9000.0


@pytest.mark.parametrize(
    "content",
    [
        '{"message": "hi"}',
        '{"message": "hi", "trades": null, "watchlist_changes": null}',
        '{"message": "hi", "trades": []}',
        '{"message": "hi", "extra": 1}',
    ],
)
async def test_omitted_arrays_are_tolerated(live_chat, fake_llm, content):
    fake_llm.content = content

    assert await live_chat.handle_message("x") == {
        "message": "hi",
        "trades": [],
        "watchlist_changes": [],
    }


async def test_actions_run_independently_and_in_order(live_chat, fake_llm, portfolio, source):
    source.add_errors["TSLA"] = MarketDataUnavailableError("upstream said apiKey=abc123")
    fake_llm.reply(
        "Mixed",
        trades=[
            {"ticker": "AAPL", "side": "buy", "quantity": 1},
            {"ticker": "MSFT", "side": "sell", "quantity": 5},
            {"ticker": "GOOGL", "side": "buy", "quantity": 1000000},
            {"ticker": "TSLA", "side": "buy", "quantity": 1},
            {"ticker": "AAPL", "side": "sell", "quantity": 1},
            {"ticker": "NVDA", "side": "buy", "quantity": 1},
        ],
        watchlist_changes=[
            {"ticker": "ZZZZ", "action": "remove"},
            {"ticker": "PYPL", "action": "add"},
        ],
    )
    # TSLA is on the watchlist already; make the source treat it as new so the failure fires.
    source.tickers.discard("TSLA")

    response = await live_chat.handle_message("go")

    assert [t["status"] for t in response["trades"]] == [
        "executed",
        "failed",
        "failed",
        "failed",
        "executed",
        "executed",
    ]
    assert "Insufficient shares" in response["trades"][1]["error"]
    assert "Insufficient cash" in response["trades"][2]["error"]
    assert response["trades"][3]["error"] == MARKET_UNAVAILABLE_MESSAGE
    assert "abc123" not in json.dumps(response)
    assert [c["status"] for c in response["watchlist_changes"]] == ["failed", "applied"]
    assert [p["ticker"] for p in portfolio.get_portfolio()["positions"]] == ["NVDA"]


async def test_an_unexpected_exception_only_fails_its_own_action(live_chat, fake_llm, portfolio, monkeypatch):
    original = portfolio.execute_trade

    async def explode_on_tsla(ticker, side, quantity):
        if ticker == "TSLA":
            raise RuntimeError("secret internal detail")
        return await original(ticker, side, quantity)

    monkeypatch.setattr(portfolio, "execute_trade", explode_on_tsla)
    fake_llm.reply(
        "x",
        trades=[
            {"ticker": "TSLA", "side": "buy", "quantity": 1},
            {"ticker": "AAPL", "side": "buy", "quantity": 1},
        ],
    )

    response = await live_chat.handle_message("go")

    assert [t["status"] for t in response["trades"]] == ["failed", "executed"]
    assert "secret internal detail" not in json.dumps(response)


@pytest.mark.parametrize(
    "item",
    [
        "buy AAPL",
        42,
        None,
        [],
        {},
        {"side": "buy", "quantity": 1},
        {"ticker": 5, "side": "buy", "quantity": 1},
        {"ticker": "   ", "side": "buy", "quantity": 1},
        {"ticker": "NOT-A-TICKER", "side": "buy", "quantity": 1},
        {"ticker": "AAPL", "quantity": 1},
        {"ticker": "AAPL", "side": "short", "quantity": 1},
        {"ticker": "AAPL", "side": 1, "quantity": 1},
        {"ticker": "AAPL", "side": "BUY", "quantity": 1},
        {"ticker": "AAPL", "side": "buy"},
        {"ticker": "AAPL", "side": "buy", "quantity": "10"},
        {"ticker": "AAPL", "side": "buy", "quantity": None},
        {"ticker": "AAPL", "side": "buy", "quantity": True},
        {"ticker": "AAPL", "side": "buy", "quantity": 0},
        {"ticker": "AAPL", "side": "buy", "quantity": -5},
        {"ticker": "AAPL", "side": "buy", "quantity": 0.00001},
        {"ticker": "AAPL", "side": "buy", "quantity": 10**400},
    ],
)
async def test_a_bad_trade_item_becomes_one_failed_action(live_chat, fake_llm, portfolio, item):
    fake_llm.content = json.dumps(
        {"message": "x", "trades": [item, {"ticker": "MSFT", "side": "buy", "quantity": 1}]}
    )

    response = await live_chat.handle_message("go")

    bad, good = response["trades"]
    assert bad["status"] == "failed"
    assert bad["price"] is None
    assert bad["error"]
    assert isinstance(bad["ticker"], str)
    assert isinstance(bad["side"], str)
    assert isinstance(bad["quantity"], (int, float))
    assert good["status"] == "executed"
    json.dumps(response, allow_nan=False)
    assert [p["ticker"] for p in portfolio.get_portfolio()["positions"]] == ["MSFT"]


async def test_an_overflowing_float_quantity_fails_and_can_still_be_sent(live_chat, fake_llm):
    fake_llm.content = '{"message": "x", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1e999}]}'

    response = await live_chat.handle_message("go")

    assert response["trades"][0]["status"] == "failed"
    assert response["trades"][0]["quantity"] == 0
    json.dumps(response, allow_nan=False)


@pytest.mark.parametrize(
    "item",
    [
        "add AAPL",
        7,
        {},
        {"action": "add"},
        {"ticker": 1, "action": "add"},
        {"ticker": "PYPL"},
        {"ticker": "PYPL", "action": "delete"},
        {"ticker": "PYPL", "action": 1},
        {"ticker": "NOT-A-TICKER", "action": "add"},
        {"ticker": "ZZZZ", "action": "remove"},
    ],
)
async def test_a_bad_watchlist_item_becomes_one_failed_action(live_chat, fake_llm, portfolio, item):
    fake_llm.content = json.dumps(
        {"message": "x", "watchlist_changes": [item, {"ticker": "PYPL", "action": "add"}]}
    )

    response = await live_chat.handle_message("go")

    bad, good = response["watchlist_changes"]
    assert bad["status"] == "failed"
    assert bad["error"]
    assert isinstance(bad["ticker"], str)
    assert isinstance(bad["action"], str)
    assert good["status"] == "applied"
    assert "PYPL" in [w["ticker"] for w in portfolio.list_watchlist()]


# Whole-reply failures


async def assert_friendly_failure(chat, db, caplog):
    before = len(stored(db))
    with caplog.at_level(logging.ERROR, logger="app.llm.service"):
        response = await chat.handle_message("my question")

    assert response == {"message": FAILURE_MESSAGE, "trades": [], "watchlist_changes": []}
    user, assistant = stored(db)[before:]
    assert (user["role"], user["content"], user["actions"]) == ("user", "my question", None)
    assert assistant["role"] == "assistant"
    assert assistant["content"] == FAILURE_MESSAGE
    assert assistant["actions"] == {"trades": [], "watchlist_changes": []}
    assert any(r.levelno == logging.ERROR for r in caplog.records)
    return response


@pytest.mark.parametrize(
    "content",
    [
        "not json at all",
        "",
        None,
        12,
        "[]",
        '"just a string"',
        '{"message": "cut off',
        '{"trades": []}',
        '{"message": 5}',
        '{"message": "   "}',
        '{"message": null}',
        '{"message": "x", "trades": "AAPL"}',
        '{"message": "x", "trades": {"ticker": "AAPL"}}',
        '{"message": "x", "watchlist_changes": 5}',
        '{"message": "x", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": NaN}]}',
        '{"message": "\\ud800"}',
    ],
)
async def test_an_unusable_reply_is_a_friendly_failure(live_chat, db, fake_llm, caplog, content):
    fake_llm.content = content

    await assert_friendly_failure(live_chat, db, caplog)


async def test_a_schema_violation_runs_none_of_its_actions(live_chat, db, fake_llm, portfolio, caplog):
    fake_llm.content = json.dumps(
        {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}]}  # no message
    )

    await assert_friendly_failure(live_chat, db, caplog)

    assert portfolio.get_portfolio()["positions"] == []


async def test_an_api_error_is_a_friendly_failure_and_no_secret_escapes(live_chat, db, fake_llm, caplog):
    fake_llm.error = RuntimeError(f"401 from OpenRouter for key {TEST_KEY}: invalid")

    response = await assert_friendly_failure(live_chat, db, caplog)

    assert TEST_KEY not in json.dumps(response)
    assert TEST_KEY not in caplog.text
    assert "[redacted]" in caplog.text
    assert TEST_KEY not in json.dumps(stored(db))


async def test_real_litellm_exception_types_are_handled(live_chat, db, fake_llm, caplog):
    import litellm

    fake_llm.error = litellm.exceptions.RateLimitError("slow down", "openrouter", MODEL)

    await assert_friendly_failure(live_chat, db, caplog)


async def test_an_empty_choices_list_is_a_friendly_failure(live_chat, db, monkeypatch, caplog):
    from types import SimpleNamespace

    async def no_choices(**kwargs):
        return SimpleNamespace(choices=[])

    monkeypatch.setattr("litellm.acompletion", no_choices)

    await assert_friendly_failure(live_chat, db, caplog)


async def test_the_timeout_is_enforced_over_the_whole_call(live_chat, db, fake_llm, monkeypatch, caplog):
    monkeypatch.setattr("app.llm.client.TIMEOUT_SECONDS", 0.05)

    async def hang():
        await asyncio.sleep(60)

    fake_llm.during_call = hang

    await asyncio.wait_for(assert_friendly_failure(live_chat, db, caplog), timeout=5)

    assert "TimeoutError" in caplog.text


# Missing key


@pytest.mark.parametrize("environ", [{}, {"OPENROUTER_API_KEY": ""}, {"OPENROUTER_API_KEY": "   "}])
async def test_without_a_key_chat_says_not_configured_and_calls_nothing(db, portfolio, fake_llm, environ):
    chat = ChatService(db, portfolio, environ=environ)

    response = await chat.handle_message("hello")

    assert response["message"].startswith("LLM not configured")
    assert response["trades"] == []
    assert response["watchlist_changes"] == []
    assert fake_llm.calls == []
    assert [m["role"] for m in stored(db)] == ["user", "assistant"]


@pytest.mark.parametrize("flag", ["false", "", "1", "yes"])
async def test_only_true_turns_on_mock_mode(db, portfolio, flag):
    chat = ChatService(db, portfolio, environ={"LLM_MOCK": flag})

    assert (await chat.handle_message("hello"))["message"].startswith("LLM not configured")


def test_environ_defaults_to_the_process_environment(db, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    chat = ChatService(db, portfolio=None)

    assert asyncio.run(chat.handle_message("hello"))["message"].startswith("Mock response")


# Storage


async def test_messages_and_actions_are_stored(live_chat, db, fake_llm):
    fake_llm.reply(
        "Bought",
        trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1}],
        watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
    )

    response = await live_chat.handle_message("  buy it  ")

    user, assistant = stored(db)
    assert (user["role"], user["content"], user["actions"]) == ("user", "buy it", None)
    assert (assistant["role"], assistant["content"]) == ("assistant", "Bought")
    assert assistant["actions"] == {
        "trades": response["trades"],
        "watchlist_changes": response["watchlist_changes"],
    }


async def test_the_response_survives_a_failure_to_store_the_reply(live_chat, fake_llm, portfolio, monkeypatch):
    fake_llm.reply("Bought", trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1}])

    def fail(response):
        raise OSError("disk full")

    monkeypatch.setattr(live_chat, "_store_assistant", fail)

    response = await live_chat.handle_message("go")

    assert response["trades"][0]["status"] == "executed"


# Concurrency


async def test_nothing_is_locked_during_the_llm_call(live_chat, db, fake_llm, portfolio):
    async def write_while_waiting():
        # If the turn held the database's write lock, this would wait out the busy timeout and raise.
        def write():
            with db.connection() as conn:
                repo.set_cash(conn, 5000.0)

        await asyncio.wait_for(asyncio.to_thread(write), timeout=2)
        await asyncio.wait_for(portfolio.execute_trade("AAPL", "buy", 1), timeout=2)

    fake_llm.during_call = write_while_waiting

    response = await live_chat.handle_message("go")

    assert response["message"] == "ok"
    assert portfolio.get_portfolio()["cash_balance"] == 4900.0


async def test_concurrent_turns_do_not_interleave(live_chat, db, fake_llm):
    async def pause():
        await asyncio.sleep(0.01)

    fake_llm.during_call = pause

    await asyncio.gather(*(live_chat.handle_message(f"m{n}") for n in range(3)))

    assert [m["role"] for m in stored(db)] == ["user", "assistant"] * 3


# Parser units


def test_parse_reply_returns_the_raw_items():
    reply = parse_reply('{"message": "hi", "trades": [1, {"x": 2}], "watchlist_changes": ["a"]}')

    assert reply.message == "hi"
    assert reply.trades == [1, {"x": 2}]
    assert reply.watchlist_changes == ["a"]


def test_parse_errors_do_not_quote_the_reply():
    with pytest.raises(ReplyParseError) as caught:
        parse_reply("private portfolio text that is not json")

    assert "private" not in str(caught.value)
