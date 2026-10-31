# FinAlly Integration Report

Date: 2026-10-31. Author: Integration Engineer. Nothing here is committed.

## Verdict

**Ready for DevOps, with one requirement:** the container's uvicorn command must pass `--timeout-graceful-shutdown 3` (defect 3). The frontend and the real backend work together in a real browser. Two real defects were fixed and one needs that flag.

## Results

All runs below are from the final code.

| Suite | Command (see Reproduce) | Result |
| ----- | ----------------------- | ------ |
| Backend, all, Python 3.14 (local venv) | `uv run --frozen pytest` | 521 passed |
| Backend, all, Python 3.12.12 (the Dockerfile's version) | same, separate venv | 521 passed |
| Of which, new API integration tests | `pytest tests/integration` | 42 passed, 3 runs in a row |
| Frontend unit tests, `tsc`, ESLint | in a `$TMPDIR` copy | 83 passed, both clean |
| Browser E2E, fresh database | `test/run_e2e.sh` | 27 passed |
| Browser E2E, same server again, used database | `test/run_e2e.sh` | 26 passed, 1 skipped |

The skip is deliberate: `first launch shows...` cannot apply to a used database, so it skips itself. `E2E_REQUIRE_FRESH=1` turns that skip into a failure, and the fresh run above used it. The server log held no warnings or errors after these runs. Every browser test also fails on any uncaught page error or undeclared console error.

**How the browser tests ran.** Binding a port and connecting to loopback both fail with `EPERM` in the sandbox. The server and Playwright were re-run with the sandbox disabled, through the permission gate, which allowed it. Chromium only, viewport 1440x900 except the tablet checks.

## Defects found

### 1. Fixed: 19 frontend source files would never have been committed

- **Symptom:** `git check-ignore` reports all of `frontend/src/lib/` as ignored. A commit would silently drop `api.ts`, `types.ts`, `priceStore.ts` and the rest, so a clean checkout or Docker build could not compile. It worked locally only because the files were on disk.
- **Root cause:** the repository-root `.gitignore` has a Python `lib/` rule.
- **Fix:** `!src/lib/` in `frontend/.gitignore`.
- **Regression test:** `backend/tests/integration/test_repository_files.py` fails if git ignores any source file under `frontend/src`, `backend/app`, `backend/tests` or `test/e2e`.

### 2. Fixed: a brand-new portfolio showed a loss on the P&L chart

- **Symptom:** on first launch, with one snapshot and no change, the chart drew a red dash and a red-centered dot.
- **Root cause:** Lightweight Charts draws a lone point as a short dash, and a value exactly on the baseline counts as below it.
- **Fix:** in `frontend/src/components/PnlChart.tsx`, a lone snapshot now has no line and no fill, and its baseline sits under it, so it is a plain green dot. `frontend/out` was rebuilt.
- **Regression test:** the first-launch E2E test counts red canvas pixels in the chart. It failed before the fix (166 pixels, then 17 after a partial fix) and passes now (0).

### 3. Needs DevOps: stopping the server hangs while a browser is open

- **Symptom:** SIGTERM with a browser's SSE stream attached: not exited after 15s, and needed SIGKILL. With no client attached it exits in 136ms. `docker stop` would wait its full 10s and then kill.
- **Root cause:** uvicorn waits for open responses before running shutdown, and the SSE stream never ends. The app's lifespan shutdown runs too late to end it.
- **Fix required:** add `--timeout-graceful-shutdown 3` to the `uvicorn` command in the Dockerfile. Measured with the flag and a client attached: exits in 3.2s and logs `Application shutdown complete`. It also logs a `CancelledError` traceback for the stream and returns 143, both harmless.
- **Data risk:** none seen. Each trade is its own committed transaction, and a SIGKILLed server restarted on the same database with cash and positions intact.
- **Why not in app code:** making the stream notice shutdown means wrapping uvicorn's signal handling, which is more invasive than one flag. No automated regression test exists; DevOps should time `docker stop` with a browser open.

### Test mistakes, not app defects

Two of my own tests failed at first, and I corrected the tests:

- A restart test expected an empty watchlist after buying AAPL, but buys add to the watchlist by contract. It now empties the list without buying, and cash has its own test.
- The heatmap color check judged red against green directly, but the neutral cell color is already slightly green, so a -0.01% cell read as green. It now measures the shift from neutral. Below 0.05% a neutral color is accepted, because the color may not have moved a visible step. At 0.05% or more the hue must match.

## What is covered

**API integration (`backend/tests/integration/`)** uses the real `create_app`, lifespan, simulator and SQLite temp file, with `LLM_MOCK=true`. Each listed area has tests:

- Chat buy reaching cash, positions, trades, snapshots and stored chat history; chat sell, add and remove.
- Failed actions: reported, changing nothing, leaving no stray feed, and not blocking later actions.
- Watchlist removal while holding keeps the feed; closing an unwatched position ends it; closing a watched one keeps it.
- SSE contract, moving prices, and stream contents equal to the tracked tickers through a session.
- Restart on the same `DB_PATH`: all data survives, cash is not reset, an emptied watchlist is not reseeded, and a held unwatched ticker gets prices and can be sold, which then ends its feed.
- Money: totals match rows, cash is conserved, and 20 concurrent buys cannot overspend.
- **Frontend contract:** `test_frontend_contract.py` parses `frontend/src/lib/types.ts` and `api.ts`, then checks real responses field by field in both directions, for every endpoint and for every kind of chat turn. No mismatches were found.

**Browser (`test/e2e/`)** covers every Section 12 scenario in the brief: fresh start, watchlist add and remove, buy, sell, heatmap colors, mocked chat (executed, failed, watchlist add), chart selection, and reload. Also: price flashes, sparklines, a live header total, rejected trades, auto-add on buy, fractional shares, removing a selected or held ticker, charting an unwatched holding, and the sub-1200px drawer. Charts are checked by reading canvas pixels, not just React attributes.

**Screenshots reviewed** at 1440x900 and 1024x768: first launch, no positions, six positions, tablet, and tablet with chat open. Layout is sound, with no overlap or overflow at 1440x900. The only visibly wrong things are defect 2 and open issues 2 and 3.

**One-off system check, run once, before the defect 2 fix (that fix only touched `PnlChart`).** The script is not kept in the repo. With a browser open, the server was stopped and restarted on the same database:

- The dot went `reconnecting`, then `disconnected` at 9.6s, then `connected` once the server returned, with no reload.
- Cash was unchanged, and the held unwatched ticker kept getting live prices.
- A further 70s soak: P&L points grew from 1 to 3, no page errors, and the only console errors were the expected connection failures from the outage.

## Open issues

Product decisions, recorded and not decided:

1. **Simulated prices reset to their seed on restart, and on removing and re-adding a ticker.** This comes from `GBMSimulator.add_ticker`; only a short restart was observed. A position bought after the price has drifted shows a sudden P&L jump on restart. By my estimate from the model's parameters, that is about 5% for NVDA after a day of uptime. Persisting the last prices would fix it, if it matters for a demo.

Cosmetic, left as is:

2. A tiny loss shows `0.00%` in red, because the color uses the unrounded value (`signClass`).
3. Widening or narrowing the window past 1200px does not close an open chat panel, which then covers part of the terminal until closed. It is closed by default when loaded narrow, as specified.
4. Mock replies read `buying 1 shares`. This matches the contract's wording.

Minor risk with a real LLM:

5. Per the LLM change log, a failed action can echo any `side` or `action`, but `types.ts` narrows them to the valid values and `describeTrade` treats anything other than `buy` as a sell. A failed `side: "hold"` would read `Sell 1 X failed: Invalid side`. The error text is still accurate. Mock mode cannot produce this.

## Not verified

- **Docker:** no image was built and no container run. That is DevOps' scope.
- **Real LLM and real Massive API:** not called. Contract item 29 excludes Massive from E2E.
- **Node 22:** the frontend was built on this machine's Node 26.12.1. `npm ci --dry-run` on the project's lockfile did not report a mismatch. The Node 22 build happens first in the Docker stage.
- **Other browsers:** no Firefox or Safari.
- **SSE resilience:** not automated, per contract item 27; see the one-off check above.
- **"A failed action does not block the next":** mock mode gives one action per message, so that test scripts the reply. The action execution and storage behind it are real.
- **Heatmap profit and loss together:** one test patches `avg_cost` in the browser, since live P&L sits near zero after a purchase. A second test checks real, live values, but cannot force both signs.

## Docker verification

Date: 2026-10-31. Author: DevOps Engineer. Nothing is committed. Docker 29.8.2, arm64 (Apple Silicon). Docker and loopback commands ran with the sandbox disabled, through the permission gate.

This supersedes the "Docker" and "Node 22" lines under "Not verified" above.

| Check | Result |
| ----- | ------ |
| Build from a clean checkout simulation (`git ls-files --cached --others --exclude-standard` copied to a temp directory, path with a space) | Passed on Node 22. Image 734MB. |
| No secrets in the image | No `.env*` file anywhere outside third-party packages, none of `planning`, `test`, `tests`, `.git`, no `sk-or-` string in `/app/app` or `/app/static`, no key in the image env or history. A later build with a project `.env` present also left none in the image. |
| Non-root on a fresh volume | Runs as `finally` (uid 1000). Created `/app/db/finally.db` on new named volumes. |
| E2E against the container, `LLM_MOCK=true`, new volume, `E2E_REQUIRE_FRESH=1` | 27 passed, on the clean-checkout image and again on the deployed image. No errors or warnings in the container log. |
| Persistence through the scripts | After a trade, cash and position were identical after a replace by `start_mac.sh`, and after `stop_mac.sh` then `start_mac.sh`. Chat history also survived. The test volume was removed before the final deployment. |
| Shutdown with an SSE client attached | `docker stop` 3.4s, exit 0, `Application shutdown complete`. `stop_mac.sh` 3.6s. With no client, 0.4s. |
| Idempotency | Start twice replaces the container. Stop twice exits 0 both times. Build-if-absent and `--build` both work from the real path with spaces. |
| Port conflict on the default 8000 | Clear error naming `FINALLY_PORT`, exit 1, nothing changed. A running `finally` on another port is left alone. `pm-pm-1` kept the same container id and start time throughout. |
| No API key | App starts and is healthy, chat replies with the `LLM not configured` guidance and no actions. |
| Missing frontend warning | With `STATIC_DIR` pointing nowhere, the warning prints in the container log, ahead of uvicorn's startup lines. |
| Backend suite after the `main.py` edit | 521 passed (local Python 3.14 venv). |
| Git ignore | `.env`, `.env.*`, `backend/.coverage`, `frontend/out`, `.DS_Store`, `db/finally.db*`, and any `*.db` are ignored. `.env.example`, `db/.gitkeep`, `backend/app/db/*` and `frontend/src/lib/*` are visible. |

### Defects found and fixed

1. **The container crashed on start: `PermissionError` on `/app/app/__init__.py`.** Some backend source files are mode 0600 on disk, and `COPY` keeps host modes, so the non-root user could not read them. The Dockerfile now runs `chmod -R a+rX` on `/app/app` and `/app/static`.
2. **Plain `docker stop` killed the app at about 3s, with exit 137.** On this Docker, a container without its own stop timeout is killed about 3s after SIGTERM, not the documented 10s. That ties with uvicorn's 3s deadline, and uvicorn lost: no lifespan shutdown ran. This looks fast, so timing alone would have passed it. The scripts now use `docker run --stop-timeout 10` and `docker stop -t 10`, giving exit 0. I did not find why the daemon's default is about 3s. A bare `docker stop` on a container started without `--stop-timeout` can still be killed this way. No data risk was seen, per defect 3 above.

### Not verified

- **Windows scripts:** `pwsh` is not installed here, so `start_windows.ps1` and `stop_windows.ps1` have never been run, or even parsed.
- **Browser opening:** every start used `--no-open`, so the `open` path in `start_mac.sh` has not run.
- **Linux hosts and x86-64 builds:** only macOS on arm64 was tested.
- **Real LLM and real Massive API:** still not called.

## For DevOps

- Run the suite against the container with `E2E_BASE_URL=http://localhost:<port> E2E_REQUIRE_FRESH=1 test/run_e2e.sh` on a **new volume**, with the container started with `LLM_MOCK=true`.
- **Do not point the suite at a volume you care about:** specs sell all positions and change the watchlist.
- The default run writes screenshots to `$TMPDIR/finally-e2e/screenshots`. The `99-screenshots` spec adds about 19s.
- `frontend/out/` is gitignored and must be built in the image.
- Add `--host 0.0.0.0` as well as the shutdown flag.
- `$TMPDIR` differs inside and outside the sandbox on this machine. Passing `TMPDIR` and `PLAYWRIGHT_BROWSERS_PATH` explicitly avoids a second browser download.

## Reproduce

Set `TMPDIR` to a local path, keep node_modules out of the project tree, and run from the project root:

```bash
# Backend, including integration tests
cd backend && UV_CACHE_DIR="$TMPDIR/uv-cache" uv run --frozen pytest

# Same on Python 3.12
UV_CACHE_DIR="$TMPDIR/uv-cache" UV_PROJECT_ENVIRONMENT="$TMPDIR/venv312" uv run --frozen --python 3.12 pytest

# Frontend, in a copy outside the project
rsync -a --exclude node_modules --exclude .next --exclude out frontend/ "$TMPDIR/fe/"
cd "$TMPDIR/fe" && npm ci && npx vitest run && npx tsc --noEmit && npx eslint . && npm run build

# App, from backend/, on a fresh database (needs local port binding)
LLM_MOCK=true DB_PATH="$TMPDIR/e2e/finally.db" STATIC_DIR="<abs path to frontend/out>" \
  uv run --frozen uvicorn app.main:app --port 8010

# Browser E2E, in another shell; copies test/ to $TMPDIR, installs Playwright and Chromium
E2E_REQUIRE_FRESH=1 E2E_BASE_URL=http://localhost:8010 test/run_e2e.sh
```

Browser downloads need `registry.npmjs.org`, `cdn.playwright.dev` and `playwright.download.prss.microsoft.com`. Playwright also tried `storage.googleapis.com` here, so allow it too.
