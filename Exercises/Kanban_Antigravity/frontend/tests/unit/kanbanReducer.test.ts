import { describe, expect, it } from "vitest";
import { initialBoard } from "../../lib/initialData";
import { kanbanReducer } from "../../lib/kanbanReducer";

describe("kanbanReducer", () => {
  it("initialBoard contains exactly 5 columns with valid initial cards", () => {
    expect(initialBoard).toHaveLength(5);
    const totalCards = initialBoard.reduce(
      (sum, col) => sum + col.cards.length,
      0,
    );
    expect(totalCards).toBe(9);
  });

  it("adds a new card to the specified column", () => {
    const action = {
      type: "add" as const,
      columnId: "backlog",
      card: {
        id: "new-card-1",
        title: "Test New Task",
        details: "Detailed notes here.",
      },
    };
    const newState = kanbanReducer(initialBoard, action);
    const backlog = newState.find((c) => c.id === "backlog");
    expect(backlog?.cards).toHaveLength(4);
    expect(backlog?.cards[3].title).toBe("Test New Task");
    expect(backlog?.cards[3].details).toBe("Detailed notes here.");
  });

  it("rejects adding a card with an empty or whitespace title", () => {
    const action = {
      type: "add" as const,
      columnId: "backlog",
      card: {
        id: "empty-title-card",
        title: "   ",
        details: "Some details",
      },
    };
    const newState = kanbanReducer(initialBoard, action);
    expect(newState).toEqual(initialBoard);
  });

  it("deletes a card by id from its column", () => {
    const action = {
      type: "delete" as const,
      cardId: "card-1",
    };
    const newState = kanbanReducer(initialBoard, action);
    const backlog = newState.find((c) => c.id === "backlog");
    expect(backlog?.cards.some((c) => c.id === "card-1")).toBe(false);
    expect(backlog?.cards).toHaveLength(2);
  });

  it("renames a column", () => {
    const action = {
      type: "rename" as const,
      columnId: "ready",
      title: "Prioritized",
    };
    const newState = kanbanReducer(initialBoard, action);
    const readyCol = newState.find((c) => c.id === "ready");
    expect(readyCol?.title).toBe("Prioritized");
  });

  it("rejects renaming a column to blank string", () => {
    const action = {
      type: "rename" as const,
      columnId: "ready",
      title: "   ",
    };
    const newState = kanbanReducer(initialBoard, action);
    const readyCol = newState.find((c) => c.id === "ready");
    expect(readyCol?.title).toBe("Ready");
  });

  it("arranges cards within the same column (reorders cards)", () => {
    // Backlog initial order: card-1, card-2, card-3
    // Move card-3 to the position of card-1 (to top)
    const action = {
      type: "move" as const,
      activeId: "card-3",
      overId: "card-1",
    };
    const newState = kanbanReducer(initialBoard, action);
    const backlog = newState.find((c) => c.id === "backlog");
    expect(backlog?.cards.map((c) => c.id)).toEqual([
      "card-3",
      "card-1",
      "card-2",
    ]);

    // Now move card-3 down to card-2's position
    const moveDown = {
      type: "move" as const,
      activeId: "card-3",
      overId: "card-2",
    };
    const stateAfterMoveDown = kanbanReducer(newState, moveDown);
    const backlogAfter = stateAfterMoveDown.find((c) => c.id === "backlog");
    expect(backlogAfter?.cards.map((c) => c.id)).toEqual([
      "card-1",
      "card-2",
      "card-3",
    ]);
  });

  it("moves a card from one column to another onto a specific card", () => {
    // Move card-1 from backlog to ready, over card-5
    const action = {
      type: "move" as const,
      activeId: "card-1",
      overId: "card-5",
    };
    const newState = kanbanReducer(initialBoard, action);
    const backlog = newState.find((c) => c.id === "backlog");
    const ready = newState.find((c) => c.id === "ready");

    expect(backlog?.cards.some((c) => c.id === "card-1")).toBe(false);
    expect(ready?.cards.map((c) => c.id)).toEqual([
      "card-4",
      "card-1",
      "card-5",
    ]);
  });

  it("moves a card to a column container", () => {
    const action = {
      type: "move" as const,
      activeId: "card-1",
      overId: "done",
    };
    const newState = kanbanReducer(initialBoard, action);
    const backlog = newState.find((c) => c.id === "backlog");
    const done = newState.find((c) => c.id === "done");
    expect(backlog?.cards.some((c) => c.id === "card-1")).toBe(false);
    expect(done?.cards.some((c) => c.id === "card-1")).toBe(true);
  });

  it("does not mutate state if moving over self or nonexistent destination", () => {
    const selfAction = {
      type: "move" as const,
      activeId: "card-1",
      overId: "card-1",
    };
    expect(kanbanReducer(initialBoard, selfAction)).toEqual(initialBoard);

    const invalidAction = {
      type: "move" as const,
      activeId: "card-1",
      overId: "nonexistent",
    };
    expect(kanbanReducer(initialBoard, invalidAction)).toEqual(initialBoard);
  });

  it("resets state to initialBoard", () => {
    const modified = kanbanReducer(initialBoard, {
      type: "delete",
      cardId: "card-1",
    });
    expect(modified.find((c) => c.id === "backlog")?.cards).toHaveLength(2);

    const resetState = kanbanReducer(modified, { type: "reset" });
    expect(resetState.find((c) => c.id === "backlog")?.cards).toHaveLength(3);
  });
});
