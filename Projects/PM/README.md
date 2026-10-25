# Project Management MVP

## Run locally

Set `OPENROUTER_API_KEY` in `.env` at this project root to enable AI chat. Start Docker Desktop, then run `scripts/start-mac.sh`, `scripts/start-linux.sh`, or `scripts/start-windows.ps1`. Open `http://localhost:8000` and sign in with `user` / `password`.

The SQLite database is stored in the Docker named volume `pm-data` and survives normal container stops/rebuilds. Use the matching stop script to stop the app. Removing the volume with `docker compose down -v` permanently deletes the local board.

## Development

- Frontend: `cd frontend && npm install && npm run dev`
- Backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload --host localhost --port 8000`
- Backend tests: `cd backend && uv run pytest`
- Frontend unit tests: `cd frontend && npm run test:unit`
