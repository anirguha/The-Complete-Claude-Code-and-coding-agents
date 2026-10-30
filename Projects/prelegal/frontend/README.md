# prelegal frontend — Legal Document Creator

A Next.js app for drafting Common Paper agreements by chatting with AI: the assistant picks the right
document, fills in its key terms from the conversation, the completed document updates in a live preview,
and the user downloads it as a PDF, which also saves it to Confluence. Users sign up and sign in, and
reopen saved documents from My documents.

## How it works

- `src/app/page.tsx` reads `../documents.json` and each document's template under `../templates/` at build
  time, so the repo remains the single source of truth for the agreement text.
- `src/documents/` holds the generic template parser and the logic that turns a draft into the filled-in
  Cover Page.
- `src/components/DocumentChat.tsx` talks to the backend's `/api/chat`, which returns the reply and the
  updated draft.
- `src/auth/` holds the sign-in and sign-up screens and the `AuthGate` that guards the app pages.
- `src/saved/` and `src/components/SavedDocuments.tsx` handle saved documents; `src/components/Workspace.tsx` opens
  one (`/?open=<id>`) into the builder.
- `src/components/DocumentPreview.tsx` renders the document as HTML; `src/components/DocumentPdf.tsx` renders
  the same content with `@react-pdf/renderer`, which is loaded only when the user clicks **Download PDF**.

The app must be run from this `frontend/` directory so the project files resolve at `..`.

## Development

```bash
npm install
npm run dev     # http://localhost:3000 (/api is proxied to the backend on port 8000)
npm test        # unit tests (Vitest)
npm run lint
npm run build
```
