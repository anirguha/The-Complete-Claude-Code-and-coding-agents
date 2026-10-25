from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Card(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(max_length=5000)


class Column(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    cardIds: list[str]


class Board(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[Column]
    cards: dict[str, Card]

    @model_validator(mode="after")
    def validate_card_positions(self) -> "Board":
        column_ids = [column.id for column in self.columns]
        if len(column_ids) != len(set(column_ids)):
            raise ValueError("Column IDs must be unique.")

        if any(card_id != card.id for card_id, card in self.cards.items()):
            raise ValueError("Card map keys must match card IDs.")

        positioned_card_ids = [
            card_id for column in self.columns for card_id in column.cardIds
        ]
        if len(positioned_card_ids) != len(set(positioned_card_ids)):
            raise ValueError("Each card can appear in only one column.")
        if set(positioned_card_ids) != set(self.cards):
            raise ValueError("Every card must appear in exactly one column.")
        return self


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)


class ChatResponse(BaseModel):
    response: str
    board: Board
