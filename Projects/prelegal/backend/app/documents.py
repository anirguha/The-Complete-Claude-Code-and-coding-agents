"""The documents Prelegal can draft, and drafts of them.

The documents are defined in documents.json at the project root, which the frontend reads too. A draft's
JSON shape (camelCase) mirrors Draft in frontend/src/documents/types.ts.
"""

import re
from datetime import date
from functools import cache
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, StringConstraints, create_model, model_validator
from pydantic.alias_generators import to_camel

# documents.json sits beside the backend directory, both in the repo and in the Docker image.
DOCUMENTS_PATH = Path(__file__).resolve().parents[2] / "documents.json"

# Drafts are embedded in the AI prompt, so their values are capped like chat messages.
FieldText = Annotated[str, StringConstraints(max_length=4000)]
PartyText = Annotated[str, StringConstraints(max_length=500)]
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DocumentField(CamelModel):
    # A camelCase identifier, used as the key in Draft.fields.
    key: str
    label: str
    description: str
    type: Literal["text", "longtext", "date"] = "text"
    # Offered to the user as the usual choice, and used in the document if they skip the field.
    default: str = ""


class Document(CamelModel):
    id: str
    name: str
    description: str
    template: str
    parties: tuple[str, str]
    fields: list[DocumentField]


class Catalog(BaseModel):
    documents: list[Document]


def load_documents(path: Path) -> dict[str, Document]:
    return {document.id: document for document in Catalog.model_validate_json(path.read_text()).documents}


DOCUMENTS = load_documents(DOCUMENTS_PATH)


class Party(CamelModel):
    name: PartyText = ""
    title: PartyText = ""
    company: PartyText = ""
    notice_address: PartyText = ""


class Draft(CamelModel):
    # None until the user and the AI settle on a document.
    document_id: str | None = None
    fields: dict[str, FieldText] = {}
    party1: Party = Party()
    party2: Party = Party()
    # Keys of items (see items()) the user chose to skip, so they are not asked about again.
    skipped: list[str] = []

    @model_validator(mode="after")
    def check_fields(self) -> "Draft":
        if self.document_id is None:
            if self.fields or self.skipped:
                raise ValueError("A draft without a document has no fields")
            return self
        document = DOCUMENTS.get(self.document_id)
        if document is None:
            raise ValueError(f"Unknown document {self.document_id!r}")
        if unknown := self.fields.keys() - {field.key for field in document.fields}:
            raise ValueError(f"Unknown fields for {document.id}: {sorted(unknown)}")
        if unknown := set(self.skipped) - {item.key for item in items(document.id)}:
            raise ValueError(f"Unknown skipped items for {document.id}: {sorted(unknown)}")
        for field in document.fields:
            value = self.fields.get(field.key)
            # Only yyyy-mm-dd: fromisoformat also accepts forms like 20261029 that the frontend can't show.
            if field.type == "date" and value and not (ISO_DATE.fullmatch(value) and date.fromisoformat(value)):
                raise ValueError(f"{field.label} must be a yyyy-mm-dd date")
        return self


class Item(NamedTuple):
    """Something the AI asks the user about: a field, or one party's detail."""

    # A field key such as "governingLaw", or a party detail such as "party1.company".
    key: str
    label: str


# The details asked about each party's signer, by Party attribute.
SIGNER_DETAILS = (("name", "signer's name"), ("title", "signer's title"), ("notice_address", "notice address"))


@cache
def items(document_id: str) -> tuple[Item, ...]:
    """Everything to ask about, in the order the AI asks: the companies, the fields, then the signers."""
    document = DOCUMENTS[document_id]
    parties = (("party1", document.parties[0]), ("party2", document.parties[1]))
    return (
        *(Item(f"{party}.company", f"{role} company") for party, role in parties),
        *(Item(field.key, field.label) for field in document.fields),
        *(
            Item(f"{party}.{to_camel(name)}", f"{role} {label}")
            for party, role in parties
            for name, label in SIGNER_DETAILS
        ),
    )


def item_value(draft: Draft, key: str) -> str:
    party, _, detail = key.partition(".")
    if detail:
        return getattr(draft, party).model_dump(by_alias=True)[detail]
    return draft.fields.get(key, "")


def missing_items(draft: Draft) -> list[Item]:
    """The items still blank and not skipped, in the order the AI should ask about them."""
    if draft.document_id is None:
        return []
    return [
        item
        for item in items(draft.document_id)
        if not item_value(draft, item.key).strip() and item.key not in draft.skipped
    ]


def new_draft(document_id: str, previous: Draft) -> Draft:
    """A blank draft of the document, keeping the parties from the previous draft.

    Defaults are not filled in, so the AI asks about every field, offering the default as the usual choice.
    """
    fields = {field.key: "" for field in DOCUMENTS[document_id].fields}
    return Draft(document_id=document_id, fields=fields, party1=previous.party1, party2=previous.party2)


# The updates below are what the AI returns via Structured Outputs. Every field is required but
# nullable, as strict JSON schemas need, and null means "leave this field as it is". They mirror Draft.

PartyUpdates = create_model(
    "PartyUpdates", __base__=CamelModel, **{name: (str | None, ...) for name in Party.model_fields}
)


@cache
def updates_model(document_id: str) -> type[BaseModel]:
    """The updates the AI may make to a draft of this document."""
    document = DOCUMENTS[document_id]
    field_updates = create_model(
        "FieldUpdates", __base__=CamelModel, **{field.key: (str | None, ...) for field in document.fields}
    )
    return create_model(
        "DraftUpdates",
        __base__=CamelModel,
        fields=(field_updates, ...),
        party1=(PartyUpdates, ...),
        party2=(PartyUpdates, ...),
        # Whether the user declined the item last asked about (the first missing one). A yes/no answer
        # rather than a list of keys, which the AI was prone to fill with items nobody asked about.
        skip_current_item=(bool, ...),
    )


def _merge(base: dict, updates: BaseModel) -> dict:
    """Returns base with the non-null updates applied, recursing into nested models."""
    merged = dict(base)
    for key, value in updates:
        if isinstance(value, BaseModel):
            merged[key] = _merge(base[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def apply_updates(draft: Draft, updates: BaseModel, allow_skip: bool = True) -> Draft:
    """Returns the draft with the non-null updates applied. Raises ValidationError if a result is invalid.

    When the updates skip the current item, the draft's first missing item is marked skipped, since that is
    the one the AI last asked about. allow_skip is False when no question has been asked yet.
    """
    merged = _merge(draft.model_dump(), updates)
    missing = missing_items(draft)
    if merged.pop("skip_current_item") and allow_skip and missing:
        merged["skipped"] = [*draft.skipped, missing[0].key]
    return Draft.model_validate(merged)
