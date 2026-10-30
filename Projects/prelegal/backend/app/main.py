import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.confluence import Confluence
from app.db import init_database
from app.routers import auth, chat, documents

BACKEND_DIR = Path(__file__).resolve().parent.parent


def create_app(db_path: Path, static_dir: Path, confluence: Confluence | None = None) -> FastAPI:
    """Builds the app. The database at db_path is created on startup if needed and kept between runs.

    Without a Confluence client, saving documents is unavailable and everything else still works.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_database(db_path)
        yield

    app = FastAPI(title="Prelegal", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.confluence = confluence

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(documents.router)

    # Mounted last so the API routes above take precedence over the exported frontend.
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app(
    db_path=Path(os.environ.get("PRELEGAL_DB_PATH", BACKEND_DIR / "data" / "prelegal.db")),
    static_dir=Path(os.environ.get("PRELEGAL_STATIC_DIR", BACKEND_DIR.parent / "frontend" / "out")),
    confluence=Confluence.from_env(),
)
