FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --no-dev --frozen
COPY backend/app ./backend/app
COPY --from=frontend-build /app/frontend/out ./frontend/out
ENV PATH="/app/backend/.venv/bin:$PATH" \
    DATABASE_PATH=/app/data/kanban.db \
    STATIC_ROOT=/app/frontend/out \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
