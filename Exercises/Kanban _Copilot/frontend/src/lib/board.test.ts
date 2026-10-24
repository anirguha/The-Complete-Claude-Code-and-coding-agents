import { describe, expect, it } from "vitest";
import {
  addCard,
  deleteCard,
  initialBoard,
  moveCard,
  renameColumn,
  type Board,
  type Card,
} from "./board";

const sampleCard: Card = {
  id: "new-01",
  title: "Write the launch note",
  details: "Share the release with the team.",
};

function copyBoard(): Board {
  return structuredClone(initialBoard);
}

describe("board", () => {
  it("starts with five named columns and dummy cards", () => {
    expect(initialBoard.columns).toHaveLength(5);
    expect(initialBoard.columns.map((column) => column.name)).toEqual([
      "Ideas",
      "Planned",
      "In progress",
      "In review",
      "Done",
    ]);
    expect(initialBoard.columns.every((column) => column.cards.length > 0)).toBe(true);
  });

  it("adds a card to the selected column without mutating the board", () => {
    const board = copyBoard();
    const result = addCard(board, "planned", sampleCard);

    expect(result.columns.find((column) => column.id === "planned")?.cards.at(-1)).toEqual(
      sampleCard,
    );
    expect(board.columns.find((column) => column.id === "planned")?.cards).not.toContain(
      sampleCard,
    );
  });

  it("deletes only the selected card", () => {
    const board = copyBoard();
    const result = deleteCard(board, "planned", "plan-01");

    expect(result.columns.find((column) => column.id === "planned")?.cards).toHaveLength(2);
    expect(result.columns.find((column) => column.id === "planned")?.cards).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ id: "plan-01" })]),
    );
    expect(result.columns.find((column) => column.id === "ideas")?.cards).toHaveLength(2);
  });

  it("moves a card from one column to another", () => {
    const board = copyBoard();
    const result = moveCard(board, "ideas", "in-progress", "idea-01");

    expect(result.columns.find((column) => column.id === "ideas")?.cards).toHaveLength(1);
    expect(result.columns.find((column) => column.id === "in-progress")?.cards.at(-1)).toEqual(
      expect.objectContaining({ id: "idea-01" }),
    );
    expect(board.columns.find((column) => column.id === "ideas")?.cards).toHaveLength(2);
  });

  it("reorders a card within its column", () => {
    const result = moveCard(copyBoard(), "planned", "planned", "plan-03", "plan-01");

    expect(result.columns.find((column) => column.id === "planned")?.cards.map((card) => card.id)).toEqual([
      "plan-03",
      "plan-01",
      "plan-02",
    ]);
  });

  it("moves a card to the end of its column when dropped without a target", () => {
    const result = moveCard(copyBoard(), "planned", "planned", "plan-01");

    expect(result.columns.find((column) => column.id === "planned")?.cards.map((card) => card.id)).toEqual([
      "plan-02",
      "plan-03",
      "plan-01",
    ]);
  });

  it("inserts a card before the target card in another column", () => {
    const result = moveCard(copyBoard(), "ideas", "done", "idea-01", "done-02");

    expect(result.columns.find((column) => column.id === "done")?.cards.map((card) => card.id)).toEqual([
      "done-01",
      "idea-01",
      "done-02",
    ]);
  });

  it("renames a column without changing its cards or identity", () => {
    const board = copyBoard();
    const result = renameColumn(board, "review", "Ready to ship");

    expect(result.columns.find((column) => column.id === "review")).toEqual({
      id: "review",
      name: "Ready to ship",
      cards: board.columns.find((column) => column.id === "review")?.cards,
    });
  });
});
