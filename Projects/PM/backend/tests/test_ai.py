import json

import httpx
import pytest
from fastapi import HTTPException

from app import ai
from app.database import DEFAULT_BOARD
from app.models import ChatRequest


class FakeResponse:
    def __init__(self, content):
        self.content = content
        self.text = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}



class FakeClient:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def post(self, url, **kwargs):
        self.request = {"url": url, **kwargs}
        if self.error:
            raise self.error
        return FakeResponse(self.content)


def action(kind, **fields):
    base = {
        "type": kind,
        "column_id": None,
        "card_id": None,
        "title": None,
        "details": None,
        "position": None,
    }
    return {**base, **fields}


@pytest.mark.asyncio
async def test_sends_board_history_and_applies_structured_actions(monkeypatch):
    fake_client = FakeClient(
        json.dumps(
            {
                "response": "Updated the column.",
                "actions": [
                    action("rename_column", column_id="col-backlog", title="To Do")
                ],
            }
        )
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda timeout: fake_client)
    history = [{"role": "assistant", "content": "Prior answer"}]

    reply, actions = await ai.answer_chat(
        DEFAULT_BOARD, ChatRequest(message="Rename backlog", history=history)
    )

    assert reply == "Updated the column."
    assert ai.apply_actions(DEFAULT_BOARD, actions).columns[0].title == "To Do"
    messages = fake_client.request["json"]["messages"]
    assert "Board JSON" in messages[0]["content"]
    assert messages[1] == {"role": "assistant", "content": "Prior answer"}
    assert messages[2] == {"role": "user", "content": "Rename backlog"}
    assert fake_client.request["json"]["model"] == "openai/gpt-oss-120b"
    assert fake_client.request["json"]["response_format"]["json_schema"]["strict"]


def test_actions_create_edit_move_and_delete_cards():
    board = ai.apply_actions(
        DEFAULT_BOARD,
        [
            action("create_card", column_id="col-done", title="New", details="Notes"),
            action("update_card", card_id="card-1", title="Renamed"),
            action("move_card", card_id="card-2", column_id="col-review", position=0),
            action("delete_card", card_id="card-3"),
        ],
    )

    assert board.cards["card-1"].title == "Renamed"
    assert board.columns[3].cardIds == ["card-2", "card-6"]
    assert "card-3" not in board.cards
    assert board.columns[1].cardIds == []
    new_id = board.columns[4].cardIds[-1]
    assert board.cards[new_id].title == "New"
    assert DEFAULT_BOARD.columns[1].cardIds == ["card-3"]


@pytest.mark.asyncio
async def test_invalid_ai_action_is_rejected_without_changes(monkeypatch):
    fake_client = FakeClient(
        json.dumps(
            {
                "response": "Done.",
                "actions": [action("delete_card", card_id="missing-card")],
            }
        )
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda timeout: fake_client)

    with pytest.raises(HTTPException, match="No board changes were saved"):
        await ai.answer_chat(DEFAULT_BOARD, ChatRequest(message="Delete a card"))


@pytest.mark.asyncio
async def test_malformed_ai_response_is_rejected(monkeypatch):
    fake_client = FakeClient("not json")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda timeout: fake_client)

    with pytest.raises(HTTPException, match="invalid response"):
        await ai.answer_chat(DEFAULT_BOARD, ChatRequest(message="Hello"))


@pytest.mark.asyncio
async def test_provider_http_error_is_surfaced(monkeypatch):
    request = httpx.Request("POST", ai.OPENROUTER_URL)
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError(
        "rate limited", request=request, response=response
    )
    fake_client = FakeClient(error=error)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda timeout: fake_client)

    with pytest.raises(HTTPException, match="HTTP 429"):
        await ai.answer_chat(DEFAULT_BOARD, ChatRequest(message="Hello"))


@pytest.mark.asyncio
async def test_provider_connection_error_is_surfaced(monkeypatch):
    request = httpx.Request("POST", ai.OPENROUTER_URL)
    fake_client = FakeClient(error=httpx.ConnectError("offline", request=request))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda timeout: fake_client)

    with pytest.raises(HTTPException, match="Could not connect"):
        await ai.answer_chat(DEFAULT_BOARD, ChatRequest(message="Hello"))
