# Stage 1: build the Next.js frontend as a static export (frontend/out).
FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# The page reads documents.json and the shared templates from the project root at build time.
COPY documents.json /app/documents.json
COPY templates/ /app/templates/
RUN npm run build

# Stage 2: the FastAPI backend, which serves the API and the exported frontend.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
# The chat API reads the document definitions from ../documents.json.
COPY documents.json /app/documents.json
COPY backend/app ./app
COPY --from=frontend /app/frontend/out /app/static

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PRELEGAL_STATIC_DIR=/app/static \
    PRELEGAL_DB_PATH=/app/data/prelegal.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
