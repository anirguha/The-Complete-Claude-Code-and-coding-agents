# Phased execution plan

Workspace: `Exercises/Kanban_Antigravity`. Build the app in `frontend/`.

Execution completed on 24 October 2026. Criteria below were checked against the finished application.

## Scope

One client-rendered Next.js board with exactly five renameable columns and dummy data on startup. Cards have a title and details only. Users can add cards, delete cards, and drag cards between columns. Keep state in memory; reload restores the initial data. No persistence, user management, archive, search, filters, or extra product features.

Prioritize polished typography, spacing, responsive layouts, and accessible interactions. Apply the required palette: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, and gray `#888888`, ensuring readable contrast. No emojis in UI, code, or documentation.

## Phase 1: Project scaffolding and verification tools

Scaffold Next.js with TypeScript and React in `frontend/`. Configure `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, and `lucide-react`. Configure Vitest, React Testing Library, and Playwright with minimal dependencies.

Success criteria:

- [x] Application and dependency lockfile exist in `frontend/`.
- [x] `.gitignore` excludes dependencies, build output, environment files, and test artifacts.
- [x] Scripts cover development, build, lint, type checking, unit tests, and browser tests.
- [x] Initial application renders; lint, type checking, and production build pass.
- [x] Minimal README includes setup, run, and test commands (no emojis).

## Phase 2: Board foundation and visual design

Create simple typed board state and deterministic dummy data. Build the board, columns, and cards with the specified palette and a cohesive visual hierarchy. Support responsive scrolling on narrow screens.

Success criteria:

- [x] Initial view shows one board with exactly five columns and populated sample cards.
- [x] Cards contain title and details only.
- [x] All columns and controls remain accessible on desktop and mobile.
- [x] Empty columns, long text, hover states, and visible keyboard focus have deliberate styling.
- [x] Unit tests verify initial rendering, five-column structure, and seed cards.

## Phase 3: Complete required interactions

Implement card creation and deletion, column renaming, and drag-and-drop between columns using immutable in-memory updates. Require nonblank card and column titles. Provide accessible labels and predictable focus management.

Success criteria:

- [x] Adding a card places its title and details in the intended column.
- [x] Blank titles receive clear validation; cancelling creation preserves state.
- [x] Deleting removes only the intended card.
- [x] Renaming affects only the intended column and preserves exactly five columns.
- [x] Pointer and keyboard interactions move cards between columns, including empty destinations.
- [x] Cancelled drags and invalid destinations preserve state without losing or duplicating cards.
- [x] Reload resets the board to dummy data without using storage or a backend.
- [x] Rigorous unit tests cover validation, cancellation, creation, deletion, renaming, and movement.

## Phase 4: Integration testing and visual refinement

Exercise the running application through Playwright. Fix discovered defects and rerun affected checks before the full browser suite.

Success criteria:

- [x] Browser tests cover initial state, card creation/deletion, column renaming, and reload reset.
- [x] Browser tests verify drag-and-drop between columns and empty destinations.
- [x] Desktop and mobile layouts preserve readable text and usable scrolling.
- [x] Tested workflows produce no application errors in the browser console.

## Phase 5: Final checks and review handoff

Verify the finished MVP and leave the development server running for user review.

Success criteria:

- [x] Lint, type checking, unit tests, Playwright suite, and production build pass on the final code.
- [x] Scope review confirms every required feature and no unrequested functionality.
- [x] README commands match the actual setup.
- [x] Development server remains running and verified.

## Verification evidence

- Phase 1: Next.js 16.4.3, React 19.3.0, TypeScript, ESLint 9, `@dnd-kit/core`, `@dnd-kit/sortable`, `lucide-react`, and package lockfile. No external services or storage persistence.
- Phases 2-3: Responsive 5-column board, 9 seed cards, pure in-memory `kanbanReducer`, accessible native modal dialogs, and keyboard/pointer drag handles. `npm test`: 16/16 tests passed across reducer and component suites in 1.38s.
- Phase 4: `npm run test:e2e`: 18/18 Playwright tests passed across desktop Chromium and mobile Chromium emulation in 8.3s. Verified validation errors, modal cancellations, column renaming, intra-column card arranging, cross-column card dragging, empty column dropping, drop outside cancellation, and zero console/page errors. Screenshots captured in artifact directory.
- Phase 5: `npm run lint` (0 errors), `npm run typecheck` (0 errors), `npm test` (16/16 passed), `npm run test:e2e` (18/18 passed), `npm run build` (compiled successfully with Turbopack). Development server running at `http://127.0.0.1:3200` (HTTP 200 OK verified).
