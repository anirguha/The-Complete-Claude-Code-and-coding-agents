import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Callable, Iterator

from app.models import Board

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "data/kanban.db"))
DEFAULT_BOARD = Board.model_validate(
    {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
            {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
            {
                "id": "col-progress",
                "title": "In Progress",
                "cardIds": ["card-4", "card-5"],
            },
            {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
            {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
        ],
        "cards": {
            "card-1": {
                "id": "card-1",
                "title": "Align roadmap themes",
                "details": "Draft quarterly themes with impact statements and metrics.",
            },
            "card-2": {
                "id": "card-2",
                "title": "Gather customer signals",
                "details": "Review support tags, sales notes, and churn feedback.",
            },
            "card-3": {
                "id": "card-3",
                "title": "Prototype analytics view",
                "details": "Sketch initial dashboard layout and key drill-downs.",
            },
            "card-4": {
                "id": "card-4",
                "title": "Refine status language",
                "details": "Standardize column labels and tone across the board.",
            },
            "card-5": {
                "id": "card-5",
                "title": "Design card layout",
                "details": "Add hierarchy and spacing for scanning dense lists.",
            },
            "card-6": {
                "id": "card-6",
                "title": "QA micro-interactions",
                "details": "Verify hover, focus, and loading states.",
            },
            "card-7": {
                "id": "card-7",
                "title": "Ship marketing page",
                "details": "Final copy approved and asset pack delivered.",
            },
            "card-8": {
                "id": "card-8",
                "title": "Close onboarding sprint",
                "details": "Document release notes and share internally.",
            },
        },
    }
)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS boards (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS columns (
                board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                id TEXT NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (board_id, id),
                UNIQUE(board_id, position)
            );
            CREATE TABLE IF NOT EXISTS cards (
                board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                id TEXT NOT NULL,
                column_id TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (board_id, id),
                UNIQUE(board_id, column_id, position),
                FOREIGN KEY (board_id, column_id)
                    REFERENCES columns(board_id, id) ON DELETE CASCADE
            );
            """
        )


def _ensure_board(connection: sqlite3.Connection, user_id: str) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
        (user_id, user_id),
    )
    connection.execute(
        "INSERT OR IGNORE INTO boards (id, user_id) VALUES (?, ?)",
        (f"board-{user_id}", user_id),
    )
    has_columns = connection.execute(
        "SELECT 1 FROM columns WHERE board_id = ? LIMIT 1", (f"board-{user_id}",)
    ).fetchone()
    if has_columns is None:
        _save_board(connection, user_id, DEFAULT_BOARD)


def _save_board(connection: sqlite3.Connection, user_id: str, board: Board) -> None:
    board_id = f"board-{user_id}"
    connection.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    for column_position, column in enumerate(board.columns):
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column.id, board_id, column.title, column_position),
        )
        for card_position, card_id in enumerate(column.cardIds):
            card = board.cards[card_id]
            connection.execute(
                """
                INSERT INTO cards
                    (id, board_id, column_id, title, details, position)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    card.id,
                    board_id,
                    column.id,
                    card.title,
                    card.details,
                    card_position,
                ),
            )


def _read_board(connection: sqlite3.Connection, user_id: str) -> Board:
    columns = connection.execute(
        """
        SELECT id, title FROM columns
        WHERE board_id = ? ORDER BY position
        """,
        (f"board-{user_id}",),
    ).fetchall()
    cards = connection.execute(
        """
        SELECT id, column_id, title, details FROM cards
        WHERE board_id = ? ORDER BY position
        """,
        (f"board-{user_id}",),
    ).fetchall()
    card_ids_by_column: dict[str, list[str]] = {row["id"]: [] for row in columns}
    card_map = {}
    for row in cards:
        card_ids_by_column[row["column_id"]].append(row["id"])
        card_map[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "details": row["details"],
        }
    return Board.model_validate(
        {
            "columns": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "cardIds": card_ids_by_column[row["id"]],
                }
                for row in columns
            ],
            "cards": card_map,
        }
    )


def load_board(user_id: str) -> Board:
    with connect() as connection:
        _ensure_board(connection, user_id)
        return _read_board(connection, user_id)


def save_board(user_id: str, board: Board) -> Board:
    with connect() as connection:
        _ensure_board(connection, user_id)
        _save_board(connection, user_id, board)
    return board


def update_board(user_id: str, change: Callable[[Board], Board]) -> Board:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_board(connection, user_id)
        board = _read_board(connection, user_id)
        updated = change(board)
        if updated != board:
            _save_board(connection, user_id, updated)
        return updated
