import { describe, expect, it } from "vitest";
import { boardReducer, initialBoard } from "../app/board-state";

describe("board state", () => {
  it("seeds five columns with globally unique identifiers and title/details cards", () => {
    expect(initialBoard).toHaveLength(5);
    const ids = initialBoard.flatMap((c) => [
      c.id,
      ...c.cards.map((card) => card.id),
    ]);
    expect(new Set(ids).size).toBe(ids.length);
    expect(initialBoard.every((c) => c.cards.length > 0)).toBe(true);
    initialBoard
      .flatMap((c) => c.cards)
      .forEach((card) =>
        expect(Object.keys(card).sort()).toEqual(["details", "id", "title"]),
      );
  });
  it("adds a trimmed card only to the selected column, allowing empty details", () => {
    const result = boardReducer(initialBoard, {
      type: "add",
      columnId: "next",
      card: { id: "new", title: "  A new idea  ", details: "" },
    });
    expect(result[1].cards.at(-1)).toEqual({
      id: "new",
      title: "A new idea",
      details: "",
    });
    expect(result[0]).toBe(initialBoard[0]);
    expect(initialBoard[1].cards).toHaveLength(2);
  });
  it("rejects blank card and column titles", () => {
    expect(
      boardReducer(initialBoard, {
        type: "add",
        columnId: "ideas",
        card: { id: "x", title: "  ", details: "" },
      }),
    ).toBe(initialBoard);
    expect(
      boardReducer(initialBoard, {
        type: "rename",
        columnId: "ideas",
        title: " ",
      }),
    ).toBe(initialBoard);
  });
  it("deletes only the intended card", () => {
    const result = boardReducer(initialBoard, { type: "delete", cardId: "c1" });
    expect(result[0].cards.map((c) => c.id)).toEqual(["c2", "c3"]);
    expect(result[1]).toBe(initialBoard[1]);
    expect(initialBoard[0].cards).toHaveLength(3);
  });
  it("renames a column without changing its cards or column count", () => {
    const result = boardReducer(initialBoard, {
      type: "rename",
      columnId: "doing",
      title: "  Building  ",
    });
    expect(result).toHaveLength(5);
    expect(result[2].title).toBe("Building");
    expect(result[2].cards).toBe(initialBoard[2].cards);
    expect(result[0]).toBe(initialBoard[0]);
  });
  it("moves a card without mutation, duplication, or loss", () => {
    const result = boardReducer(initialBoard, {
      type: "move",
      cardId: "c1",
      columnId: "done",
    });
    expect(result[0].cards.some((c) => c.id === "c1")).toBe(false);
    expect(result[4].cards.at(-1)).toEqual(initialBoard[0].cards[0]);
    expect(result.flatMap((c) => c.cards)).toHaveLength(9);
    expect(result[1]).toBe(initialBoard[1]);
    expect(initialBoard[0].cards).toHaveLength(3);
  });
  it("moves into an empty column", () => {
    const board = initialBoard.map((c) =>
      c.id === "done" ? { ...c, cards: [] } : c,
    );
    expect(
      boardReducer(board, {
        type: "move",
        cardId: "c1",
        columnId: "done",
      })[4].cards.map((c) => c.id),
    ).toEqual(["c1"]);
  });
  it("preserves state for same-column drops and invalid destinations", () => {
    for (const [cardId, columnId] of [
      ["c1", "ideas"],
      ["c1", "missing"],
      ["missing", "done"],
    ]) {
      expect(
        boardReducer(initialBoard, { type: "move", cardId, columnId }),
      ).toBe(initialBoard);
    }
  });
});
