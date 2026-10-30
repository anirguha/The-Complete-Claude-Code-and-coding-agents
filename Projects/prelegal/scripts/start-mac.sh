#!/usr/bin/env bash
# Builds the Prelegal image and starts it at http://localhost:8000.
# Accounts and saved-document records persist in the prelegal-data Docker volume.
# Set PRELEGAL_PORT to use a different host port.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=prelegal
CONTAINER=prelegal
VOLUME=prelegal-data
PORT="${PRELEGAL_PORT:-8000}"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
if curl -s -o /dev/null "http://localhost:$PORT"; then
  echo "Port $PORT is already in use. Stop whatever is using it, or set PRELEGAL_PORT." >&2
  exit 1
fi

docker build -t "$IMAGE" .

ENV_ARGS=()
[ -f .env ] && ENV_ARGS=(--env-file .env)
if ! docker run -d --name "$CONTAINER" -p "$PORT:8000" -v "$VOLUME:/app/data" ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} "$IMAGE" >/dev/null; then
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  exit 1
fi

for _ in $(seq 30); do
  if curl -fsS "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
    echo "Prelegal is running at http://localhost:$PORT"
    exit 0
  fi
  sleep 1
done
echo "Prelegal did not become healthy; recent logs:" >&2
docker logs --tail 50 "$CONTAINER" >&2
exit 1
