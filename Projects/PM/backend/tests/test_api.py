from fastapi.testclient import TestClient

from app import database
from app.main import app


def rename_action(column_id, title):
    return {
        "type": "rename_column",
        "column_id": column_id,
        "card_id": None,
        "title": title,
        "details": None,
        "position": None,
    }


def create_client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "kanban.db")
    database.initialize_database()
    return TestClient(app)


def signed_in_client(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 200
    return client


def test_health_is_available_without_auth(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_requires_demo_credentials(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    assert client.post(
        "/api/auth/login", json={"username": "user", "password": "wrong"}
    ).status_code == 401
    assert client.get("/api/board").status_code == 401


def test_login_board_update_and_logout(tmp_path, monkeypatch):
    client = signed_in_client(tmp_path, monkeypatch)
    initial = client.get("/api/board")
    assert initial.status_code == 200
    assert len(initial.json()["columns"]) == 5

    board = initial.json()
    board["columns"][0]["title"] = "Queued"
    updated = client.put("/api/board", json=board)
    assert updated.status_code == 200

    reloaded = client.get("/api/board")
    assert reloaded.json()["columns"][0]["title"] == "Queued"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/board").status_code == 401


def test_invalid_board_is_rejected_without_partial_save(tmp_path, monkeypatch):
    client = signed_in_client(tmp_path, monkeypatch)
    original = client.get("/api/board").json()
    invalid = {**original, "columns": original["columns"][:-1]}
    assert client.put("/api/board", json=invalid).status_code == 422
    assert client.get("/api/board").json() == original


def test_database_supports_same_card_ids_on_different_users(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "kanban.db")
    database.initialize_database()

    first = database.load_board("user")
    second = database.load_board("another-user")
    second.columns[0].title = "Separate board"
    database.save_board("another-user", second)

    assert first.cards.keys() == second.cards.keys()
    assert database.load_board("user").columns[0].title == "Backlog"
    assert database.load_board("another-user").columns[0].title == "Separate board"


def test_chat_provider_failure_keeps_board_unchanged(
    tmp_path, monkeypatch
):
    client = signed_in_client(tmp_path, monkeypatch)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    response = client.post("/api/chat", json={"message": "Add a card"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]
    assert len(client.get("/api/board").json()["cards"]) == 8


def test_chat_saves_a_valid_ai_board_update(tmp_path, monkeypatch):
    from app import main

    client = signed_in_client(tmp_path, monkeypatch)

    async def valid_update(board, chat_request):
        return "Renamed.", [rename_action("col-backlog", "Queued")]

    monkeypatch.setattr(main, "answer_chat", valid_update)
    response = client.post("/api/chat", json={"message": "Rename backlog"})

    assert response.status_code == 200
    assert response.json()["board"]["columns"][0]["title"] == "Queued"
    assert client.get("/api/board").json()["columns"][0]["title"] == "Queued"


def test_login_with_non_ascii_credentials_is_rejected(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/auth/login", json={"username": "us\u00e9r", "password": "p\u00e4ss"}
    )
    assert response.status_code == 401


def test_unknown_api_path_returns_404(tmp_path, monkeypatch):
    client = create_client(tmp_path, monkeypatch)
    assert client.get("/api/does-not-exist").status_code == 404


def test_columns_cannot_be_added_removed_or_reordered(tmp_path, monkeypatch):
    client = signed_in_client(tmp_path, monkeypatch)
    original = client.get("/api/board").json()

    replaced = {
        **original,
        "columns": [*original["columns"][:-1], {**original["columns"][-1], "id": "col-new"}],
    }
    reordered = {**original, "columns": original["columns"][::-1]}

    assert client.put("/api/board", json=replaced).status_code == 400
    assert client.put("/api/board", json=reordered).status_code == 400
    assert client.get("/api/board").json() == original


def test_chat_keeps_edits_made_while_ai_was_responding(tmp_path, monkeypatch):
    from app import main

    client = signed_in_client(tmp_path, monkeypatch)

    async def slow_update(board, chat_request):
        edited = client.get("/api/board").json()
        edited["cards"]["card-1"]["title"] = "Edited during chat"
        assert client.put("/api/board", json=edited).status_code == 200
        return "Renamed.", [rename_action("col-backlog", "Queued")]

    monkeypatch.setattr(main, "answer_chat", slow_update)
    response = client.post("/api/chat", json={"message": "Rename backlog"})

    assert response.status_code == 200
    saved = client.get("/api/board").json()
    assert saved == response.json()["board"]
    assert saved["columns"][0]["title"] == "Queued"
    assert saved["cards"]["card-1"]["title"] == "Edited during chat"


def test_chat_conflicting_with_a_concurrent_edit_saves_nothing(
    tmp_path, monkeypatch
):
    from app import main

    client = signed_in_client(tmp_path, monkeypatch)

    async def stale_update(board, chat_request):
        edited = client.get("/api/board").json()
        edited["columns"][0]["cardIds"].remove("card-1")
        del edited["cards"]["card-1"]
        assert client.put("/api/board", json=edited).status_code == 200
        return "Updated.", [
            rename_action("col-backlog", "Queued"),
            {**rename_action(None, "Renamed"), "type": "update_card", "card_id": "card-1"},
        ]

    monkeypatch.setattr(main, "answer_chat", stale_update)
    response = client.post("/api/chat", json={"message": "Rename card 1"})

    assert response.status_code == 409
    saved = client.get("/api/board").json()
    assert saved["columns"][0]["title"] == "Backlog"
    assert "card-1" not in saved["cards"]
