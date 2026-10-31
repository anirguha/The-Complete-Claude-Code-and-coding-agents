"""App wiring: lifespan, static files, environment and the SSE stream."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.importer import import_from_string

from app import main
from app.main import create_app, run_snapshots
from app.market.simulator import SimulatorDataSource


def snapshot_tasks() -> list[asyncio.Task]:
    return [t for t in asyncio.all_tasks() if t.get_name() == "portfolio-snapshots"]


class TestLifespan:
    def test_start_and_stop(self, make_app, tmp_path):
        app = make_app()
        source = app.state.source
        assert source.start_calls == []
        assert not (tmp_path / "finally.db").exists()  # nothing happens until startup

        with TestClient(app) as client:
            assert (tmp_path / "finally.db").exists()
            assert len(source.start_calls) == 1
            assert set(source.start_calls[0]) == set(app.state.portfolio.tracked_tickers())
            assert len(source.get_tickers()) == 10
            assert client.get("/api/health").status_code == 200
            assert source.stop_calls == 0

        assert source.stop_calls == 1

    async def test_snapshot_task_is_cancelled_at_shutdown(self, make_app):
        app = make_app()
        async with app.router.lifespan_context(app):
            await asyncio.sleep(0)
            tasks = snapshot_tasks()
            assert len(tasks) == 1
        assert tasks[0].cancelled()
        assert snapshot_tasks() == []

    def test_first_snapshot_is_only_recorded_once(self, make_app):
        app = make_app()
        with TestClient(app):
            assert len(app.state.portfolio.get_history()) == 1
        with TestClient(app):
            assert len(app.state.portfolio.get_history()) == 1

    def test_restart_tracks_held_tickers_and_keeps_data(self, make_app):
        first = make_app()
        with TestClient(first) as client:
            client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 1, "side": "buy"})
            client.delete("/api/watchlist/PYPL")

        second = make_app()
        with TestClient(second) as client:
            assert "PYPL" in second.state.source.get_tickers()
            assert client.get("/api/portfolio").json()["positions"][0]["ticker"] == "PYPL"
            assert client.get("/api/portfolio").json()["cash_balance"] == 9900.0

    def test_source_stops_even_if_startup_fails(self, make_app, monkeypatch):
        app = make_app()

        def fail(_):
            raise RuntimeError("boom")

        monkeypatch.setattr(main, "_record_first_snapshot", fail)
        with pytest.raises(RuntimeError, match="boom"):
            with TestClient(app):
                pass
        assert app.state.source.stop_calls == 1

    def test_snapshots_are_recorded_periodically(self, make_app):
        app = make_app(snapshot_seconds=0.01)
        with TestClient(app):
            deadline = time.monotonic() + 5
            while len(app.state.portfolio.get_history()) < 3 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert len(app.state.portfolio.get_history()) >= 3

    async def test_one_failed_snapshot_does_not_stop_the_loop(self):
        class FlakyPortfolio:
            calls = 0

            def record_snapshot(self):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("boom")

        portfolio = FlakyPortfolio()
        task = asyncio.create_task(run_snapshots(portfolio, 0.001))
        deadline = time.monotonic() + 5
        while portfolio.calls < 3 and time.monotonic() < deadline:
            await asyncio.sleep(0.001)
        assert not task.done()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert task.cancelled()
        assert portfolio.calls >= 3

    def test_real_simulator_end_to_end(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DB_PATH", str(tmp_path / "real.db"))
        monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        app = create_app(env_file=None)
        assert isinstance(app.state.source, SimulatorDataSource)
        with TestClient(app) as client:
            assert client.get("/api/health").json()["market"]["source"] == "simulator"
            rows = client.get("/api/watchlist").json()["watchlist"]
            assert all(r["price"] > 0 for r in rows)
            trade = client.post(
                "/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"}
            )
            assert trade.status_code == 200
            assert client.get("/api/portfolio").json()["positions"][0]["ticker"] == "ZZZZ"


class TestStaticFiles:
    @pytest.fixture
    def static_client(self, make_app, tmp_path, monkeypatch):
        static = tmp_path / "static"
        static.mkdir()
        (static / "index.html").write_text("<h1>FinAlly</h1>")
        (static / "404.html").write_text("<h1>Next.js not found page</h1>")
        (static / "app.js").write_text("console.log(1)")
        monkeypatch.setenv("STATIC_DIR", str(static))
        with TestClient(make_app()) as client:
            yield client

    def test_serves_the_frontend(self, static_client):
        index = static_client.get("/")
        assert index.status_code == 200
        assert "FinAlly" in index.text
        assert index.headers["content-type"].startswith("text/html")
        assert static_client.get("/app.js").status_code == 200

    def test_api_routes_win_over_the_mount(self, static_client):
        assert static_client.get("/api/health").json()["status"] == "ok"
        assert static_client.get("/api/portfolio").status_code == 200
        response = static_client.post(
            "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("method", ["get", "post", "delete"])
    @pytest.mark.parametrize("path", ["/api/nope", "/api/portfolio/nope", "/api/"])
    def test_unknown_api_path_is_json_404(self, static_client, method, path):
        response = getattr(static_client, method)(path)
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"detail": "Not Found"}

    def test_unknown_frontend_path_gets_the_html_404(self, static_client):
        response = static_client.get("/nope")
        assert response.status_code == 404
        assert "not found page" in response.text

    def test_path_only_starting_with_api_is_the_frontends(self, static_client):
        assert "not found page" in static_client.get("/apifoo").text

    def test_no_static_dir_is_fine_and_unknown_api_is_json_404(self, client):
        response = client.get("/api/nope")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}
        assert client.get("/").status_code == 404

    def test_mount_is_the_last_route(self, make_app, tmp_path, monkeypatch):
        static = tmp_path / "static"
        static.mkdir()
        monkeypatch.setenv("STATIC_DIR", str(static))
        assert make_app().routes[-1].name == "frontend"


class TestEnvironment:
    VARIABLE = "FINALLY_TEST_ENV_VARIABLE"

    @pytest.fixture
    def clean_variable(self, monkeypatch):
        # setenv first, so monkeypatch removes whatever load_dotenv sets.
        monkeypatch.setenv(self.VARIABLE, "x")
        monkeypatch.delenv(self.VARIABLE)

    def test_env_file_path_is_the_project_root(self):
        assert main.ENV_FILE == Path(main.__file__).parents[2] / ".env"

    def test_file_is_loaded(self, make_app, tmp_path, monkeypatch, clean_variable):
        env_file = tmp_path / "custom.env"
        env_file.write_text(f"{self.VARIABLE}=from-file\n")
        create_app(env_file=env_file)
        assert main.os.environ[self.VARIABLE] == "from-file"

    def test_file_does_not_override(self, make_app, tmp_path, monkeypatch):
        monkeypatch.setenv(self.VARIABLE, "already-set")
        env_file = tmp_path / "custom.env"
        env_file.write_text(f"{self.VARIABLE}=from-file\n")
        create_app(env_file=env_file)
        assert main.os.environ[self.VARIABLE] == "already-set"

    def test_missing_file_is_fine(self, make_app, tmp_path):
        create_app(env_file=tmp_path / "missing.env")

    def test_no_upward_search(self, make_app, tmp_path, monkeypatch, clean_variable):
        (tmp_path / ".env").write_text(f"{self.VARIABLE}=found-by-search\n")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        create_app(env_file=nested / ".env")
        assert self.VARIABLE not in main.os.environ
        create_app(env_file=None)
        assert self.VARIABLE not in main.os.environ

    def test_importing_create_app_does_not_build_the_module_app(self):
        assert "app" not in vars(main)

    def test_uvicorn_can_load_the_app(self, make_app, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "ENV_FILE", tmp_path / "missing.env")
        try:
            instance = import_from_string("app.main:app")
            assert isinstance(instance, FastAPI)
            assert main.app is instance  # built once
        finally:
            vars(main).pop("app", None)

    def test_other_attributes_still_raise(self):
        with pytest.raises(AttributeError):
            main.nonexistent


class TestStream:
    @staticmethod
    def stream_scope() -> dict:
        path = "/api/stream/prices"
        return {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": b"",
            "headers": [],
            "server": ("test", 80),
            "client": ("test", 1234),
        }

    async def test_streams_tracked_tickers_and_ends_on_disconnect(self, make_app):
        # Raw ASGI, because the stream never ends on its own.
        app = make_app()
        bodies: list[bytes] = []
        got_event = asyncio.Event()
        disconnect = asyncio.Event()

        async def receive():
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message.get("body"):
                bodies.append(message["body"])
                got_event.set()

        async with app.router.lifespan_context(app):
            await app.state.portfolio.execute_trade("PYPL", "buy", 1)
            await app.state.portfolio.remove_watchlist("PYPL")
            task = asyncio.create_task(app(self.stream_scope(), receive, send))
            await asyncio.wait_for(got_event.wait(), timeout=5)

            payload = json.loads(bodies[0].decode().removeprefix("data: "))
            assert "AAPL" in payload
            assert "PYPL" in payload  # held but unwatched: still priced
            assert set(payload["AAPL"]) == {
                "ticker",
                "price",
                "previous_price",
                "timestamp",
                "change",
                "direction",
            }

            disconnect.set()
            await asyncio.wait_for(task, timeout=5)  # ends without being cancelled
            assert task.exception() is None
