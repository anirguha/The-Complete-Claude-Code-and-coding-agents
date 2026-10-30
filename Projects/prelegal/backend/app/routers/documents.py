"""The signed-in user's saved documents.

Each saved document is a Confluence page showing the key terms, with the generated PDF and the draft (as JSON,
so the app can reopen it) attached. SQLite keeps the index: which user owns which page.
"""

import logging
import re
import secrets
import sqlite3
from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field, StringConstraints, ValidationError

from app.confluence import Confluence, ConfluenceError
from app.documents import DOCUMENTS, CamelModel, Document, Draft
from app.routers.auth import CurrentUser, Db

DRAFT_ATTACHMENT = "prelegal-draft.json"
MAX_PDF_BYTES = 10 * 1024 * 1024
# Confluence titles are at most 255 characters, so each company name in a title is shortened to this.
MAX_TITLE_COMPANY = 60

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_confluence(request: Request) -> Confluence:
    confluence = request.app.state.confluence
    if confluence is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Saving documents is not set up on this server.")
    return confluence


ConfluenceDep = Annotated[Confluence, Depends(get_confluence)]

Text = Annotated[str, StringConstraints(max_length=4000)]


class SummaryRow(CamelModel):
    label: Annotated[str, StringConstraints(max_length=200)]
    values: Annotated[list[Text], Field(min_length=1, max_length=2)]


class Summary(CamelModel):
    """The cover page as the app shows it (buildSummary in frontend/src/documents/coverPage.ts).

    The app formats every value, so the page shows exactly what the PDF does.
    """

    disclaimer: Text
    terms: Annotated[list[SummaryRow], Field(max_length=50)]
    party_roles: tuple[Text, Text]
    parties: Annotated[list[SummaryRow], Field(max_length=10)]


class SavedDocument(CamelModel):
    id: int
    document_id: str
    title: str
    page_url: str
    updated_at: str


class OpenedDocument(CamelModel):
    saved: SavedDocument
    draft: Draft


def parse[M: BaseModel](model: type[M], value: str, what: str) -> M:
    try:
        return model.model_validate_json(value)
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Invalid {what}: {error.errors()[0]['msg']}")


def read_pdf(pdf: UploadFile) -> bytes:
    content = pdf.file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES or not content.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Attach the document as a PDF of at most 10 MB")
    return content


def attachment_name(pdf: UploadFile) -> str:
    """The app's file name for the PDF, limited to safe characters."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", (pdf.filename or "").removesuffix(".pdf")).strip("-.")[:120]
    return f"{stem or 'document'}.pdf"


def page_title(document: Document, draft: Draft, ref: str) -> str:
    def company(party: str, role: str) -> str:
        name = getattr(draft, party).company.strip() or role
        return name if len(name) <= MAX_TITLE_COMPANY else name[: MAX_TITLE_COMPANY - 1].rstrip() + "…"

    return f"{document.name}: {company('party1', document.parties[0])} and {company('party2', document.parties[1])} ({ref})"


def page_body(document: Document, summary: Summary, pdf_name: str) -> str:
    """The page in Confluence storage format: the disclaimer, the key terms and the parties."""

    def rows(summary_rows: list[SummaryRow]) -> str:
        return "".join(
            f"<tr><th>{escape(row.label)}</th>{''.join(f'<td>{escape(value)}</td>' for value in row.values)}</tr>"
            for row in summary_rows
        )

    roles = "".join(f"<th>{escape(role)}</th>" for role in summary.party_roles)
    return (
        '<ac:structured-macro ac:name="info"><ac:rich-text-body>'
        f"<p>{escape(summary.disclaimer)}</p>"
        "</ac:rich-text-body></ac:structured-macro>"
        f"<p>A {escape(document.name)} drafted with Prelegal, based on the Common Paper standard terms. "
        f"The complete document is attached as <strong>{escape(pdf_name)}</strong>.</p>"
        f"<h2>Key terms</h2><table><tbody>{rows(summary.terms)}</tbody></table>"
        f"<h2>Parties</h2><table><tbody><tr><th></th>{roles}</tr>{rows(summary.parties)}</tbody></table>"
    )


def discard(confluence: Confluence, page_id: str) -> None:
    """Deletes a page that could not be fully saved, so no half-saved page is left behind."""
    try:
        confluence.delete_page(page_id)
    except ConfluenceError:
        logger.exception("Could not delete half-saved page %s", page_id)


def owned_row(db: sqlite3.Connection, user_id: int, saved_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM documents WHERE id = ? AND user_id = ?", (saved_id, user_id)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return row


def confluence_failed(user_id: int) -> HTTPException:
    logger.exception("Confluence request failed for user %s", user_id)
    return HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach Confluence. Please try again.")


def save(
    user: CurrentUser,
    db: sqlite3.Connection,
    confluence: Confluence,
    row: sqlite3.Row | None,
    draft: str,
    summary: str,
    pdf: UploadFile,
) -> SavedDocument:
    """Saves a new document (row is None) or updates the saved one: its Confluence page, then the index."""
    parsed = parse(Draft, draft, "draft")
    if parsed.document_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a document before saving it")
    document = DOCUMENTS[parsed.document_id]
    page_summary = parse(Summary, summary, "summary")
    content = read_pdf(pdf)

    ref = row["ref"] if row else secrets.token_hex(3)
    title = page_title(document, parsed, ref)
    name = attachment_name(pdf)
    body = page_body(document, page_summary, name)
    try:
        page = confluence.update_page(row["page_id"], title, body) if row else confluence.create_page(title, body)
        try:
            confluence.attach(page.id, name, content, "application/pdf")
            confluence.attach(page.id, DRAFT_ATTACHMENT, parsed.model_dump_json(by_alias=True).encode(), "application/json")
        except ConfluenceError:
            if row is None:
                discard(confluence, page.id)
            raise
    except ConfluenceError:
        raise confluence_failed(user.id)

    if row is None:
        row = db.execute(
            """
            INSERT INTO documents (user_id, document_id, title, ref, page_id, page_url)
            VALUES (?, ?, ?, ?, ?, ?) RETURNING *
            """,
            (user.id, document.id, title, ref, page.id, page.url),
        ).fetchone()
    else:
        row = db.execute(
            """
            UPDATE documents SET document_id = ?, title = ?, page_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? RETURNING *
            """,
            (document.id, title, page.url, row["id"]),
        ).fetchone()
    return SavedDocument.model_validate(dict(row))


@router.get("")
def list_documents(user: CurrentUser, db: Db) -> list[SavedDocument]:
    rows = db.execute(
        "SELECT * FROM documents WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (user.id,)
    ).fetchall()
    return [SavedDocument.model_validate(dict(row)) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def save_document(
    user: CurrentUser,
    db: Db,
    confluence: ConfluenceDep,
    draft: Annotated[str, Form()],
    summary: Annotated[str, Form()],
    pdf: UploadFile,
) -> SavedDocument:
    return save(user, db, confluence, None, draft, summary, pdf)


@router.put("/{saved_id}")
def update_document(
    saved_id: int,
    user: CurrentUser,
    db: Db,
    confluence: ConfluenceDep,
    draft: Annotated[str, Form()],
    summary: Annotated[str, Form()],
    pdf: UploadFile,
) -> SavedDocument:
    return save(user, db, confluence, owned_row(db, user.id, saved_id), draft, summary, pdf)


@router.get("/{saved_id}")
def open_document(saved_id: int, user: CurrentUser, db: Db, confluence: ConfluenceDep) -> OpenedDocument:
    row = owned_row(db, user.id, saved_id)
    try:
        draft = Draft.model_validate_json(confluence.read_attachment(row["page_id"], DRAFT_ATTACHMENT))
    except (ConfluenceError, ValidationError):
        raise confluence_failed(user.id)
    return OpenedDocument(saved=SavedDocument.model_validate(dict(row)), draft=draft)
