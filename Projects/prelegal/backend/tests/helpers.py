"""Test data shared by the document and chat tests."""

from app.documents import DOCUMENTS

NO_PARTY_UPDATES = {"name": None, "title": None, "company": None, "noticeAddress": None}


def updates(
    document_id: str,
    fields: dict | None = None,
    party1: dict | None = None,
    party2: dict | None = None,
    skip: bool = False,
) -> dict:
    """The JSON of a document's updates: the given changes, with null for everything else."""
    return {
        "fields": {field.key: None for field in DOCUMENTS[document_id].fields} | (fields or {}),
        "party1": NO_PARTY_UPDATES | (party1 or {}),
        "party2": NO_PARTY_UPDATES | (party2 or {}),
        "skipCurrentItem": skip,
    }
