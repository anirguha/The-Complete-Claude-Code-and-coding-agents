# Frontend

This directory contains the Next.js 16 / React 19 frontend. The app is exported as static files with `output: "export"` and served from FastAPI in Docker. Browser requests use same-origin `/api` paths in the exported app; during `next dev`, `src/lib/api.ts` sends requests to the local FastAPI service at `http://localhost:8000`.

## Structure

- `src/app/page.tsx`: checks the session, loads the board, and coordinates sign-in, sign-out, and persisted board changes.
- `src/app/globals.css`: Tailwind CSS 4 imports and project color/font tokens.
- `src/components/KanbanBoard.tsx`: drag-and-drop board and column/card actions.
- `src/components/KanbanColumn.tsx`, `KanbanCard.tsx`, `NewCardForm.tsx`: column, card editor, and card creation UI.
- `src/components/SignIn.tsx`: demo login form.
- `src/components/AIChatSidebar.tsx`: AI conversation UI; delegates requests and board persistence to the API module.
- `src/lib/kanban.ts`: board/card/column types, demo data, IDs, and drag-and-drop ordering.
- `src/lib/api.ts`: typed same-origin API client, with credentials included for the signed session cookie.
- `src/**/*.test.ts(x)`: Vitest and Testing Library unit/component tests.
- `tests/`: Playwright browser tests.

## Conventions

- Keep UI components typed and use the existing `@/` alias for `src/` imports.
- Persist board changes through `src/lib/api.ts`; do not add browser-only local storage as a second source of truth.
- Surface API failures in the UI instead of silently discarding them.
- Keep the static-export build compatible: avoid server-only Next.js features, runtime API routes, and features requiring an image optimizer.
- Run `npm run test:unit`, `npm run lint`, `npm run build`, and `npm run test:e2e` from this directory when changing frontend behavior.
