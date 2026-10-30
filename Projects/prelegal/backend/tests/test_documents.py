import json
import re

import pytest
from pydantic import ValidationError

from app.documents import (
    DOCUMENTS,
    DOCUMENTS_PATH,
    Draft,
    Party,
    apply_updates,
    items,
    load_documents,
    missing_items,
    new_draft,
    updates_model,
)
from tests.helpers import updates

PROJECT_ROOT = DOCUMENTS_PATH.parent
TERM = re.compile(r'<span class="\w+_link">(.+?)</span>')
NDA = "mutual-nda"
CSA = "cloud-service-agreement"


def normalize(term: str) -> str:
    """Folds possessives and plurals, so "Customer's" and "Subscription Periods" match their fields."""
    return re.sub(r"[’']s$", "", term).removesuffix("s")


def test_documents_have_unique_ids():
    ids = [document["id"] for document in json.loads(DOCUMENTS_PATH.read_text())["documents"]]
    assert len(ids) == len(set(ids)) == len(load_documents(DOCUMENTS_PATH))


def test_every_catalog_template_is_a_document():
    catalog = json.loads((PROJECT_ROOT / "catalog.json").read_text())
    # The Mutual NDA's cover page is rendered from its fields rather than from its template.
    expected = {t["filename"] for t in catalog["templates"]} - {"templates/Mutual-NDA-coverpage.md"}
    assert {document.template for document in DOCUMENTS.values()} == expected


@pytest.mark.parametrize("document", DOCUMENTS.values(), ids=DOCUMENTS.keys())
def test_field_keys_are_unique_camel_case_identifiers(document):
    keys = [field.key for field in document.fields]
    assert len(keys) == len(set(keys))
    assert all(re.fullmatch(r"[a-z][A-Za-z0-9]*", key) for key in keys)


@pytest.mark.parametrize("document", DOCUMENTS.values(), ids=DOCUMENTS.keys())
def test_fields_cover_every_term_in_the_template(document):
    terms = set(TERM.findall((PROJECT_ROOT / document.template).read_text()))
    covered = {field.label for field in document.fields} | set(document.parties) | {"Notice Address"}

    assert {normalize(t) for t in terms} <= {normalize(c) for c in covered}


@pytest.mark.parametrize("document", DOCUMENTS.values(), ids=DOCUMENTS.keys())
def test_updates_model_mirrors_the_document_fields(document):
    model = updates_model(document.id)

    assert model.model_fields.keys() == {"fields", "party1", "party2", "skip_current_item"}
    assert model.model_fields["fields"].annotation.model_fields.keys() == {f.key for f in document.fields}


def test_draft_uses_camel_case_json_like_the_frontend():
    draft = Draft.model_validate(
        {"documentId": NDA, "fields": {"effectiveDate": "2026-10-29"}, "party1": {"noticeAddress": "a@acme.com"}}
    )

    dumped = draft.model_dump(by_alias=True)
    assert dumped["documentId"] == NDA
    assert dumped["party1"] == {"name": "", "title": "", "company": "", "noticeAddress": "a@acme.com"}


@pytest.mark.parametrize(
    "draft",
    [
        {"documentId": "employment-contract"},
        {"documentId": NDA, "fields": {"subscriptionPeriod": "1 year"}},
        {"documentId": NDA, "fields": {"effectiveDate": "next Monday"}},
        {"documentId": NDA, "fields": {"effectiveDate": "20261029"}},
        {"documentId": NDA, "fields": {"effectiveDate": "2026-02-30"}},
        {"documentId": NDA, "fields": {"purpose": "x" * 4001}},
        {"party1": {"company": "x" * 501}},
        {"documentId": NDA, "skipped": ["subscriptionPeriod"]},
        {"skipped": ["purpose"]},
        {"fields": {"purpose": "A deal"}},
    ],
)
def test_invalid_drafts_are_rejected(draft):
    with pytest.raises(ValidationError):
        Draft.model_validate(draft)


def test_new_draft_is_blank_and_keeps_the_parties():
    previous = Draft(document_id=NDA, fields={"governingLaw": "Delaware"}, party1=Party(company="Acme"))

    draft = new_draft("ai-addendum", previous)

    assert draft.document_id == "ai-addendum"
    assert draft.fields == {f.key: "" for f in DOCUMENTS["ai-addendum"].fields}
    assert draft.party1.company == "Acme"
    assert draft.skipped == []


def test_items_ask_for_the_companies_then_the_fields_then_the_signers():
    keys = [item.key for item in items("pilot-agreement")]

    assert keys == [
        "party1.company",
        "party2.company",
        "effectiveDate",
        "pilotPeriod",
        "generalCapAmount",
        "governingLaw",
        "chosenCourts",
        "party1.name",
        "party1.title",
        "party1.noticeAddress",
        "party2.name",
        "party2.title",
        "party2.noticeAddress",
    ]
    assert items("pilot-agreement")[0].label == "Provider company"
    assert items("pilot-agreement")[-1].label == "Customer notice address"


def test_missing_items_leave_out_filled_and_skipped_items():
    draft = new_draft("pilot-agreement", Draft(party1=Party(company="Acme", name="  ")))
    draft = draft.model_copy(update={"fields": draft.fields | {"pilotPeriod": "60 days"}, "skipped": ["generalCapAmount"]})

    keys = [item.key for item in missing_items(draft)]

    assert keys[:4] == ["party2.company", "effectiveDate", "governingLaw", "chosenCourts"]
    assert "party1.name" in keys
    assert not {"party1.company", "pilotPeriod", "generalCapAmount"} & set(keys)


def test_nothing_is_missing_without_a_document_or_once_everything_is_answered():
    assert missing_items(Draft()) == []
    draft = new_draft("pilot-agreement", Draft())
    assert missing_items(draft.model_copy(update={"skipped": [item.key for item in items("pilot-agreement")]})) == []


def apply(draft: Draft, allow_skip: bool = True, **changes) -> Draft:
    model = updates_model(draft.document_id)
    return apply_updates(draft, model.model_validate(updates(draft.document_id, **changes)), allow_skip)


def test_null_updates_leave_the_draft_unchanged():
    draft = new_draft(CSA, Draft(party1=Party(company="Acme")))

    assert apply(draft) == draft


def test_updates_set_fields_and_parties_independently():
    draft = new_draft(CSA, Draft(party1=Party(company="Acme", name="Jane")))

    result = apply(
        draft,
        fields={"governingLaw": "Delaware", "effectiveDate": "2026-11-02"},
        party1={"title": "CEO"},
        party2={"company": "Globex"},
    )

    assert result.fields == draft.fields | {"governingLaw": "Delaware", "effectiveDate": "2026-11-02"}
    assert result.party1 == Party(company="Acme", name="Jane", title="CEO")
    assert result.party2 == Party(company="Globex")


def test_empty_string_clears_a_field_and_the_original_is_untouched():
    draft = apply(new_draft(NDA, Draft()), fields={"modifications": "None."})

    result = apply(draft, fields={"modifications": ""}, party1={"company": "Globex"})

    assert result.fields["modifications"] == ""
    assert draft.fields["modifications"] == "None."
    assert draft.party1.company == ""


def test_skipping_marks_the_first_missing_item_skipped():
    draft = apply(new_draft(CSA, Draft(party1=Party(company="Acme"))), skip=True)

    result = apply(draft, skip=True)

    assert result.skipped == ["party2.company", "effectiveDate"]
    assert missing_items(result)[0].key == "orderDate"


def test_skipping_is_ignored_when_not_allowed_or_nothing_is_missing():
    draft = new_draft(CSA, Draft())
    assert apply(draft, allow_skip=False, skip=True).skipped == []

    everything = [item.key for item in items(CSA)]
    done = draft.model_copy(update={"skipped": everything})
    assert apply(done, skip=True).skipped == everything


def test_invalid_updates_are_rejected():
    with pytest.raises(ValidationError):
        apply(new_draft(NDA, Draft()), fields={"effectiveDate": "next Monday"})
