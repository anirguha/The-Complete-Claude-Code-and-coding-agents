#!/usr/bin/env bash
# Start FinAlly in Docker (macOS/Linux). Safe to run repeatedly.
#
#   scripts/start_mac.sh [--build] [--no-open]
#
#   --build     Rebuild the image, even if it exists.
#   --no-open   Do not open the browser.
#
# FINALLY_PORT sets the host port (default 8000).
set -euo pipefail

IMAGE=finally
CONTAINER=finally
VOLUME=finally-data
CONTAINER_PORT=8000
HEALTH_TIMEOUT_SECONDS=90
# Must exceed uvicorn's 3s graceful shutdown, or docker kills the app before it finishes.
STOP_TIMEOUT_SECONDS=10

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${FINALLY_PORT:-8000}"
BUILD=false
OPEN=true

die() {
  echo "Error: $*" >&2
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --build) BUILD=true ;;
    --no-open) OPEN=false ;;
    -h | --help)
      sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) die "unknown option '$arg'. Usage: scripts/start_mac.sh [--build] [--no-open]" ;;
  esac
done

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((10#$PORT < 1 || 10#$PORT > 65535)); then
  die "FINALLY_PORT must be a port number from 1 to 65535, got '$PORT'."
fi

command -v docker >/dev/null 2>&1 || die "docker is not installed."
docker info >/dev/null 2>&1 || die "cannot reach Docker. Is it running?"

port_is_taken() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

port_taken_message() {
  echo "port $PORT is already in use by another program. Choose a free one, for example: FINALLY_PORT=8030 scripts/start_mac.sh"
}

# Our own running container is about to be replaced, so its port does not count as taken.
# Checking before anything changes means a failed start leaves a running app alone.
own_port=""
if [ -n "$(docker ps -q --filter "name=^/${CONTAINER}$")" ]; then
  own_port="$(docker port "$CONTAINER" "$CONTAINER_PORT/tcp" 2>/dev/null | head -n 1 | sed 's/.*://')"
fi
if [ "$PORT" != "$own_port" ] && port_is_taken "$PORT"; then
  die "$(port_taken_message)"
fi

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env from .env.example. Add OPENROUTER_API_KEY to it to enable AI chat."
fi

if [ "$BUILD" = true ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building the $IMAGE image. The first build takes a few minutes."
  docker build -t "$IMAGE" "$ROOT"
fi

if [ -n "$(docker ps -aq --filter "name=^/${CONTAINER}$")" ]; then
  echo "Replacing the existing $CONTAINER container. Your data is kept."
  docker stop -t "$STOP_TIMEOUT_SECONDS" "$CONTAINER" >/dev/null
  docker rm "$CONTAINER" >/dev/null
fi

# Published on loopback only: the app has no login, and its chat can place trades.
run_error=""
if ! run_error="$(docker run -d \
  --name "$CONTAINER" \
  --stop-timeout "$STOP_TIMEOUT_SECONDS" \
  -v "$VOLUME:/app/db" \
  -p "127.0.0.1:$PORT:$CONTAINER_PORT" \
  --env-file "$ROOT/.env" \
  "$IMAGE" 2>&1)"; then
  docker rm "$CONTAINER" >/dev/null 2>&1 || true
  case "$run_error" in
    *"port is already allocated"* | *"address already in use"*) die "$(port_taken_message)" ;;
    *) die "could not start the container: $run_error" ;;
  esac
fi

printf 'Waiting for the app to become healthy'
status=""
for _ in $(seq 1 "$HEALTH_TIMEOUT_SECONDS"); do
  status="$(docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' "$CONTAINER")"
  case "$status" in
    running/healthy | running/unhealthy | exited/* | dead/*) break ;;
  esac
  printf '.'
  sleep 1
done
echo

if [ "$status" != "running/healthy" ]; then
  docker logs --tail 30 "$CONTAINER" >&2 || true
  die "the app did not become healthy (status: $status). See the logs above."
fi

URL="http://localhost:$PORT"
echo "FinAlly is running at $URL"
echo "Stop it with scripts/stop_mac.sh. Your data is kept in the $VOLUME volume."

if [ "$OPEN" = true ]; then
  if [ "$(uname)" = "Darwin" ]; then
    open "$URL" || echo "Could not open a browser. Go to $URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || echo "Could not open a browser. Go to $URL"
  fi
fi
