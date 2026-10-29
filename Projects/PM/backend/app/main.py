import hmac
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.ai import answer_chat, apply_actions
from app.database import initialize_database, load_board, update_board
from app.models import Board, ChatRequest, ChatResponse, Credentials


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="Project Management API", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32),
    same_site="lax",
    https_only=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)

STATIC_ROOT = Path(os.environ.get("STATIC_ROOT", "../frontend/out")).resolve()


def authenticated_user(request: Request) -> str:
    user_id = request.session.get("user_id")
    if user_id != "user":
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user_id


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(credentials: Credentials, request: Request) -> dict[str, str]:
    valid_username = hmac.compare_digest(credentials.username.encode(), b"user")
    valid_password = hmac.compare_digest(credentials.password.encode(), b"password")
    if not (valid_username and valid_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    request.session.clear()
    request.session["user_id"] = "user"
    load_board("user")
    return {"username": "user"}


@app.get("/api/auth/me")
def current_user(user_id: str = Depends(authenticated_user)) -> dict[str, str]:
    return {"username": user_id}


@app.post("/api/auth/logout", dependencies=[Depends(authenticated_user)])
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@app.get("/api/board")
def get_board(user_id: str = Depends(authenticated_user)) -> Board:
    return load_board(user_id)


@app.put("/api/board")
def put_board(board: Board, user_id: str = Depends(authenticated_user)) -> Board:
    def replace(current: Board) -> Board:
        if [c.id for c in board.columns] != [c.id for c in current.columns]:
            raise HTTPException(
                status_code=400, detail="Columns can be renamed but not changed."
            )
        return board

    return update_board(user_id, replace)


@app.post("/api/chat")
async def chat(
    chat_request: ChatRequest,
    user_id: str = Depends(authenticated_user),
) -> ChatResponse:
    reply, actions = await answer_chat(load_board(user_id), chat_request)
    # Apply the actions to the latest board so edits made while the AI was
    # responding are kept.
    try:
        board = update_board(user_id, lambda latest: apply_actions(latest, actions))
    except (KeyError, StopIteration, ValueError) as error:
        raise HTTPException(
            status_code=409,
            detail="The board changed while the AI was responding. "
            "No AI changes were saved.",
        ) from error
    return ChatResponse(response=reply, board=board)


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str) -> FileResponse:
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found.")
    requested_path = (STATIC_ROOT / path).resolve()
    if requested_path != STATIC_ROOT and STATIC_ROOT not in requested_path.parents:
        raise HTTPException(status_code=404, detail="Not found.")
    if requested_path.is_dir():
        requested_path = requested_path / "index.html"
    if not requested_path.is_file():
        requested_path = STATIC_ROOT / "index.html"
    if not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Frontend is not built.")
    return FileResponse(requested_path)
