#!/usr/bin/env bash
# Stops and removes the Prelegal container. Accounts and saved-document records stay in the
# prelegal-data volume; to wipe them, run: docker volume rm prelegal-data
set -euo pipefail

if [ -n "$(docker ps -aq --filter 'name=^prelegal$')" ]; then
  docker rm -f prelegal >/dev/null
  echo "Prelegal stopped"
else
  echo "Prelegal was not running"
fi
