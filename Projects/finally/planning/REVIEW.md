# FinAlly — Project Review

_Reviewer agent, 2026-10-30. Scope: everything in `Projects/finally/` (CLAUDE.md, `planning/`, `.claude/`), plus repo-level git state that affects it. There is still no application code. The root-level `finally/` folder and git history are not authoritative: the project is being rebuilt from scratch here. Items already listed in PLAN.md §13 are not repeated unless this review adds something new._

Severity: **Critical** = could leak secrets or lose work now. **High** = agents will build the wrong thing or fail to build. **Medium** = inconsistency or guesswork risk. **Low** = cleanup.

What changed since the 2026-10-29 review: two local commits. `3d54958` added the planning docs and REVIEW.md, and also committed the root `.env` and the old root `finally/` copy. `081c577` added a root `.gitignore` (which ignores `.env`) and removed `.env` from the tree. Nothing in `CLAUDE.md`, `planning/PLAN.md`, `planning/MARKET_DATA_SUMMARY.md`, `planning/archive/` or `.claude/` changed after the previous review was written.

---

## Status of prior findings (2026-10-29)

| # | Finding | Status | Notes |
|---|---------|--------|-------|
| 1 | `.env` untracked and not git-ignored | **Partial** | The root `.gitignore` now ignores `.env` (verified with `git check-ignore`). But `Projects/finally/.gitignore` was not restored, and the root file is a Python template: it does **not** ignore `node_modules/`, `.next/`, `out/`, `*.db` or `static/`. The `.env` was also committed before being ignored (see N1). |
| 2 | `.env` in the wrong place, holds unrelated credentials | Open | It is still at the git root, still holds the Atlassian and Confluence keys, and still has no `LLM_MOCK`. There is no `Projects/finally/.env` and no `.env.example`. |
| 3 | §9 names the `cerebras-inference` skill, which is actually `cerebras`. §13 A2 is wrong | Open | PLAN lines 296 and 307 still say `cerebras-inference`. A2 still claims the skill is deleted. |
| 4 | The cerebras skill uses blocking `completion`, has no timeout, allows silent provider fallback, and has non-strict schemas | Open | SKILL.md unchanged. |
| 5 | `MARKET_DATA_SUMMARY.md` describes non-existent code in the past tense | Open | Still says "Complete, tested… 73 tests". |
| 6 | The archived design contradicts the summary (lazy `massive` import, `DEFAULT_CORR`, `-> None`) | Open | The archive is unchanged (e.g. `DEFAULT_CORR` at MARKET_DATA_DESIGN.md:342 and the lazy import at :680). |
| 7 | The reviewer agent is told to write PLAN.md | Open | `.claude/agents/reviewer.md` is unchanged, typos included. This run again left PLAN.md untouched. |
| 8 | Two competing review workflows; "feedbackto" typo | Open | |
| 9 | `.claude/settings.json` deleted | Open, low impact | The old file only enabled 3 plugins (frontend-design, context7, playwright), so nothing important was lost. Recreate it if you want those plugins pinned per project or want a `uv`/`npm`/`docker` allowlist. Otherwise close it. |
| 10 | CLAUDE.md headings inverted; stale §13 auto-loaded | Open | |
| 11 | SSE payload (`change_percent`, timestamp unit, `retry:`) not pinned | Open | |
| 12 | SSE is change-driven; status dot / heartbeat | Open | |
| 13 | §13 item 5 is half-decided by the design | Open | |
| 14 | `agent-browser` vs Playwright | Open | |
| 15 | README, LICENSE and CI workflows deleted | Open | |
| 16 | `db/.gitkeep` missing / ignore rule | Open | The `db/` directory doesn't exist yet. |
| 17 | `include_router` inside lifespan in the design | Open | |
| 18 | `reasoning_effort="low"` not stated in §9 | Open | |

**Totals: 0 resolved, 1 partial, 17 open.**

---

## New findings

### Critical

#### N1. The `.env` with live secrets is in local git history
- Commit `3d54958` added the root `.env`: 6 lines, namely `OPENROUTER_API_KEY`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_SPACE_KEY` and `MASSIVE_API_KEY`. `081c577` deletes it from the tree, but the blob is still in history.
- `main` is **ahead of `origin/main` by 2 and not pushed yet**, so nothing has leaked to GitHub. The next `git push` will publish all three tokens.
- **Fix before any push:** rewrite the two local commits so that neither contains `.env`. For example, run `git reset --soft origin/main`, confirm `.env` is not staged, then recommit. Afterwards, check that `git log origin/main..HEAD --all -- .env` prints nothing.
- If this history was ever pushed or shared, rotate the OpenRouter, Atlassian and Massive keys.

### High

#### N2. The old project copy is now tracked at the root `finally/` and will pull agents off the fresh-start path
- `3d54958` committed 39 files under the root `finally/`. They include a working `backend/app/market/*` with tests, a separate `CLAUDE.md`, `.claude/settings.json`, and a `cerebras` skill.
- `MARKET_DATA_SUMMARY.md` gives the exact import path (`from app.market import PriceCache, …`) and calls the code "complete". An agent that greps the repo for `PriceCache` will find this copy and import or copy from it, which contradicts the from-scratch decision.
- PLAN §13 A1 still offers "restore the market data code" as an option. That option conflicts with the decision.
- **Fix:** add one line to `Projects/finally/CLAUDE.md`: "Build everything under `Projects/finally/` from scratch. Do not read, import or copy from the repo-root `finally/` folder or from git history." Reword §13 A1 to "rebuild per the summary". Optionally, untrack the root `finally/` folder.

#### N3. Only the chat response is specified; the rest of the REST contract is not
- §13 item 11 pins `POST /api/chat`. Nothing pins the response bodies for `GET /api/portfolio`, `POST /api/portfolio/trade` (success **and** failure), `GET /api/portfolio/history`, `GET/POST/DELETE /api/watchlist`, or `/api/health`. Nothing pins the error envelope or status codes either: FastAPI's default is `{"detail": …}`, and 400 vs 422 for validation errors is undecided.
- Frontend and backend agents will build in parallel against guessed shapes. That is the most likely integration failure.
- **Fix:** add an "API contract" subsection to §8 with one JSON example per endpoint and a single error shape. For example, `{"error": "insufficient_cash", "message": "..."}` with 400 for business-rule failures and 422 left to FastAPI for schema errors. Alternatively, have the backend agent publish `planning/API.md` before frontend work starts.

#### N4. No agent roster, build order, or definition of done
- §1 says "agents interact through files in `planning/`" and §4 mentions Frontend Engineer, Backend and Market Data agents. But `.claude/agents/` contains only `reviewer.md`, and nothing defines who owns what, in what order, or how hand-off is signalled.
- **Fix:** add a short §14 "Build plan". It should list the agents (market data, backend API/DB, LLM, frontend, Docker/scripts, E2E), their owned directories, the order (market data, then backend + API contract, then frontend, then Docker, then E2E), and a done-check per stage (for example "`uv run pytest` green" or "`curl /api/health` returns 200 in the container"). Add the matching `.claude/agents/*.md`.

### Medium

#### N5. The frontend dev loop is undefined
- In production, the frontend is a static export on the same origin. During development, `next dev` serves on :3000 while FastAPI is on :8000, so relative `/api/*` fetches and `new EventSource('/api/stream/prices')` miss the backend. Next.js `rewrites` are not supported with `output: 'export'`.
- **Fix:** pick one approach and document it. Either (a) a `NEXT_PUBLIC_API_BASE` env var (empty in production, `http://localhost:8000` in dev) plus a dev-only CORS allowlist for `http://localhost:3000` in FastAPI, or (b) frontend agents always test against a built export served by the backend.

#### N6. The database location is contradictory, and the relative path collides with `backend/db/`
- §11 runs `-v finally-data:/app/db`, which is a **named** volume, then says "the `db/` directory in the project root maps to `/app/db`". Only a bind mount does that. With the named volume, the host `db/` (and `db/.gitkeep`) is never used.
- When run locally (`cd backend && uv run uvicorn …`), the relative default `db/finally.db` resolves to `backend/db/finally.db`, which is inside the schema-code directory from §4.
- **Fix:** state that Docker uses the named volume and that the host `db/` is only for local runs. Resolve `DB_PATH` (§13 item 20) to an absolute path anchored at the project root, not at the current working directory. Adopting §13 item 31 (`backend/app/db/`) removes the name clash.

#### N7. Dependencies are not pinned and there is no lockfile policy for LiteLLM
- §11 says `uv sync` "from lockfile", but there is no `uv.lock` yet and no stated pin policy. LiteLLM moves fast and has had compromised PyPI releases reported (March 2026). It is also heavy for a slim image.
- **Fix:** pin `litellm` to a vetted exact version, commit `uv.lock`, and use `uv sync --frozen --no-dev` in the Dockerfile. Do the same with `package-lock.json` and `npm ci` for the frontend stage.

#### N8. §13's 33 open items are now the bottleneck
- Nothing in PLAN.md changed in the last day. Every agent session still loads all of §13 through `@planning/PLAN.md`, including the wrong A2. Some agents will treat each "Suggested" as decided, and others won't.
- **Fix:** the owner accepts the suggestions as a batch, with explicit overrides only where they disagree, and folds them into §§5–12. Known conflicts to settle while doing so:
  - item 17 omits `change_percent` (prior #11);
  - item 29 ("defer Massive") contradicts the summary's "`massive` is a core dependency" (prior #6);
  - item A1's "restore" option (N2).

### Low

- **N9. Docker details.** `python:3.12-slim` has no `curl`, so a `HEALTHCHECK` must use `python -c "import urllib.request…"` or install curl. `docker run --env-file .env` fails hard if `.env` is missing, so the start scripts should pass it only when the file exists. That fits §13 item 19.
- **N10. LLM-initiated watchlist changes need the same validation as manual ones.** §9 says this for trades but not for `watchlist_changes`. Apply the §13 item 5 symbol rule. Also cap the watchlist size (for example 50): the simulator rebuilds a Cholesky matrix on every add, and an LLM loop could add many tickers.
- **N11. Ignore rules for the project.** When restoring `Projects/finally/.gitignore` (prior #1), include `node_modules/`, `.next/`, `out/`, `backend/static/`, `.venv/`, `db/*` + `!db/.gitkeep`, `test-results/` and `playwright-report/`.

---

## Suggested order of action
1. **N1:** scrub `.env` from the two unpushed commits **before any `git push`**.
2. **N2:** add the "don't use root `finally/`" guard to CLAUDE.md. Then prior #3, #5 and #7, which are one-line doc fixes.
3. **N8:** settle §13 in one pass. Fold in prior #4, #6, #11 and #12, plus N3 (API contract) and N6 (DB path).
4. **N4:** write the build plan and agent definitions, then start the backend agent.
