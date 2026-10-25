import json
import logging
import os
import uuid

import httpx
from fastapi import HTTPException

from app.models import Board, ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger("uvicorn.error")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "column_id", "card_id", "title", "details", "position"],
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                "rename_column",
                "create_card",
                "update_card",
                "move_card",
                "delete_card",
            ],
        },
        "column_id": {"type": ["string", "null"]},
        "card_id": {"type": ["string", "null"]},
        "title": {"type": ["string", "null"]},
        "details": {"type": ["string", "null"]},
        "position": {"type": ["integer", "null"]},
    },
}

RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["response", "actions"],
    "properties": {
        "response": {"type": "string"},
        "actions": {"type": "array", "items": ACTION_SCHEMA},
    },
}


def _message(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def _board_for_ai(board: Board) -> str:
    data = board.model_dump()
    data["cards"] = list(data["cards"].values())
    return json.dumps(data)


def _require(action: dict, field: str) -> str:
    value = action.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{action['type']} requires {field}.")
    return value


def apply_actions(board: Board, actions: list[dict]) -> Board:
    data = board.model_dump()
    columns = {column["id"]: column for column in data["columns"]}
    cards = data["cards"]

    def column_of(card_id: str) -> dict:
        return next(c for c in data["columns"] if card_id in c["cardIds"])

    for action in actions:
        kind = action.get("type")
        if not kind:
            continue
        if kind == "rename_column":
            columns[_require(action, "column_id")]["title"] = _require(action, "title")
        elif kind == "create_card":
            card_id = f"card-{uuid.uuid4().hex[:8]}"
            cards[card_id] = {
                "id": card_id,
                "title": _require(action, "title"),
                "details": action.get("details") or "No details yet.",
            }
            columns[_require(action, "column_id")]["cardIds"].append(card_id)
        elif kind == "update_card":
            card = cards[_require(action, "card_id")]
            if action.get("title"):
                card["title"] = action["title"]
            if action.get("details") is not None:
                card["details"] = action["details"]
        elif kind == "move_card":
            card_id = _require(action, "card_id")
            if card_id not in cards:
                raise ValueError(f"Unknown card {card_id}.")
            target = columns[_require(action, "column_id")]
            column_of(card_id)["cardIds"].remove(card_id)
            position = action.get("position")
            if position is None:
                target["cardIds"].append(card_id)
            else:
                target["cardIds"].insert(max(position, 0), card_id)
        elif kind == "delete_card":
            card_id = _require(action, "card_id")
            if card_id not in cards:
                raise ValueError(f"Unknown card {card_id}.")
            column_of(card_id)["cardIds"].remove(card_id)
            del cards[card_id]
        else:
            raise ValueError(f"Unknown action {kind}.")
    return Board.model_validate(data)


async def answer_chat(
    board: Board, request: ChatRequest
) -> ChatResponse:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI chat is unavailable because OPENROUTER_API_KEY is not configured.",
        )

    history: list[ChatMessage] = request.history
    messages = [
        _message(
            "system",
            "You help manage this Kanban board. Always answer in the required JSON "
            "format with a non-empty `response` for the user. To change the board, "
            "add actions using the existing column and card IDs below; leave `actions` "
            "empty unless the user explicitly asks for a change (greetings, questions, "
            "and summaries never change the board). Action fields not used by an "
            "action type must be null. rename_column: column_id, title. create_card: "
            "column_id, title, details. update_card: card_id and the title and/or "
            "details to change. move_card: card_id, column_id, optional position "
            "(0-based, default end). delete_card: card_id. Board JSON: "
            + _board_for_ai(board),
        ),
        *[_message(item.role, item.content) for item in history],
        _message("user", request.message),
    ]

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "reasoning": {"effort": "low"},
                    "provider": {"require_parameters": True},
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "kanban_assistant_response",
                            "strict": True,
                            "schema": RESPONSE_SCHEMA,
                        },
                    },
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI provider returned HTTP {error.response.status_code}.",
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail="Could not connect to the AI provider."
        ) from error

    try:
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("AI response content is not text.")
        data = json.loads(content)
        reply = data["response"]
        if not isinstance(reply, str):
            raise ValueError("AI response text is missing.")
        updated_board = board
        if data["actions"]:
            updated_board = apply_actions(board, data["actions"])
    except (
        KeyError,
        IndexError,
        StopIteration,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        logger.warning(
            "Invalid AI response (%s): %s; body=%.2000s",
            type(error).__name__,
            str(error).replace("\n", " "),
            response.text,
        )
        raise HTTPException(
            status_code=502,
            detail="AI returned an invalid response. No board changes were saved.",
        ) from error

    return ChatResponse(response=reply, board=updated_board)
