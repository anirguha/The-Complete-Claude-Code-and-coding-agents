import json
import os
import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.confluence import Confluence
from app.documents import Draft, Party, new_draft
from app.main import create_app
from app.routers import documents
from tests.conftest import ALICE, sign_up_and_in

BASE = "https://acme.atlassian.net/wiki"
PDF = b"%PDF-1.4 a pdf"
BOB = {"email": "bob@example.com", "name": "Bob", "password": "another password"}
PDF_NAME = "Mutual-Non-Disclosure-Agreement-Acme-Globex.pdf"
SUMMARY = {
    "disclaimer": "This document is an AI-assisted draft.",
    "terms": [
        {"label": "Effective Date", "values": ["November 2, 2026"]},
        {"label": "Governing Law", "values": ["Delaware"]},
    ],
    "partyRoles": ["Party 1", "Party 2"],
    "parties": [{"label": "Company", "values": ["Acme", "Globex"]}],
}


class FakeConfluence:
    """An in-memory stand-in for the Confluence REST endpoints the client uses."""

    def __init__(self):
        self.pages: dict[str, dict] = {}
        self.fail = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.fail:
            return httpx.Response(500, text="Confluence is down")
        path, method = request.url.path.removeprefix("/wiki"), request.method
        if path == "/api/v2/spaces":
            return httpx.Response(200, json={"results": [{"id": "131075", "key": request.url.params["keys"]}]})
        if path == "/api/v2/pages" and method == "POST":
            body = json.loads(request.content)
            page_id = str(1000 + len(self.pages))
            self.pages[page_id] = {**body, "version": 1, "attachments": {}}
            return httpx.Response(200, json=self.page_json(page_id))
        if match := re.fullmatch(r"/api/v2/pages/(\d+)", path):
            page = self.pages[match[1]]
            if method == "PUT":
                body = json.loads(request.content)
                assert body["version"]["number"] == page["version"] + 1
                page.update(title=body["title"], body=body["body"], version=body["version"]["number"])
            elif method == "DELETE":
                del self.pages[match[1]]
                return httpx.Response(204)
            return httpx.Response(200, json=self.page_json(match[1]))
        if match := re.fullmatch(r"/rest/api/content/(\d+)/child/attachment", path):
            attachments = self.pages[match[1]]["attachments"]
            if method == "PUT":
                assert request.headers["X-Atlassian-Token"] == "no-check"
                filename, content = parse_upload(request)
                attachments[filename] = content
                return httpx.Response(200, json={"results": []})
            name = request.url.params["filename"]
            found = [{"_links": {"download": f"/download/{match[1]}/{name}"}}] if name in attachments else []
            return httpx.Response(200, json={"results": found})
        if match := re.fullmatch(r"/download/(\d+)/(.+)", path):
            return httpx.Response(200, content=self.pages[match[1]]["attachments"][match[2]])
        return httpx.Response(404)

    def page_json(self, page_id: str) -> dict:
        page = self.pages[page_id]
        return {"id": page_id, "title": page["title"], "version": {"number": page["version"]}, "_links": {"webui": f"/spaces/SCRUM/pages/{page_id}"}}


def parse_upload(request: httpx.Request) -> tuple[str, bytes]:
    content = request.read()
    boundary = request.headers["content-type"].split("boundary=")[1].encode()
    for part in content.split(b"--" + boundary):
        if b'name="file"' in part:
            head, _, body = part.partition(b"\r\n\r\n")
            return re.search(rb'filename="([^"]+)"', head)[1].decode(), body.removesuffix(b"\r\n")
    raise AssertionError("no file in upload")


@pytest.fixture
def confluence() -> FakeConfluence:
    return FakeConfluence()


@pytest.fixture
def client(db_path: Path, static_dir: Path, confluence: FakeConfluence):
    client = Confluence(BASE, "me@acme.com", "token", "SCRUM", transport=httpx.MockTransport(confluence.handle))
    with TestClient(create_app(db_path, static_dir, client)) as test_client:
        yield test_client


def draft_json(**changes) -> str:
    draft = new_draft("mutual-nda", Draft(party1=Party(company="Acme"), party2=Party(company="Globex")))
    draft = draft.model_copy(update={"fields": draft.fields | {"governingLaw": "Delaware", "effectiveDate": "2026-11-02"}, "skipped": ["modifications"], **changes})
    return draft.model_dump_json(by_alias=True)


def save(
    client: TestClient,
    draft: str | None = None,
    pdf: bytes = PDF,
    saved_id: int | None = None,
    summary: str | None = None,
    pdf_name: str = PDF_NAME,
):
    files = {"pdf": (pdf_name, pdf, "application/pdf")}
    data = {"draft": draft or draft_json(), "summary": summary or json.dumps(SUMMARY)}
    if saved_id is None:
        return client.post("/api/documents", data=data, files=files)
    return client.put(f"/api/documents/{saved_id}", data=data, files=files)


def test_documents_require_sign_in(client: TestClient):
    assert client.get("/api/documents").status_code == 401
    assert save(client).status_code == 401
    assert client.get("/api/documents/1").status_code == 401


def test_saving_creates_a_confluence_page_with_the_pdf_and_draft(signed_in: TestClient, confluence: FakeConfluence):
    response = save(signed_in)

    assert response.status_code == 201
    saved = response.json()
    assert saved["documentId"] == "mutual-nda"
    assert re.fullmatch(r"Mutual Non-Disclosure Agreement: Acme and Globex \([0-9a-f]{6}\)", saved["title"])
    [(page_id, page)] = confluence.pages.items()
    assert saved["pageUrl"] == f"{BASE}/spaces/SCRUM/pages/{page_id}"
    assert page["spaceId"] == "131075" and page["title"] == saved["title"]

    body = page["body"]["value"]
    assert "<p>This document is an AI-assisted draft.</p>" in body
    assert f"attached as <strong>{PDF_NAME}</strong>" in body
    assert "<tr><th>Effective Date</th><td>November 2, 2026</td></tr><tr><th>Governing Law</th><td>Delaware</td></tr>" in body
    assert "<tr><th></th><th>Party 1</th><th>Party 2</th></tr><tr><th>Company</th><td>Acme</td><td>Globex</td></tr>" in body

    attachments = page["attachments"]
    assert attachments[PDF_NAME] == PDF
    assert json.loads(attachments[documents.DRAFT_ATTACHMENT])["fields"]["governingLaw"] == "Delaware"


def test_page_content_is_escaped(signed_in: TestClient, confluence: FakeConfluence):
    summary = {**SUMMARY, "parties": [{"label": "Company", "values": ["<script>Acme & Co</script>", "Globex"]}]}
    save(signed_in, summary=json.dumps(summary))

    [page] = confluence.pages.values()
    assert "<script>" not in page["body"]["value"]
    assert "&lt;script&gt;Acme &amp; Co&lt;/script&gt;" in page["body"]["value"]


def test_long_company_names_are_shortened_in_the_title(signed_in: TestClient):
    long_name = "Acme " * 100

    saved = save(signed_in, draft_json(party1=Party(company=long_name), party2=Party(company=long_name))).json()

    assert len(saved["title"]) <= 255
    assert "Acme Acme" in saved["title"] and "…" in saved["title"]


def test_attachment_names_are_made_safe(signed_in: TestClient, confluence: FakeConfluence):
    save(signed_in, pdf_name="../../etc/pass wd?.pdf")
    save(signed_in, pdf_name="###.pdf")

    names = [name for page in confluence.pages.values() for name in page["attachments"] if name.endswith(".pdf")]
    assert names == ["etc-pass-wd.pdf", "document.pdf"]


def test_saved_documents_are_listed_newest_first_and_reopened(signed_in: TestClient):
    first = save(signed_in).json()
    second = save(signed_in, draft_json(party2=Party(company="Initech"))).json()

    listed = signed_in.get("/api/documents").json()
    assert [d["id"] for d in listed] == [second["id"], first["id"]]

    opened = signed_in.get(f"/api/documents/{second['id']}").json()
    assert opened["saved"] == second
    assert opened["draft"]["party2"]["company"] == "Initech"
    assert opened["draft"]["skipped"] == ["modifications"]


def test_saving_again_updates_the_same_page(signed_in: TestClient, confluence: FakeConfluence):
    saved = save(signed_in).json()

    updated = save(signed_in, draft_json(party2=Party(company="Initech")), pdf=b"%PDF-2", saved_id=saved["id"])

    assert updated.status_code == 200
    assert updated.json()["id"] == saved["id"]
    assert updated.json()["title"].startswith("Mutual Non-Disclosure Agreement: Acme and Initech (")
    assert updated.json()["title"][-8:] == saved["title"][-8:]  # same unique suffix
    [page] = confluence.pages.values()
    assert page["version"] == 2
    assert b"%PDF-2" in page["attachments"].values()
    assert len(signed_in.get("/api/documents").json()) == 1


def test_users_cannot_see_or_change_each_others_documents(signed_in: TestClient, confluence: FakeConfluence):
    saved = save(signed_in).json()
    with TestClient(signed_in.app) as bob:
        sign_up_and_in(bob, BOB)
        assert bob.get("/api/documents").json() == []
        assert bob.get(f"/api/documents/{saved['id']}").status_code == 404
        assert save(bob, saved_id=saved["id"]).status_code == 404
    assert len(signed_in.get("/api/documents").json()) == 1


@pytest.mark.parametrize(
    "draft, pdf, summary",
    [
        (json.dumps({"documentId": None}), PDF, None),
        ("not json", PDF, None),
        (json.dumps({"documentId": "employment-contract"}), PDF, None),
        (None, b"not a pdf", None),
        (None, b"%PDF" + b"x" * documents.MAX_PDF_BYTES, None),
        (None, PDF, "not json"),
        (None, PDF, json.dumps({**SUMMARY, "terms": [{"label": "Law", "values": []}]})),
    ],
)
def test_invalid_saves_are_rejected(signed_in: TestClient, confluence: FakeConfluence, draft, pdf, summary):
    assert save(signed_in, draft, pdf, summary=summary).status_code == 422
    assert confluence.pages == {}


def test_confluence_failures_are_a_bad_gateway(signed_in: TestClient, confluence: FakeConfluence):
    saved = save(signed_in).json()
    confluence.fail = True

    assert save(signed_in).status_code == 502
    assert save(signed_in, saved_id=saved["id"]).status_code == 502
    response = signed_in.get(f"/api/documents/{saved['id']}")
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not reach Confluence. Please try again."
    assert len(signed_in.get("/api/documents").json()) == 1


def test_a_failed_attachment_removes_the_new_page(signed_in: TestClient, confluence: FakeConfluence):
    handle = confluence.handle

    def fail_attachments(request: httpx.Request) -> httpx.Response:
        if "child/attachment" in request.url.path:
            return httpx.Response(500)
        return handle(request)

    signed_in.app.state.confluence.http._transport = httpx.MockTransport(fail_attachments)

    assert save(signed_in).status_code == 502
    assert confluence.pages == {}
    assert signed_in.get("/api/documents").json() == []


def test_saving_is_unavailable_without_confluence(db_path: Path, static_dir: Path):
    with TestClient(create_app(db_path, static_dir)) as client:
        sign_up_and_in(client)
        response = save(client)
        assert response.status_code == 503
        assert response.json()["detail"] == "Saving documents is not set up on this server."
        assert client.get("/api/documents").json() == []


@pytest.mark.skipif(Confluence.from_env() is None, reason="needs Confluence settings (run with --env-file ../.env)")
def test_live_confluence_round_trip(db_path: Path, static_dir: Path):
    """Saves, updates and reopens a document in the real Confluence space, then deletes the page."""
    live = Confluence.from_env()
    with TestClient(create_app(db_path, static_dir, live)) as client:
        sign_up_and_in(client, {**ALICE, "email": "prelegal-live-test@example.com"})
        saved = save(client).json()
        page_id = saved["pageUrl"].rstrip("/").split("/")[-1]
        try:
            assert saved["pageUrl"].startswith(live.base_url)
            updated = save(client, draft_json(party2=Party(company="Initech")), saved_id=saved["id"]).json()
            assert "Initech" in updated["title"]
            assert client.get(f"/api/documents/{saved['id']}").json()["draft"]["party2"]["company"] == "Initech"
        finally:
            live.delete_page(page_id)
