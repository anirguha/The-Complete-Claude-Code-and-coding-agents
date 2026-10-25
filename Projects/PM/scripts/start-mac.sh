#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose up --build -d
printf '%s\n' "Project Management is running at http://localhost:8000"
