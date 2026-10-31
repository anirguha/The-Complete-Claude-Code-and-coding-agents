"""The real litellm code, stopped at the HTTP layer: what would actually be sent to OpenRouter.

No request leaves the process. This proves our arguments survive litellm's
translation, not that OpenRouter accepts them.
"""

import asyncio
import json
import logging

import httpx
import pytest

from tests.llm.conftest import TEST_KEY


def completion_response(request: httpx.Request, content: str) -> httpx.Response:
    return httpx.Response(
        200,
        request=request,
        json={
            "id": "gen-1",
            "object": "chat.completion",
            "created": 1,
            "model": "openai/gpt-oss-120b",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


@pytest.fixture
def transport(monkeypatch):
    """Replaces HTTP sends. Set `respond` to control the outcome; `requests` records each one."""

    class Transport:
        requests: list[httpx.Request] = []
        delay = 0.0
        content = json.dumps(
            {
                "message": "Bought",
                "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}],
                "watchlist_changes": [],
            }
        )
        respond = None

    state = Transport()
    state.requests = []

    async def send(self, request, **kwargs):
        state.requests.append(request)
        if state.delay:
            await asyncio.sleep(state.delay)
        if state.respond is not None:
            return state.respond(request)
        return completion_response(request, state.content)

    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    return state


async def test_the_request_on_the_wire(live_chat, transport):
    response = await live_chat.handle_message("buy one apple")

    assert response["message"] == "Bought"
    assert response["trades"][0]["status"] == "executed"

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {TEST_KEY}"
    assert request.extensions["timeout"]["read"] == 30.0

    body = json.loads(request.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["provider"] == {"order": ["cerebras"]}
    assert body["reasoning_effort"] == "low"
    assert body["messages"][-1] == {"role": "user", "content": "buy one apple"}
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert set(response_format["json_schema"]["schema"]["required"]) == {
        "message",
        "trades",
        "watchlist_changes",
    }


@pytest.mark.parametrize("status", [401, 429, 500, 503])
async def test_an_http_error_fails_once_without_retrying_or_leaking(live_chat, transport, caplog, status):
    transport.respond = lambda request: httpx.Response(
        status, request=request, json={"error": {"message": f"bad key {TEST_KEY}", "code": status}}
    )

    with caplog.at_level(logging.DEBUG):
        response = await live_chat.handle_message("hello")

    assert response["trades"] == []
    assert response["message"].startswith("Sorry")
    assert len(transport.requests) == 1
    assert TEST_KEY not in json.dumps(response)
    assert TEST_KEY not in "\n".join(
        r.getMessage() for r in caplog.records if r.name.startswith("app.")
    )


async def test_the_event_loop_stays_responsive_during_a_slow_call(live_chat, transport):
    transport.delay = 0.6
    gaps: list[float] = []

    async def heartbeat():
        loop = asyncio.get_running_loop()
        last = loop.time()
        while True:
            await asyncio.sleep(0.01)
            now = loop.time()
            gaps.append(now - last)
            last = now

    beat = asyncio.create_task(heartbeat())
    await live_chat.handle_message("hello")
    beat.cancel()

    assert len(gaps) >= 10
    assert max(gaps) < 0.4
