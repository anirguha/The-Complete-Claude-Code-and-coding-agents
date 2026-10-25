from fastapi.testclient import TestClient

from app import database
from app.main import app


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
        updated = board.model_copy(deep=True)
        updated.columns[0].title = "Queued"
        return main.ChatResponse(response="Renamed.", board=updated)

    monkeypatch.setattr(main, "answer_chat", valid_update)
    response = client.post("/api/chat", json={"message": "Rename backlog"})

    assert response.status_code == 200
    assert response.json()["board"]["columns"][0]["title"] == "Queued"
    assert client.get("/api/board").json()["columns"][0]["title"] == "Queued"
