"""HTTP routes for chat."""

from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import BaseModel, BeforeValidator, StringConstraints

from .service import ChatService

MAX_MESSAGE_CHARS = 4000


def _without_lone_surrogates(value: Any) -> str | None:
    """JSON can carry them, but they can be neither stored nor echoed in a 422 response.

    A non-string becomes None, which fails validation without echoing what was sent.
    """
    return value.encode("utf-8", "replace").decode("utf-8") if isinstance(value, str) else None


class ChatRequest(BaseModel):
    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_CHARS, strict=True),
        BeforeValidator(_without_lone_surrogates),  # later in this list means it runs first
    ]


def create_chat_router(chat: ChatService) -> APIRouter:
    router = APIRouter(prefix="/api/chat")

    @router.post("")
    async def send_message(request: ChatRequest) -> dict[str, Any]:
        return await chat.handle_message(request.message)

    @router.get("/history")  # a plain `def` runs on the thread pool, so SQLite never blocks the loop
    def history() -> dict[str, Any]:
        return {"messages": chat.list_history()}

    return router
