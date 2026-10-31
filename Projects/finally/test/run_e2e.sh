#!/usr/bin/env bash
# Run the Playwright suite against an app that is already running with LLM_MOCK=true.
#
#   E2E_BASE_URL=http://localhost:8010 test/run_e2e.sh [playwright args]
#
# Works from a copy under $TMPDIR, because this project lives on Google Drive
# and node_modules must stay out of the project tree.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="${TMPDIR:-/tmp}/finally-e2e"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-${TMPDIR:-/tmp}/pw-browsers}"
export npm_config_cache="${npm_config_cache:-${TMPDIR:-/tmp}/npm-cache}"
export E2E_SCREENSHOT_DIR="${E2E_SCREENSHOT_DIR:-$work/screenshots}"

mkdir -p "$work"
rsync -a --delete --exclude node_modules --exclude test-results --exclude screenshots "$here/" "$work/"
cd "$work"
[ -d node_modules/@playwright/test ] || npm install --no-audit --no-fund
npx playwright install chromium
exec npx playwright test "$@"
