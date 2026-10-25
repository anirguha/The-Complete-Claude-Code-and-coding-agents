# Database

The MVP uses SQLite with foreign-key enforcement. The database path defaults to `data/kanban.db` for local backend development and is set to `/app/data/kanban.db` in Docker. Compose mounts the named volume `pm-data` at `/app/data`; `docker compose down` stops/removes the container but preserves this volume. Use `docker compose down -v` only when intentionally deleting local board data.

The machine-readable schema is in [`database-schema.json`](./database-schema.json). It describes four relational tables:

- `users`: unique username; each user owns at most one board.
- `boards`: one board per user, enforced by a unique foreign key.
- `columns`: ordered per board, with IDs unique within their board.
- `cards`: ordered within a column, with IDs unique within their board, title, and details.

Columns and cards are ordered by their integer `position`. Column and card primary keys include the board ID, allowing different users' boards to reuse local IDs such as `card-1`. IDs are stable within a board across updates. Replacing a board deletes and reinserts its columns and cards within one SQLite transaction; composite foreign keys and cascades keep related rows consistent. Pydantic validates that every card appears in exactly one column and that the card map keys match card IDs before persistence.

On first successful sign-in, the backend creates the `user` row and seeds that user's board with the existing eight-card demo. Further sign-ins load the same stored board. The authentication credential is fixed to `user` / `password` for this local-only MVP; it is not stored as a user password in SQLite.

The AI service receives the current board and can return either `board_update: null` or a complete replacement board. The backend validates the proposed board before saving. Provider failures, malformed output, and invalid board data return an error and preserve the last valid database state.
