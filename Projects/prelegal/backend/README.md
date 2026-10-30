# Prelegal backend

FastAPI app that serves the API under `/api` and the statically exported frontend at `/`.
The AI chat drafts the documents defined in `../documents.json`; saved documents are stored in Confluence.
The SQLite database (users, sessions, the saved-document index) is created from `app/schema.sql` if missing and kept between runs.

```bash
uv sync
uv run --env-file ../.env uvicorn app.main:app --reload   # http://localhost:8000
uv run pytest                       # the live AI and Confluence tests are skipped
uv run --env-file ../.env pytest    # includes them (Confluence only when its settings are set)
```

Settings (environment variables):

- `PRELEGAL_DB_PATH` — SQLite file, default `data/prelegal.db`
- `OPENROUTER_API_KEY` — used by the AI chat (`/api/chat`); kept in the project root `.env`
- `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_SPACE_KEY` — where saved documents go (`/api/documents`); without them saving returns 503
- `PRELEGAL_STATIC_DIR` — exported frontend, default `../frontend/out` (skipped if missing)
