#!/usr/bin/env bash
# Stop and remove the FinAlly container (macOS/Linux). Safe to run repeatedly.
# The finally-data volume is kept, so your portfolio survives.
set -euo pipefail

CONTAINER=finally
# Must exceed uvicorn's 3s graceful shutdown, or docker kills the app before it finishes.
STOP_TIMEOUT_SECONDS=10

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker is not running, so there is nothing to stop."
  exit 0
fi

if [ -z "$(docker ps -aq --filter "name=^/${CONTAINER}$")" ]; then
  echo "FinAlly is not running. Nothing to stop."
  exit 0
fi

docker stop -t "$STOP_TIMEOUT_SECONDS" "$CONTAINER" >/dev/null
docker rm "$CONTAINER" >/dev/null
echo "FinAlly stopped. Your data is kept in the finally-data volume."
