import { BoardAction, Column } from "./types";
import { initialBoard } from "./initialData";

export function moveCard(
  columns: Column[],
  fromColumnId: string,
  toColumnId: string,
  cardId: string,
  index: number,
): Column[] {
  const fromColumn = columns.find((column) => column.id === fromColumnId);
  const card = fromColumn?.cards.find((item) => item.id === cardId);
  if (!fromColumn || !card) return columns;

  return columns.map((column) => {
    if (column.id !== fromColumnId && column.id !== toColumnId) return column;

    const remaining =
      column.id === fromColumnId
        ? column.cards.filter((item) => item.id !== cardId)
        : column.cards;

    if (column.id !== toColumnId) return { ...column, cards: remaining };

    const next = [...remaining];
    const target = Math.max(0, Math.min(index, next.length));
    next.splice(target, 0, card);
    return { ...column, cards: next };
  });
}

export function kanbanReducer(state: Column[], action: BoardAction): Column[] {
  switch (action.type) {
    case "add": {
      const trimmedTitle = action.card.title.trim();
      if (!trimmedTitle) return state;

      return state.map((column) => {
        if (column.id !== action.columnId) return column;
        return {
          ...column,
          cards: [
            ...column.cards,
            {
              ...action.card,
              title: trimmedTitle,
              details: action.card.details.trim(),
            },
          ],
        };
      });
    }

    case "delete": {
      return state.map((column) => ({
        ...column,
        cards: column.cards.filter((card) => card.id !== action.cardId),
      }));
    }

    case "rename": {
      const trimmedTitle = action.title.trim();
      if (!trimmedTitle) return state;

      return state.map((column) => {
        if (column.id !== action.columnId) return column;
        return {
          ...column,
          title: trimmedTitle,
        };
      });
    }

    case "move": {
      const { activeId, overId } = action;
      if (!activeId || !overId || activeId === overId) return state;

      const fromColumn = state.find((column) =>
        column.cards.some((card) => card.id === activeId),
      );
      if (!fromColumn) return state;

      const toColumn =
        state.find((column) => column.id === overId) ??
        state.find((column) =>
          column.cards.some((card) => card.id === overId),
        );
      if (!toColumn) return state;

      if (fromColumn.id === toColumn.id) {
        const oldIndex = fromColumn.cards.findIndex(
          (card) => card.id === activeId,
        );
        const newIndex = fromColumn.cards.findIndex(
          (card) => card.id === overId,
        );
        if (newIndex < 0 || oldIndex === newIndex) return state;
        return moveCard(state, fromColumn.id, toColumn.id, activeId, newIndex);
      }

      const overIndex = toColumn.cards.findIndex((card) => card.id === overId);
      const index = overIndex < 0 ? toColumn.cards.length : overIndex;
      return moveCard(state, fromColumn.id, toColumn.id, activeId, index);
    }

    case "reset": {
      return initialBoard.map((column) => ({
        ...column,
        cards: [...column.cards],
      }));
    }

    default:
      return state;
  }
}
