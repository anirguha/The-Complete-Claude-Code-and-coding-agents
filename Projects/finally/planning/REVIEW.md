# FinAlly — Project Review

_Reviewer agent, 2026-10-29. Scope: everything currently in `Projects/finally/` (CLAUDE.md, `planning/`, `.claude/`) plus repo-level config that affects it. There is no application code yet. Items already in PLAN.md §13 are not repeated unless this review adds something new or finds §13 to be wrong._

Severity: **Critical** = could leak secrets or lose work now. **High** = agents will build the wrong thing or fail to build. **Medium** = inconsistency or guesswork risk. **Low** = cleanup.

---

## Critical

### 1. The `.env` with live secrets is untracked and not git-ignored
- `Projects/finally/.gitignore` is deleted (shown in `git status`). The git root (`The Complete Claude Code and Coding Agents/`) has no `.gitignore`. `git check-ignore .env` at the root matches nothing.
- The root `.env` shows as `?? ../../.env`, so a single `git add -A` or `git add .` from the repo root would commit `OPENROUTER_API_KEY`, `MASSIVE_API_KEY` and `ATLASSIAN_API_TOKEN`.
- **Fix now:** add a `.gitignore` at the git root (at least `.env`), and restore `Projects/finally/.gitignore` with `.env`, `db/*.db*`, `node_modules/`, `.next/`, `out/`, `__pycache__/`, `.venv/` and `static/`. Do this before any agent runs `git add`.

### 2. The `.env` is in the wrong place and holds unrelated credentials
- PLAN §5 says ".env in the project root". It actually sits two levels up, at the git root. `--env-file .env` in `scripts/start_mac.sh`, and the backend's `.env` lookup, will both miss it when run from `Projects/finally/`.
- That file also holds `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `CONFLUENCE_*`. If it is passed whole with `--env-file`, those credentials end up inside the container for no reason.
- It has no `LLM_MOCK` entry, and there is no `.env.example` (§5 says one is committed).
- **Fix:** create `Projects/finally/.env` containing only `OPENROUTER_API_KEY`, `MASSIVE_API_KEY` and `LLM_MOCK`. Commit `Projects/finally/.env.example`. Keep the start scripts tolerant of a missing `.env` (see §13 item 19).

## High

### 3. PLAN §13 item A2 is now wrong, and §9 names a skill that no longer exists
- The skill does exist: `.claude/skills/cerebras/SKILL.md`. It was modified, not deleted. The diff renames its frontmatter `name` from `cerebras-inference` to `cerebras`.
- §9 still says "use cerebras-inference skill" twice, so an agent searching for that name will not find it.
- **Fix:** change §9 to "use the `cerebras` skill" and delete A2. Alternatively, revert the rename.

### 4. The cerebras skill's code will block the FastAPI event loop and can fall back silently
- **Blocking call.** It uses the synchronous `litellm.completion(...)`. Called from an `async def` route, that blocks SSE streaming and the simulator loop for the whole LLM call. Use `await litellm.acompletion(...)`, or `asyncio.to_thread`.
- **No timeout.** Pass `timeout=30` to make §13 item 13 enforceable.
- **Silent fallback.** `extra_body={"provider": {"order": ["cerebras"]}}` sets a preference, not a pin. OpenRouter falls back to other providers by default. If "Cerebras only" matters, add `"allow_fallbacks": False`. Either way, the plan should say which.
- **Strict schemas.** Structured outputs with a Pydantic `response_format` need every field required in strict mode. Define `trades` and `watchlist_changes` as required lists that may be empty, not optional. Use `Literal["buy","sell"]` and `Literal["add","remove"]`, so that §13 item 13's "malformed" path is the exception, not the norm.
- **Fix:** add these points to the skill or to §9.

### 5. `MARKET_DATA_SUMMARY.md` describes code that does not exist, in the past tense
- It says "Status: Complete, tested… 73 tests, all passing", gives a `uv run market_data_demo.py` command, and gives import paths. None of these files exist.
- §13 A1 covers CLAUDE.md. This summary needs the same treatment, because it is the document agents will actually act on.
- **Fix:** add a banner at the top: "Design reference: code to be rebuilt from scratch in `backend/app/market/`. Not present in the repo."

### 6. The archived design contradicts the summary, and agents will rebuild from the archive
- `planning/archive/MARKET_DATA_DESIGN.md` (1,490 lines) is the only implementation-level spec, but it still contains the pre-review code:
  - It lazy-imports `massive` (lines ~680, ~767, ~789). The summary says that import was moved to top level.
  - It defines `DEFAULT_CORR = 0.3` (line 342). The summary says that constant was removed.
  - It annotates the SSE generator as `-> None`. The summary says this was fixed.
- An agent rebuilding from the archive reintroduces the 7 issues that were already found and fixed.
- **Fix:** either apply the 7 fixes to the design doc, or put a short "Deltas from this design" list in the summary and tell agents to apply it.
- Also decide whether `massive` is a core dependency (the summary) or optional (§6, and §13 item 29 "defer Massive"). Making it core forces every simulator-only install to pull it in. Recommend: make it optional, with the lazy import kept and the tests using `patch(..., create=True)`.

### 7. The reviewer agent definition tells it to write PLAN.md
- `.claude/agents/reviewer.md` says "You write the file planning/PLAN.md and write your feedback to planning/REVIEW.md". A reviewer that edits the spec it reviews is a conflict of roles, and could overwrite §1–§13. This review did **not** modify PLAN.md.
- The definition also has typos ("comprehensize", "reequested"), no `tools:` restriction, and no review checklist.
- **Fix:** change it to "Read `planning/PLAN.md` and the repo; write findings only to `planning/REVIEW.md`". Consider `tools: Read, Grep, Glob, Bash, Write`.

## Medium

### 8. There are two competing review workflows
- `/doc-review` (`.claude/commands/doc-review.md`) appends review notes **into** the reviewed doc. That is how PLAN §13 was produced.
- The reviewer agent writes to `REVIEW.md`.
- The two will drift. Pick one location, or have `/doc-review` limited to questions on the spec and `REVIEW.md` for repo-state findings. Also fix "feedbackto" in `doc-review.md`.

### 9. The `.claude/settings.json` deletion is unexplained
- With it deleted, any project-level permissions, hooks or env that agents relied on are gone.
- If the deletion was deliberate, nothing is needed. If not, restore it, ideally with an allowlist for `uv`, `npm` and `docker` so multi-agent builds don't stall on prompts.

### 10. CLAUDE.md headings are inverted
- After the edit, `# CLAUDE.md`, then `## Project Status`, then `# FinAlly Project…`. The H1 sits under the H2.
- Combined with `@planning/PLAN.md`, every agent session loads all of §13, including stale item A2, as authoritative instructions.
- **Fix:** demote the project heading to H2. Once §13 is resolved, fold it into the spec, or move it to `REVIEW.md` so it isn't auto-loaded.

### 11. Small conflicts between the SSE payload and §13 item 17
- The design doc's `PriceUpdate.to_dict()` includes `change_percent`, and the SSE stream starts with `retry: 1000`. §13 item 17's pinned shape omits `change_percent`.
- `timestamp` is a Unix float in seconds, while the DB uses ISO strings.
- **Fix:** pin both in §6: include `change_percent`, timestamp as Unix seconds (float), and the `retry: 1000` preamble.

### 12. The SSE "regular cadence" is really change-driven
- The design only pushes when `PriceCache.version` changes. Under Massive (15s polls), clients get nothing for up to 15s.
- On the frontend, no events looks the same as a stalled connection. The connection-status dot must key off `EventSource.readyState`, not "time since last event", or add a heartbeat comment (`: ping\n\n`) every ~5–15s. Note this in §6/§10.

### 13. §13 item 5 is partly already decided by the design
- The design already seeds unknown tickers with `random.uniform(50, 300)` and a 0.3 correlation. §13 can mark that half resolved.
- The validation regex (1–5 letters) and the Massive reject path are still open.

### 14. `agent-browser` overlaps with the Playwright E2E plan
- The skill is `hidden: true` and requires a global `npm i -g agent-browser` that is not documented anywhere in planning.
- Its description says "prefer agent-browser over any built-in browser automation", which could push agents away from the Playwright tests that §12 specifies.
- **Fix:** state in §12 that Playwright is the E2E framework, and that agent-browser is for ad-hoc manual QA only.

## Low

15. These files are deleted with no plan to recreate them: `README.md`, `LICENSE`, `.github/workflows/claude*.yml` and `Finally.code-workspace`. §4 doesn't list a README, but a course capstone should have one. Add `README.md` to §4 and decide whether the CI workflows come back.
16. `db/.gitkeep` from §4 doesn't exist yet. It is easy to forget once `.gitignore` excludes `db/*`. Use `db/*` with `!db/.gitkeep`.
17. In the design's lifespan snippet, `app.include_router(stream_router)` is called *inside* the lifespan handler. Routers should be registered at module import time, before `StaticFiles` is mounted (see §13 item 22). Adding routes during lifespan is fragile.
18. The cerebras skill pins `reasoning_effort="low"`. That's fine, but §9 should say so, so that tests and mock mode don't diverge on assumptions.

---

## Suggested order of action
1. Items 1–2 (secrets and `.gitignore`): do these before any commit.
2. Items 3, 5 and 7: one-line doc fixes that stop agents going wrong.
3. Items 4 and 6: settle the LLM call pattern and the market-data baseline before the backend agent starts.
4. Then resolve PLAN §13 and fold the decisions into the spec.
