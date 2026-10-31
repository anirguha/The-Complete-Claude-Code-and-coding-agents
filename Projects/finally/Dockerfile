# Stage 1: build the static frontend export (frontend/out).
FROM node:22-slim AS frontend
WORKDIR /build
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: the FastAPI app, which serves the API and the frontend on one port.
FROM python:3.12-slim
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir --root-user-action=ignore uv==0.12.6

WORKDIR /app
# Dependencies get their own layer, so editing app code does not reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --no-install-project
COPY backend/app ./app
RUN uv sync --frozen --no-dev --no-cache
COPY --from=frontend /build/out ./static

# COPY keeps host file modes, and some source files here are 0600, so open them up
# for the non-root user. A fresh named volume copies /app/db's owner, so the app can
# write to it.
RUN useradd --create-home --uid 1000 finally \
    && chmod -R a+rX /app/app /app/static \
    && mkdir -p /app/db \
    && chown finally:finally /app/db
USER finally

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/app/db/finally.db \
    STATIC_DIR=/app/static
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

# The timeout is required: an open SSE stream otherwise blocks shutdown until docker kills it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "3"]
