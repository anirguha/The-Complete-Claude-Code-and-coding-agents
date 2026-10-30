"""AI chat that drafts legal documents: each turn returns the assistant's reply and the updated draft.

The AI first works out which supported document the user needs, then fills in that document's fields.
The conversation is not stored; the browser sends the whole history and the current draft every turn.
"""

import logging
from datetime import date, timedelta
from functools import cache
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, status
from litellm import completion
from pydantic import BaseModel, Field, StringConstraints, create_model

from app.documents import DOCUMENTS, CamelModel, Draft, apply_updates, missing_items, new_draft, updates_model
from app.routers.auth import CurrentUser

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
LLM_TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = """\
You are Prelegal's assistant. You help the user draft legal agreements based on Common Paper's \
standard terms, by chatting with them and filling in the document's key terms.

Prelegal can draft only these documents (id: name. description):
{catalog}

How to work:
- Be friendly, concise and plain-spoken. Ask exactly one question per message, so the user is \
never handed a list.
- Write plain text: the chat does not render Markdown, so never use asterisks, bold or headings.
- If no document has been chosen, find out what the user needs. As soon as one of the documents \
above fits, set documentId to its id. If you are unsure between documents, briefly explain the \
options and ask.
- If the user asks for a document that is not in the list (for example an employment contract or \
a lease), explain that Prelegal cannot generate that document, and suggest any listed document \
that might help instead.
- Set documentId only to choose or switch documents; otherwise set it to null, which keeps the \
current document. Switch only when the user clearly wants a different listed document.
- Fill in a field only with what the user has said or clearly implied. Never invent names, \
companies, addresses or dates.
- In "updates", set only the values that change this turn and use null for everything else. To \
clear a value, set it to an empty string. Date fields take yyyy-mm-dd.
- If the user asks something unrelated, answer briefly and steer back to the document.
- You are not a lawyer. If asked for legal advice, say so and suggest they consult one.

Today's date is {today}. Look up dates like "next Monday" in this calendar of the coming two \
weeks rather than working them out:
{calendar}

{document}
"""

NO_DOCUMENT = "No document has been chosen yet."

DOCUMENT_SECTION = """\
The current document is the {name} ({id}).
{chosen}
Its parties are party1, the {party1}, and party2, the {party2}.

Its fields are:
{fields}

The draft currently holds (JSON):
{draft}

{progress}"""

NEXT_QUESTIONS = """Still to ask about, in this order (label, with its key in brackets):
{missing}

{current}
Record whatever the user's latest message provides, and acknowledge it briefly in "reply". Then \
put one question in "question" about the first item above that this turn's updates neither fill \
nor skip, briefly saying what it means and giving an example when that helps; do not repeat the \
question in "reply". If the user did not answer the item you last asked about, ask about it \
again. When a field has a usual choice, offer it so the user can simply agree, and if they do, use it word \
for word. Refer to items by their labels and never show the user keys like \
party1.name. Keep asking like this, one item per message, until every item is filled in or \
skipped. The user can answer "skip" to any question, so mention that for items that may not \
apply. If this turn fills or skips every remaining item, leave "question" empty and instead \
summarize the key terms in "reply" and tell the user they can download the PDF from the preview."""

ALL_DONE = """Every item is filled in or skipped. In "reply", answer the user's latest message, then \
summarize the key terms in a few lines and tell the user they can download the PDF from the \
preview, or ask you to change anything. Leave "question" empty."""

CURRENT_ITEM = """You last asked about the {label}. Set "skipCurrentItem" to true only if the user's \
latest message says to skip it, or that it is not needed or does not apply; then leave it unset in \
"updates" and ask about the next item. Otherwise set "skipCurrentItem" to false.
"""

NO_CURRENT_ITEM = """You have not asked about any item yet, so set "skipCurrentItem" to false.
"""

# Used when items are still missing but the AI did not ask about one, so every turn ends with a question.
FALLBACK_QUESTION = "What should the {label} be? You can say skip if it is not needed."

MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
# A reply and its follow-up question are joined into one message, which must fit in MessageText.
ReplyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3400)]
QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: MessageText


class ChatRequest(CamelModel):
    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=100)]
    draft: Draft


class ChatResponse(CamelModel):
    reply: str
    draft: Draft


@cache
def turn_model(document_id: str | None) -> type[BaseModel]:
    """What the AI returns each turn, via Structured Outputs. Updates exist only once a document is chosen."""
    fields = {
        # Constrained like ChatMessage.content, since the reply joins the history sent back next turn.
        "reply": (ReplyText, ...),
        "document_id": (Literal[tuple(DOCUMENTS)] | None, ...),
    }
    if document_id is not None:
        fields["updates"] = (updates_model(document_id), ...)
        # A separate field, so the AI cannot forget to ask about the next missing item.
        fields["question"] = (QuestionText, ...)
    return create_model("ChatTurn", __base__=CamelModel, **fields)


def compose_reply(reply: str, question: str, draft: Draft) -> str:
    """Joins the AI's reply and its question about the next missing item, filling in a question if it gave none."""
    missing = missing_items(draft)
    if missing and not question:
        question = FALLBACK_QUESTION.format(label=missing[0].label)
    return "\n\n".join(part for part in (reply, question) if part)


def format_day(day: date) -> str:
    return f"{day:%A}, {day.isoformat()}"


JUST_CHOSEN = """It was chosen from the user's latest message: confirm the choice in one sentence, \
fill in anything the conversation already says about it, then ask about what is missing.
"""


def describe_document(draft: Draft, just_chosen: bool) -> str:
    if draft.document_id is None:
        return NO_DOCUMENT
    document = DOCUMENTS[draft.document_id]
    fields = "\n".join(
        f"- {field.key} ({field.label}{', a date' if field.type == 'date' else ''}): {field.description}"
        + (f' Usual choice: "{field.default}"' if field.default else "")
        for field in document.fields
    )
    return DOCUMENT_SECTION.format(
        name=document.name,
        id=document.id,
        chosen=JUST_CHOSEN if just_chosen else "",
        party1=document.parties[0],
        party2=document.parties[1],
        fields=fields,
        draft=draft.model_dump_json(by_alias=True),
        progress=describe_progress(draft, just_chosen),
    )


def describe_progress(draft: Draft, just_chosen: bool) -> str:
    """What is left to ask about, worked out here so the AI keeps asking until nothing is missing."""
    missing = missing_items(draft)
    if not missing:
        return ALL_DONE
    return NEXT_QUESTIONS.format(
        missing="\n".join(f"- {item.label} ({item.key})" for item in missing),
        current=NO_CURRENT_ITEM if just_chosen else CURRENT_ITEM.format(label=missing[0].label),
    )


def build_messages(
    messages: list[ChatMessage], draft: Draft, today: date, just_chosen: bool = False
) -> list[dict[str, str]]:
    catalog = "\n".join(f"- {d.id}: {d.name}. {d.description}" for d in DOCUMENTS.values())
    # The model gets weekday arithmetic wrong, so it is given the dates to look up instead.
    calendar = "\n".join(format_day(today + timedelta(days=n)) for n in range(1, 15))
    system = SYSTEM_PROMPT.format(
        catalog=catalog, today=format_day(today), calendar=calendar, document=describe_document(draft, just_chosen)
    )
    return [{"role": "system", "content": system}, *(m.model_dump() for m in messages)]


def ask(messages: list[ChatMessage], draft: Draft, just_chosen: bool = False) -> BaseModel:
    turn_type = turn_model(draft.document_id)
    response = completion(
        model=MODEL,
        messages=build_messages(messages, draft, date.today(), just_chosen),
        response_format=turn_type,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    return turn_type.model_validate_json(response.choices[0].message.content)


@router.post("")
def chat(body: ChatRequest, user: CurrentUser) -> ChatResponse:
    draft = body.draft
    try:
        turn = ask(body.messages, draft)
        just_chosen = turn.document_id is not None and turn.document_id != draft.document_id
        if just_chosen:
            # The turn was answered without the new document's fields, so ask again with them. That
            # lets one message both choose the document and fill in what it already says.
            draft = new_draft(turn.document_id, draft)
            turn = ask(body.messages, draft, just_chosen=True)
        reply = turn.reply
        if draft.document_id is not None:
            draft = apply_updates(draft, turn.updates, allow_skip=not just_chosen)
            reply = compose_reply(turn.reply, turn.question, draft)
    except Exception:
        # Covers the LLM failing or timing out as well as a reply that is empty or does not fit the draft.
        logger.exception("Chat turn failed for user %s", user.id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The AI assistant could not respond. Please try again.")
    return ChatResponse(reply=reply, draft=draft)
