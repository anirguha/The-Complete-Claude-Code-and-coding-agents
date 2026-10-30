# Prelegal Project

## Overview

This is a SaaS product to allow users to draft legal agreements based on templates in the templates directory.
The user can carry out AI chat in order to establish what document they want and how to fill in the fields.
The available documents are covered in the catalog.json file in the project root, included here:

@catalog.json

The current implementation covers PL-8 (V1 technical foundation), PL-9 (AI chat for the Mutual NDA), PL-10 (all document types) and PL-11 (multiple users): users sign up and sign in, chat with AI, which picks one of the 11 supported documents and fills it in, with a live preview and PDF download. Downloaded documents are saved to Confluence and listed under My documents.

## Development process

When instructed to build a feature:

1. Use your Atlassian tools to read the feature instructions from Jira
2. Develop the feature - do not skip any step from the feature-dev 7 step process
3. Thoroughly test the feature with unit tests and integration tests and fix any issues
4. Submit a PR using your github tools

## AI design

When writing code to make calls to LLMs, use your Cerebras skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. You should use Structured Outputs so that you can interpret the results and populate fields in the legal document.

There is an OPENROUTER_API_KEY in the .env file in the project root. Saving documents to Confluence also needs ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN, CONFLUENCE_URL (e.g. https://guhaa1.atlassian.net/wiki) and CONFLUENCE_SPACE_KEY (SCRUM, the Prelegal space) there; without them the app works but cannot save documents. `.env.example` lists every setting.

## Technical design

The entire project should be packaged into a Docker container.  
The backend should be in backend/ and be a uv project, using FastAPI.  
The frontend should be in frontend/  
The database should use SQLLite, allowing for a users table with sign up and sign in. Since PL-11 it persists across restarts in the `prelegal-data` Docker volume (tables are created if missing).  
Consider statically building the frontend and serving it via FastAPI, if that will work.  
There should be scripts in scripts/ for:

```bash
# Mac
scripts/start-mac.sh    # Start
scripts/stop-mac.sh     # Stop

# Linux
scripts/start-linux.sh
scripts/stop-linux.sh

# Windows
scripts/start-windows.ps1
scripts/stop-windows.ps1
```

Backend available at http://localhost:8000

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)
- Dark Navy: `#032147` (headings)
- Gray Text: `#888888`

## Implementation Status

### Completed (PL-8) - V1 foundation

- Docker multi-stage build: Next.js static export (Node) + FastAPI backend (Python, uv)
- FastAPI serves the API under `/api` and the exported frontend at `/`, on http://localhost:8000
- SQLite database (`backend/app/schema.sql`) deleted and recreated every time the app starts
- `users` table: id, email (unique), name, password_hash (unused until real auth), created_at
- Fake login (replaced by real accounts in PL-11)
- `AuthGate` sends signed-out users to `/login` and shows a Sign out bar
- Mutual NDA live preview and PDF download (from the prototype; generalised in PL-10)
- Start/stop scripts for Mac, Linux, Windows
- Tests: `cd backend && uv run pytest`, `cd frontend && npm test`

### Completed (PL-9) - AI chat for the Mutual NDA

- The manual NDA form is replaced by a free-form chat beside the live preview
- `POST /api/chat` (`backend/app/routers/chat.py`) calls `openrouter/openai/gpt-oss-120b` on Cerebras via LiteLLM with Structured Outputs
- The AI returns its reply plus a patch of NDA fields (null = unchanged); the backend merges it and returns all the fields
- Stateless: the browser keeps the conversation and sends the history and current fields each turn; nothing is stored
- The system prompt includes today's date and a two-week calendar so relative dates ("next Monday") resolve correctly
- Tests mock the LLM; `uv run --env-file ../.env pytest` also runs a live test against the real model

### Completed (PL-10) - All supported document types

- `documents.json` (project root) defines the 11 documents Prelegal can draft: the catalog's templates, with the Mutual NDA's cover page and standard terms merged into one. Each has its two party roles and its fields (key, label, description for the AI, type `text`/`longtext`/`date`, optional default offered as the usual choice)
- `backend/tests/test_documents.py` checks every `*_link` term in each template is covered by a field label or party role, so `documents.json` stays in sync with the templates
- Drafts are generic: `{documentId, fields: {key: value}, party1, party2}` (`backend/app/documents.py`, `frontend/src/documents/types.ts`)
- The AI picks the document from the conversation (`documentId`, where null keeps the current one) and declines documents that are not supported, suggesting alternatives
- Structured Output models are built per document with `create_model`. When the AI picks or switches a document, the backend starts a blank draft (parties kept) and asks the model again with the new document's fields, so one message can choose and fill in a document
- Frontend: a generic template parser (nested numbered/lettered clauses, heading and term spans) and a generic cover page (key terms + signature table labelled with the party roles) for the preview (`DocumentPreview`) and PDF (`DocumentPdf`). Before a document is chosen, the preview lists the supported documents
- The Dockerfile copies `documents.json` into both build stages

### Completed - The chat asks about every item, one at a time

- The backend works out the items still to ask about, in a fixed order (`items()` / `missing_items()` in `backend/app/documents.py`): both companies, then the document's fields, then each signer's name, title and notice address. The list goes into the prompt
- The AI returns a separate `question` about the next missing item, which the backend appends to its reply; if the AI leaves it empty while items are missing, the backend asks about the next item itself, so every turn ends with a question until all items are filled in or skipped
- Defaults are no longer pre-filled; the AI offers each field's default as the usual choice
- The user can say "skip" (or "not needed") to any question: the AI sets `skipCurrentItem`, and the backend marks the item it last asked about (the first missing one) in `draft.skipped`, so it is not asked again. The preview and PDF show a skipped field's default, or "Not applicable."
- Once nothing is missing, the AI summarizes the key terms and points to the PDF download

### Completed (PL-11) - Multiple users

- Real accounts: `/signup` (name, email, password of 8+ characters; then on to `/login` with the email filled in) and `/login`, on a split-screen design (`frontend/src/auth/AuthLayout.tsx`)
- Passwords are hashed with scrypt and a per-user salt; sessions are random tokens in an httpOnly cookie (30 days), stored as SHA-256 hashes with an expiry in the `sessions` table; sign-out deletes the session (`backend/app/routers/auth.py`)
- The SQLite database persists (`prelegal-data` volume mounted at `/app/data` by the start scripts); `schema.sql` creates missing tables
- Downloading a PDF saves the document: `POST /api/documents` (or `PUT` to update the same one) creates a Confluence page in the Prelegal space with the key terms, parties and disclaimer, and attaches the PDF and `prelegal-draft.json` (`backend/app/routers/documents.py`, `backend/app/confluence.py`). The `documents` table indexes each user's pages
- `/documents` (My documents) lists the user's saved documents; Open reloads one into the builder (`/?open=<id>`) to keep editing, and View in Confluence opens its page
- If Confluence is not configured or fails, the PDF still downloads and the app says it was not saved
- Disclaimer ("finalization is subject to review and approval") under the chat, on the preview and PDF cover page, and on the Confluence page
- Tests: Confluence is faked with httpx `MockTransport`; `uv run --env-file ../.env pytest` also runs a live Confluence round trip when the Atlassian settings are present

### Local development

- Backend: `cd backend && uv run --env-file ../.env uvicorn app.main:app --reload` (port 8000; the env file supplies `OPENROUTER_API_KEY` and the Confluence settings)
- Frontend: `cd frontend && npm run dev` (port 3000; `/api` is proxied to port 8000)

### Current API Endpoints

- `POST /api/auth/signup` - Create an account with `{email, name, password}` (201; 409 if the email is taken); does not sign in
- `POST /api/auth/signin` - Sign in with `{email, password}` and set the session cookie (401 for wrong credentials)
- `GET /api/auth/me` - Get the signed-in user (401 if not signed in)
- `POST /api/auth/signout` - End the session and clear the cookie
- `POST /api/chat` - One AI chat turn: `{messages, draft}` in, `{reply, draft}` out (401 if not signed in, 422 for an invalid draft, 502 if the AI fails)
- `GET /api/documents` - The signed-in user's saved documents, newest first
- `POST /api/documents` - Save a document: multipart `draft` (JSON) and `pdf`; creates its Confluence page (201; 503 if Confluence is not configured, 502 if it fails)
- `PUT /api/documents/{id}` - Update a saved document and its Confluence page (404 if not the user's)
- `GET /api/documents/{id}` - Reopen a saved document: `{saved, draft}`
- `GET /api/health` - Health check
