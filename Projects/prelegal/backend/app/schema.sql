-- Tables are created only if missing: the database persists across restarts (a Docker volume in production).

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    -- SHA-256 of the session cookie's token, so a leaked database does not leak live sessions.
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);

-- The user's saved documents. Each is a Confluence page holding the PDF and the draft; this is the index.
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    title TEXT NOT NULL,
    -- A short random suffix that keeps the page title unique in the Confluence space.
    ref TEXT NOT NULL,
    page_id TEXT NOT NULL,
    page_url TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
