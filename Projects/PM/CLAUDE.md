# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read `AGENTS.md` (business requirements, coding standards, color scheme) and `docs/PLAN.md` before making changes. `frontend/AGENTS.md`, `backend/AGENTS.md`, and `scripts/AGENTS.md` hold per-directory conventions. Key standards: keep it simple, no over-engineering, no emojis, identify root cause with evidence before fixing.

## Commands

Run the packaged app (Docker): `scripts/start-mac.sh` / `scripts/stop-mac.sh` (also `-linux.sh`, `-windows.ps1`), then open http://localhost:8000 and sign in with `user` / `password`.

Backend (from `backend/`, Python 3.12, managed by `uv`):
- `uv sync`
- `uv run uvicorn app.main:app --reload --host localhost --port 8000`
- `uv run pytest` (all tests), `uv run pytest tests/test_api.py::test_name` (single test)

Frontend (from `frontend/`):
- `npm run dev` (talks to FastAPI at `http://localhost:8000`, override with `NEXT_PUBLIC_API_URL`)
- `npm run test:unit`, single file: `npx vitest run src/lib/kanban.test.ts`, single test: add `-t "name"`
- `npm run lint`, `npm run build` (static export to `frontend/out`)
- `npm run test:e2e` (Playwright; starts its own backend on port 8001 with a temp DB and `next dev` on 3000)

## Architecture

One container, one origin. The Dockerfile builds the Next.js app as a static export (`output: "export"`) and copies `frontend/out` into a `uv`-based Python image. FastAPI (`backend/app/main.py`) serves `/api/*` and falls through to a catch-all route that serves files from `STATIC_ROOT`. Because the frontend is static, it cannot use server-only Next.js features, API routes, or image optimization.

- **Auth**: fixed `user` / `password` check, stored in a signed HTTP-only session cookie (`SESSION_SECRET`). Protected routes depend on `authenticated_user`. The `users` row and a seeded demo board are created on first sign-in.
- **Persistence** (`backend/app/database.py`): SQLite at `DATABASE_PATH` (default `backend/data/kanban.db`, `/app/data/kanban.db` in Docker on the `pm-data` named volume). Tables are created on startup. Saving a board replaces all its columns and cards in one transaction. Schema is documented in `docs/DATABASE.md` and `docs/database-schema.json`.
- **Board model** (`backend/app/models.py`, mirrored in `frontend/src/lib/kanban.ts`): `columns` is an ordered list of `{id, title, cardIds}` and `cards` is a map of id to `{id, title, details}`. Pydantic validates that every card appears in exactly one column. The frontend always sends the full board via `PUT /api/board`.
- **AI chat** (`backend/app/ai.py`, `POST /api/chat`): calls OpenRouter with model `openai/gpt-oss-120b`, sending the board JSON plus chat history and requiring strict JSON-schema output of `{response, actions[]}`. Actions (`rename_column`, `create_card`, `update_card`, `move_card`, `delete_card`) are applied by `apply_actions` and the result is validated as a full `Board` before saving. Any provider error or invalid output aborts without changing the board. A missing `OPENROUTER_API_KEY` returns 503. (`docs/PLAN.md` and `docs/DATABASE.md` still describe a full-board `board_update` response; the code uses the action list.)
- **Frontend data flow**: `src/app/page.tsx` owns session and board state; all server calls go through `src/lib/api.ts` (with credentials included). Drag-and-drop uses `@dnd-kit`. Don't add local storage as a second source of truth, and on a failed write, show the error and reload the saved board.

## Environment

`.env` at the project root (see `.env.example`) provides `OPENROUTER_API_KEY` and `SESSION_SECRET` to Docker Compose at runtime. It is never copied into the image.
