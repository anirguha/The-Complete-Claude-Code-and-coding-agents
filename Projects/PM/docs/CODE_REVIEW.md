# Code Review

Date: 2026-10-26. Scope: the whole `PM` folder at commit `0770a3a` (backend, frontend, Docker, scripts, tests, docs).

## Summary

The codebase is small, readable, and close to the standards in `AGENTS.md`. The board model is validated in one place (Pydantic `Board`), saves are transactional, AI output goes through the same validation as user edits, and errors are surfaced in the UI. The main correctness risk is a lost-update race between AI chat and manual edits. The rest are small bugs, documentation drift, and hygiene items.

Checks run during the review:

| Check | Result |
| --- | --- |
| `uv run pytest` (backend) | 17 passed |
| `npm run test:unit` | 10 passed |
| `npm run lint` | clean |
| `npm run build` | static export succeeds |
| `npx tsc --noEmit` | 40 errors, all in test files (see L4) |
| `npm audit` | 23 findings total; 6 in production deps (1 critical, 4 high, 1 moderate) |
| Playwright e2e | not run |

Findings marked "Verified" were reproduced with a probe script against the FastAPI app; the others come from reading the code.

## Resolution status

H1 and M1-M6 are fixed. Each fix has a regression test; low-severity items remain open.

- H1: `POST /api/chat` now applies the AI's actions to the latest saved board inside one `BEGIN IMMEDIATE` transaction (`database.update_board`). If a concurrent edit removed something an action needs, it returns 409 and saves nothing. The frontend reloads the board after pending saves finish instead of trusting the chat response board.
- M1: credentials are compared as bytes.
- M2: `api.ts` only uses `detail` when it is a string; the new-card form enforces the same length limits as the API.
- M3: column titles commit once on Enter or blur; Escape reverts.
- M4: unknown `/api/*` paths return 404.
- M5: `PUT /api/board` returns 400 if column IDs or their order change.
- M6: Compose publishes on `127.0.0.1` only and no longer has a default session secret (an unset secret falls back to a random per-process value).

## High

### H1. AI chat overwrites edits made while the AI request is in flight

`backend/app/main.py:98-101` loads the board, awaits the OpenRouter call (up to 45 s), then saves the AI result built from the board as it was at the start. Any `PUT /api/board` that lands in that window (drag, rename, add, delete) is silently discarded in the database. The frontend does the same thing: `AIChatSidebar` calls `onBoardChange={setBoard}` (`frontend/src/app/page.tsx:154`) with the returned board, replacing whatever the user changed meanwhile.

Repro: send a chat message, and while "Thinking..." is shown, drag a card to another column. When the reply arrives the card moves back, and it stays back after reload.

Simplest fix: re-load the board after the AI call and apply the actions to that fresh board (actions are ID-based, so they rebase well), or disable board editing while a chat request is in flight. Either needs a test.

## Medium

### M1. Non-ASCII login input returns HTTP 500 (Verified)

`hmac.compare_digest` raises `TypeError` for `str` arguments that contain non-ASCII characters (`backend/app/main.py:58-59`). Logging in with username `usér` returns 500 instead of 401. Fix: compare `.encode()` bytes.

### M2. Validation errors display as "[object Object]" (Verified)

FastAPI returns `detail` as a list of objects for 422 responses. `frontend/src/lib/api.ts:30` passes it straight to `new Error(...)`, so the user sees `[object Object]`. This is reachable: `NewCardForm` has no `maxLength` on title/details (`frontend/src/components/NewCardForm.tsx:27-44`), unlike the edit form, so a 201-character title triggers it. Fix: add `maxLength={200}` / `maxLength={5000}` to the new-card inputs, and only use `detail` when it is a string.

### M3. Column rename saves on every keystroke

`ColumnTitleInput` calls `onCommit` from `onChange` (`frontend/src/components/KanbanColumn.tsx:30-34`), so typing a 10-character title sends 10 full-board `PUT` requests. Escape does not revert because each keystroke has already been committed. Committing on blur/Enter (and reverting on Escape) is simpler and matches the user's intent.

### M4. Unknown `/api/*` GET paths return the HTML app with 200 (Verified)

The catch-all route (`backend/app/main.py:105-116`) falls back to `index.html` for any missing file, including `/api/does-not-exist`. API clients and debugging get a 200 HTML page instead of a 404. Fix: raise 404 when `path` starts with `api/`.

### M5. "Fixed columns" is not enforced by the API (Verified)

The business requirement says columns are fixed and can only be renamed. `PUT /api/board` accepts any set of columns; a request that drops four columns and adds a new one succeeds. The UI never does this, so the risk is limited to direct API calls, but the invariant is cheap to enforce: reject a board whose column IDs differ from the stored board's.

### M6. Container is reachable from the network with known credentials and a known default secret

`docker-compose.yml` publishes `"8000:8000"`, which binds on all interfaces, and falls back to `SESSION_SECRET=local-development-secret-change-me` when `.env` lacks it. Combined with the fixed `user` / `password`, anyone on the same network can use the board (and spend the OpenRouter key through `/api/chat`), and session cookies can be forged with the public default secret. For a local-only MVP, bind to `"127.0.0.1:8000:8000"` and drop the default secret (the app already generates a random one per process when it is unset).

## Low

### L1. Broken Tailwind class on the board header

`frontend/src/components/KanbanBoard.tsx:121` has `shadow sm:p-8-[var(--shadow)]`, which looks like a merge of `sm:p-8` and `shadow-[var(--shadow)]`. Neither the larger padding nor the custom shadow is applied. Should be `sm:p-8 shadow-[var(--shadow)]`.

### L2. A 401 after the session expires leaves the user stuck

Only the initial load maps `"Please sign in."` to the sign-in screen (`frontend/src/app/page.tsx:38-42`), and it does so by matching the error message text. If the session cookie becomes invalid later (for example after a container restart without `SESSION_SECRET`), saves fail, the reload fails, and `logout` itself requires auth and fails with 401 (`backend/app/main.py:73-78`), so the Sign out button only shows an error. Suggest: let `logout` work without a valid session, and have `api.ts` expose the status code so a 401 anywhere returns to the sign-in screen.

### L3. Failed save does not cancel later queued saves

`handleBoardChange` (`frontend/src/app/page.tsx:86-109`) chains saves. If save A fails, the catch reloads the server board, but save B (queued before the failure, built on A's state) still runs afterwards and can re-apply part of the rejected change. Low impact because the server validates every board; worth knowing if the queue logic changes.

### L4. TypeScript does not know the Vitest globals

`src/test/vitest.d.ts` references `vitest`, which does not declare `describe`/`it`/`expect` as globals. `npx tsc --noEmit` reports 40 errors in the three test files. `next build` and Vitest still pass, so this only affects editors and any future typecheck step. Fix: reference `vitest/globals` instead.

### L5. Keyboard users cannot move cards

Only `PointerSensor` is registered (`frontend/src/components/KanbanBoard.tsx:35-39`). Adding `KeyboardSensor` with `sortableKeyboardCoordinates` is a two-line change that makes drag-and-drop accessible.

### L6. Writes on every read

`load_board` calls `_ensure_board` (`backend/app/database.py:121-134, 166`), so every `GET /api/board` runs two `INSERT OR IGNORE` statements and a commit. Seeding already happens at login; reads could skip it. Minor, but it also means a GET can fail with "database is locked" under contention.

### L7. Playwright tests share a persistent database

`frontend/playwright.config.ts` uses a fixed `/tmp/pm-kanban-playwright.db` that is never cleaned and `reuseExistingServer` outside CI. The rename and move tests change persistent state, so later runs start from a different board (card-1 is already moved, the column is already "Queued"). `CLAUDE.md` describes this as a temp DB; it is not reset between runs. Delete the file in a global setup or use a unique path per run.

### L8. Uncontrolled mode in `KanbanBoard` exists only for tests

`KanbanBoard` keeps a `localBoard` seeded from `initialData` (`frontend/src/components/KanbanBoard.tsx:23-32`) and always writes to it even when controlled. Production always passes `board`. This duplicates the seed data in `frontend/src/lib/kanban.ts` and `backend/app/database.py`, and `cardsById` (`useMemo` of `board.cards`) adds nothing. Tests could render the component with a `board` prop and a state wrapper instead.

### L9. Small backend items

- `apply_actions` silently skips actions with an empty `type` (`backend/app/ai.py:76-78`) even though the schema enum forbids it; raising would be consistent with the rest of the function.
- The invalid-response log line includes up to 2000 characters of the provider body (`backend/app/ai.py:199-204`), which contains board content. Acceptable locally; worth trimming if logs are ever shipped.
- `pydantic` is imported directly but only installed transitively through FastAPI (`backend/pyproject.toml`). Declare it.
- The local `.venv` runs Python 3.14 while Docker uses 3.12; pin with a `.python-version` file so tests match the image.
- `fastapi.testclient` emits a Starlette deprecation warning about `httpx`; harmless now, will need attention on upgrade.

### L10. Small frontend items

- `createId` uses `Math.random` (`frontend/src/lib/kanban.ts:164-168`); `crypto.randomUUID()` is simpler and collision-safe.
- `"start": "next start"` in `package.json` does not work with `output: "export"`; remove it.
- Header copy "One board. Five columns. Zero clutter." and the column count are hard-coded rather than derived from the board.
- `frontend/public/*.svg` are unused create-next-app leftovers.
- `@types/node` is `^20` while the build image is Node 22.
- `next/font/google` downloads fonts at build time, so `docker compose up --build` needs internet access.

### L11. Docker and scripts

- `docker-compose.yml` repeats `DATABASE_PATH`, `STATIC_ROOT`, and `PYTHONPATH`, which the Dockerfile already sets.
- The container runs as root and has no `HEALTHCHECK`, although `/api/health` exists.
- The Mac and Linux scripts are identical; that is fine for discoverability, just keep them in sync.

## Dependencies

`npm audit` reports 23 findings (14 high, 4 critical), 6 of them in production dependencies, including `next` 16.1.6 and `sharp`. Because the app ships as a static export and Next.js does not run as a server in production, most `next` server-side advisories do not apply at runtime, but they do apply to `npm run dev`. Upgrading `next` and `eslint-config-next` to the latest 16.x patch is the low-risk step; this matches the "latest versions" standard in `AGENTS.md`. `docs/PLAN.md` already recorded these findings without acting on them.

## Documentation drift

- `docs/DATABASE.md` (last paragraph) and `docs/PLAN.md` Part 9 describe a full-board `board_update` response. The code uses an action list (`rename_column`, `create_card`, `update_card`, `move_card`, `delete_card`). `CLAUDE.md` notes the discrepancy; the docs themselves should be updated.
- `docs/PLAN.md` "Verification status" says 16 backend and 9 frontend tests; there are now 17 and 10.
- `CLAUDE.md` calls the Playwright database a temp DB; see L7.

## Test coverage gaps

Worth adding alongside the fixes above:

- Concurrent chat and board edit (H1).
- Non-ASCII credentials (M1).
- 422 error rendering in the UI (M2).
- Unknown `/api/*` path returns 404 (M4).
- Rejecting added or removed columns (M5).
- 401 mid-session returns to sign-in (L2).
- `move_card` with an explicit `position` and an unknown `column_id` in `apply_actions`.

## What is working well

- One validation path: user edits and AI proposals both become a `Board` and are validated before saving.
- Saves replace the board in a single SQLite transaction with composite foreign keys and cascades, so partial boards cannot be persisted.
- The AI integration uses strict JSON-schema output, ID-based actions, a bounded history, and a timeout, and every failure mode returns a clear error without touching the board.
- The static-file route correctly blocks path traversal.
- Secrets stay out of the image (`.dockerignore`, runtime env only), and the API key is never echoed in errors.
- Frontend code is small, typed, and consistent; Testing Library tests use accessible queries.
