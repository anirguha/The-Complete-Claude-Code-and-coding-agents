# Backend

This directory contains the FastAPI service, SQLite persistence layer, OpenRouter client, and backend tests. Run it locally from this directory with `uv run uvicorn app.main:app --reload --host localhost --port 8000`.

## Structure

- `app/main.py`: HTTP routes, session authentication, CORS for the local Next.js development server, and static frontend serving.
- `app/models.py`: Pydantic API models and complete-board consistency validation.
- `app/database.py`: SQLite schema creation, demo-board seeding, ordered board reads, and transactional saves.
- `app/ai.py`: OpenRouter request using the configured structured-output schema and response validation.
- `tests/`: pytest API, persistence, model, and AI behavior tests.

## Conventions

- Keep all board reads and writes scoped to the authenticated user.
- Validate the complete board before persisting it; AI proposals must not bypass the same validation.
- Never return API keys or raw provider credentials in an error response.
- Keep `OPENROUTER_API_KEY` and `SESSION_SECRET` in runtime environment variables, not source files or the image.
- Run `uv run pytest` from this directory after backend changes.