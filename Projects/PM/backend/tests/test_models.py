import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import database
from app.database import DEFAULT_BOARD
from app.models import Board


def test_default_board_has_complete_card_positions():
    board = DEFAULT_BOARD.model_dump()
    positioned = [card_id for column in board["columns"] for card_id in column["cardIds"]]
    assert set(positioned) == set(board["cards"])


def test_board_rejects_duplicate_or_missing_card_positions():
    board = DEFAULT_BOARD.model_dump()
    board["columns"][1]["cardIds"].append("card-1")
    with pytest.raises(ValidationError, match="only one column"):
        Board.model_validate(board)


def test_board_rejects_unknown_card_positions():
    board = DEFAULT_BOARD.model_dump()
    board["columns"][0]["cardIds"].append("unknown")
    with pytest.raises(ValidationError, match="exactly one column"):
        Board.model_validate(board)


def test_database_schema_matches_sqlite_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "kanban.db")
    database.initialize_database()
    schema_path = Path(__file__).parents[2] / "docs" / "database-schema.json"
    schema = json.loads(schema_path.read_text())

    with database.connect() as connection:
        actual_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert actual_tables == set(schema["tables"])
        for table_name, table in schema["tables"].items():
            actual_columns = {
                row["name"]
                for row in connection.execute(f'PRAGMA table_info("{table_name}")')
            }
            assert actual_columns == set(table["columns"])
