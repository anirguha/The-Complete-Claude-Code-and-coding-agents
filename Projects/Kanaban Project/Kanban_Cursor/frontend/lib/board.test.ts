import { describe, expect, it } from "vitest";
import { addCard, deleteCard, moveCard, renameColumn, updateCard } from "./board";
import { initialBoard } from "./dummy-data";

describe("board", () => {
  it("seeds five columns", () => {
    expect(initialBoard.columns).toHaveLength(5);
    expect(initialBoard.columns.map((column) => column.name)).toEqual([
      "Backlog",
      "To Do",
      "In Progress",
      "Review",
      "Done",
    ]);
  });

  it("renames a column and keeps its cards", () => {
    const column = initialBoard.columns[0];
    const next = renameColumn(initialBoard, column.id, "Ideas");

    expect(next.columns).toHaveLength(5);
    expect(next.columns[0]).toEqual({ ...column, name: "Ideas" });
    expect(initialBoard.columns[0].name).toBe("Backlog");
  });

  it("adds a card to the end of a column", () => {
    const column = initialBoard.columns[1];
    const next = addCard(initialBoard, column.id, "Ship the board", "Polish the spacing");
    const cards = next.columns[1].cards;

    expect(next.columns).toHaveLength(5);
    expect(cards).toHaveLength(column.cards.length + 1);
    expect(cards.at(-1)).toMatchObject({
      title: "Ship the board",
      details: "Polish the spacing",
    });
    expect(initialBoard.columns[1].cards).toHaveLength(column.cards.length);
  });

  it("updates a card title and details", () => {
    const next = updateCard(
      initialBoard,
      "backlog",
      "launch-brief",
      "Launch notes",
      "A shorter brief",
    );

    expect(next.columns[0].cards[0]).toMatchObject({
      id: "launch-brief",
      title: "Launch notes",
      details: "A shorter brief",
    });
    expect(next.columns[0].cards[1]).toEqual(initialBoard.columns[0].cards[1]);
    expect(initialBoard.columns[0].cards[0].title).toBe("Draft the launch brief");
  });

  it("deletes only the chosen card", () => {
    const column = initialBoard.columns[0];
    const card = column.cards[0];
    const next = deleteCard(initialBoard, column.id, card.id);

    expect(next.columns[0].cards.map((item) => item.id)).toEqual(["competitor-notes"]);
    expect(next.columns[1].cards).toEqual(initialBoard.columns[1].cards);
    expect(next.columns).toHaveLength(5);
  });

  it("moves a card to another column", () => {
    const next = moveCard(initialBoard, "backlog", "done", "launch-brief", 0);

    expect(next.columns[0].cards.map((card) => card.id)).toEqual(["competitor-notes"]);
    expect(next.columns[4].cards[0].id).toBe("launch-brief");
    expect(next.columns).toHaveLength(5);
  });

  it("reorders a card within a column", () => {
    const next = moveCard(initialBoard, "backlog", "backlog", "launch-brief", 1);

    expect(next.columns[0].cards.map((card) => card.id)).toEqual([
      "competitor-notes",
      "launch-brief",
    ]);
    expect(next.columns[4].cards.map((card) => card.id)).toEqual(
      initialBoard.columns[4].cards.map((card) => card.id),
    );
  });

  it("appends a card when it is moved to the end of a column", () => {
    const next = moveCard(initialBoard, "review", "todo", "qa-pass", 2);

    expect(next.columns[3].cards).toEqual([]);
    expect(next.columns[1].cards.map((card) => card.id)).toEqual([
      "hero-copy",
      "empty-states",
      "qa-pass",
    ]);
  });
});
