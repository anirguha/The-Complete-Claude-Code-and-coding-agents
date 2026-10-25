# Project Management MVP delivery plan

## Decisions

- Run the Next.js frontend as a static export served by FastAPI from the same origin.
- Store SQLite data in the named Docker volume `pm-data`, mounted at `/app/data`. Stopping or recreating the application container does not remove the volume.
- Read `OPENROUTER_API_KEY` from the project-root `.env` through Docker Compose runtime environment interpolation. Never copy `.env` into the image. The AI feature returns a visible service error when the key is missing.
- Use the fixed local MVP credentials `user` / `password`; persist the user and board separately so the schema can support more users later.
- If an AI request, structured response, or proposed board is invalid, abort the operation and return an error. Do not save a partial or invalid board.
- Build the FastAPI health/API scaffold first, then add the static Next.js export to the same image in Part 3. The finished app has one FastAPI origin for both static files and `/api`; no throwaway static page is needed. Part 7 then replaces the UI's demo-state source with the persistent API. This keeps the transitions explicit and independently testable.

## Part 1: Plan and existing frontend

- [x] Review the existing demo board, components, styling, unit tests, and browser tests.
- [x] Document the implementation sequence, acceptance criteria, test coverage, persistence, secret handling, AI failure policy, and phase transitions here.
- [x] Document the frontend's current structure and conventions in `frontend/AGENTS.md`.

**Tests:** Existing frontend unit and browser tests are retained and extended in later parts.

**Success criteria:** The plan identifies the files/surfaces, key decisions, observable success conditions, and tests for every delivery phase.

## Part 2: Docker, FastAPI, and scripts

- [x] Create a Python backend managed by `uv`, with a health endpoint.
- [x] Add a multi-stage Docker build that builds the static frontend and serves it from FastAPI.
- [x] Add Compose configuration, named database volume, runtime environment variables, and non-secret `.env.example`.
- [x] Add Mac, Linux, and Windows start/stop scripts.
- [x] Serve static files from FastAPI and reject paths outside the static output.

**Tests:** Backend health endpoint test; Compose configuration validation; Docker image build and container smoke test.

**Success criteria:** `docker compose up --build -d` starts one service at `http://localhost:8000`; `/api/health` returns `{"status":"ok"}`; the static site is served at `/`; `docker compose down` leaves `pm-data` intact.

## Part 3: Static frontend

- [x] Configure Next.js static export and disable image optimization that requires a runtime image server.
- [x] Keep the existing Kanban demo board, five columns, drag-and-drop behavior, add/remove cards, and column rename.
- [x] Add inline card editing.
- [x] Retain and extend component and board utility tests.

**Tests:** Frontend unit tests, lint, production static build, and browser tests.

**Success criteria:** The exported site loads at `/`; all five columns display; a user can rename columns, move cards, add cards, edit cards, and remove cards.

## Part 4: Demo sign-in

- [x] Require the fixed `user` / `password` credentials before displaying the board.
- [x] Store authentication in an HTTP-only signed session cookie.
- [x] Provide sign-out and protect board and chat API routes.
- [x] Display authentication and connection errors in the UI.

**Tests:** Backend tests for valid/invalid credentials, protected routes, sign-out, and frontend browser tests for the sign-in gate.

**Success criteria:** Anonymous visitors see the sign-in screen; valid credentials reveal the board; invalid credentials show an error; sign-out returns to the sign-in screen.

## Part 5: Database model

- [x] Define a JSON schema for users, one board per user, ordered columns, and ordered cards.
- [x] Document relational constraints, default seed data, persistence, and board updates in `docs/DATABASE.md`.

**Tests:** Validate the checked-in schema's entities and constraints against the backend model tests.

**Success criteria:** The checked-in schema unambiguously describes the data stored by the backend and matches the SQLite tables.

## Part 6: Backend board API

- [x] Create the SQLite database and tables automatically on startup.
- [x] Create a user's initial board on first sign-in.
- [x] Add authenticated read and replace operations for the user's board.
- [x] Validate card/column references and preserve board updates atomically.

**Tests:** FastAPI tests for initialization, authentication, default board, validation failures, and durable updates after a new database connection.

**Success criteria:** The API returns the signed-in user's persisted board; valid updates survive reload; invalid boards receive a client error and leave the stored board unchanged.

## Part 7: Frontend and backend integration

- [x] Replace the production UI's demo-only state with authenticated API loading and saves.
- [x] Persist rename, drag-and-drop, create, edit, and delete operations through the board API.
- [x] Show API errors and reload the saved board if a write fails.
- [x] Keep local Next.js development pointed at FastAPI while production uses same-origin requests.

**Tests:** Backend API persistence tests, frontend interaction tests, and browser tests against both local development servers.

**Success criteria:** Board changes survive page reload and container restart; the browser uses the same origin in the packaged app.

## Part 8: OpenRouter connectivity

- [x] Call OpenRouter from FastAPI using the configured `OPENROUTER_API_KEY` and `openai/gpt-oss-120b`.
- [x] Return an explicit service error when the key is missing, the provider rejects the request, or the connection fails.

**Tests:** Mocked provider success, HTTP error, and connection failure tests; optional live smoke test with a user-provided key.

**Success criteria:** Provider calls stay server-side; the configured model receives the request; provider failures are visible and do not change the database.

## Part 9: Structured AI board operations

- [x] Include current board JSON, user request, and prior user/assistant turns in each request.
- [x] Require strict structured output containing user-facing text and either a full board update or `null`.
- [x] Validate every proposed board update before saving it atomically.
- [x] Reject malformed or inconsistent responses without changing the board.

**Tests:** Mocked structured-response tests for valid response, update, malformed output, invalid board, and provider errors.

**Success criteria:** Only valid complete board updates persist; invalid AI output produces a visible error and leaves the previous board intact.

## Part 10: AI chat interface

- [x] Add a responsive chat sidebar with conversation history and request state.
- [x] Send the user's conversation to the backend and display the assistant response.
- [x] Apply a successful returned board update to the UI and persisted board.
- [x] Show AI errors and allow the user to retry without losing the draft.

**Tests:** Chat component tests, backend AI route tests, full frontend unit/browser tests, Docker build, and end-to-end container smoke test.

**Success criteria:** A user can chat about the board; assistant updates appear immediately and remain after reload; failed or invalid AI operations show errors and do not partially modify the board.

## Verification status

- Backend: 16 tests passed, including mocked OpenRouter success, malformed output, HTTP failure, connection failure, and board persistence.
- Frontend: 9 unit tests passed; lint and static production build passed.
- Docker: Compose validation and isolated image/container smoke test passed, including a board update persisting across container restart.
- Playwright browser tests were added but could not be run because Chromium was unavailable. Browser downloads reached 100% but did not finish installing in this environment.
- No live OpenRouter request was made. AI provider behavior was tested with mocked responses; the `.env` value was not inspected.
- `npm ci` reported 23 dependency audit findings in the existing frontend lockfile (1 low, 4 moderate, 14 high, 4 critical); dependency versions were not changed as part of this implementation.
