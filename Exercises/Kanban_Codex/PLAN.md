# Phased execution plan

Workspace: `Exercises/Kanban_Codex`. Build the app in `frontend/`.

Execution completed on 24 October 2026. Criteria below were checked against the finished application.

## Scope

One client-rendered Next.js board with exactly five renameable columns and dummy data on startup. Cards have a title and details only. Users can add cards, delete cards, and drag cards between columns. Keep state in memory; reload restores the initial data. No persistence, user management, archive, search, filters, or extra product features.

Prioritize polished typography, spacing, responsive layouts, and accessible interactions. Apply the required palette: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, and gray `#888888`, ensuring readable contrast.

## Phase 1: Project scaffolding and verification tools

Verify current stable versions using official sources at implementation time. Scaffold Next.js with TypeScript, keeping board interactions client rendered. Choose a maintained drag-and-drop library with keyboard support. Configure Vitest, React Testing Library, and Playwright with minimal dependencies.

Success criteria:

- [x] Application and dependency lockfile exist in `frontend/`.
- [x] `.gitignore` excludes dependencies, build output, environment files, and test artifacts.
- [x] Scripts cover development, build, lint, type checking, unit tests, and browser tests.
- [x] Initial application renders; lint, type checking, and production build pass.
- [x] Minimal README includes setup, run, and test commands.

## Phase 2: Board foundation and visual design

Depends on Phase 1. Create simple typed board state and deterministic dummy data. Build the board, columns, and cards with the specified palette and a cohesive visual hierarchy. Use horizontal scrolling on narrow screens where needed to keep columns usable.

Success criteria:

- [x] Initial view shows one board with exactly five columns and populated sample cards.
- [x] Cards contain title and details only.
- [x] All columns and controls remain accessible on desktop and mobile.
- [x] Empty columns, long text, hover states, and visible keyboard focus have deliberate styling.
- [x] Unit/component tests verify initial rendering, five-column structure, and unique seed identifiers.

## Phase 3: Complete the required interactions

Depends on Phase 2. Implement card creation and deletion, column renaming, and drag-and-drop between columns using immutable in-memory updates. Require nonblank card and column titles; allow empty details. Provide accessible labels and predictable focus management.

Success criteria:

- [x] Adding a card places its title and details in the intended column.
- [x] Blank titles receive clear validation; cancelling creation preserves state.
- [x] Deleting removes only the intended card.
- [x] Renaming affects only the intended column and preserves exactly five columns.
- [x] Pointer and keyboard interactions move cards between columns, including empty destinations.
- [x] Cancelled drags and invalid destinations preserve state without losing or duplicating cards.
- [x] Reload resets the board to dummy data without using storage or a backend.
- [x] Rigorous unit/component tests cover validation, cancellation, creation, deletion, renaming, movement, and preservation of unrelated state.

## Phase 4: Integration testing and visual refinement

Depends on Phase 3. Exercise the running application through Playwright and inspect desktop/mobile screenshots. Fix discovered defects and rerun affected checks before the full browser suite.

Success criteria:

- [x] Browser tests cover initial state, card creation/deletion, column renaming, and reload reset.
- [x] Browser tests verify pointer and keyboard drag-and-drop, empty destinations, and drag cancellation.
- [x] Browser tests cover form cancellation and blank-title validation.
- [x] Desktop and mobile layouts preserve readable text, reachable controls, and usable scrolling.
- [x] Keyboard navigation, accessible names, focus restoration, and any dialogs work correctly.
- [x] Visual inspection confirms polished spacing, contrast, long-text handling, and drag feedback.
- [x] Tested workflows produce no application errors in the browser console.

## Phase 5: Final checks and review handoff

Depends on Phase 4. Verify the finished MVP and leave it available locally for review.

Success criteria:

- [x] Lint, type checking, unit/component tests, Playwright suite, and production build pass on the final code.
- [x] Scope review confirms every required feature and no unrequested functionality.
- [x] README commands match the actual setup, including browser installation prerequisites and the in-memory reset behavior.
- [x] Development server remains running and its actual local URL has been checked.
- [x] Handoff shares the URL, verification results, and any material limitations.

## Execution discipline

Complete phases in dependency order. Record evidence and unresolved defects alongside the relevant phase. Do not mark criteria complete while defects remain. Keep changes inside this workspace and avoid deployment or external services as part of the MVP.

## Verification evidence

- Phase 1: Next.js 16.4.3, React 19.3.0, TypeScript, and npm lockfile. ESLint 9 is retained for compatibility with the Next.js lint plugins' declared peer ranges. No external services or environment variables.
- Phases 2–3: responsive five-column board, nine sample cards, in-memory reducer, accessible native dialogs, and pointer/touch/keyboard drag handles. `npm test`: 13 tests passed across state and component suites.
- Phase 4: `npm run test:e2e`: 10 tests passed across desktop Chromium and mobile Chromium emulation, including real touch events. Checked validation, cancellation, focus, renaming, adding/deleting, keyboard moves into an empty column, mouse/touch moves, invalid drops, long text, layout overflow, reload reset, and absence of browser application errors. Desktop/mobile board, dialog, and long-text screenshots were visually inspected.
- Defects fixed during browser verification: stable drag context identifier prevents hydration mismatches; dialog input receives focus after opening; tests wait for the announced keyboard drop destination before releasing.
- Phase 5: `npm run lint`, `npm run typecheck`, `npm test`, `npm run test:e2e`, and `npm run build` passed. Local development server is running at `http://127.0.0.1:3100`; HTTP response verified as 200.
- Intentional limitation: all changes reset on reload. Browser coverage uses Chromium desktop and mobile emulation; physical-device and Safari/Firefox testing was not performed.
