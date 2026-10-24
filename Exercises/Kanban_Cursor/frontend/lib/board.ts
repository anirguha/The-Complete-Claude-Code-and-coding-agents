import type { Board, Card } from "./types";

export function renameColumn(board: Board, columnId: string, name: string): Board {
  return {
    columns: board.columns.map((column) =>
      column.id === columnId ? { ...column, name } : column,
    ),
  };
}

export function addCard(
  board: Board,
  columnId: string,
  title: string,
  details: string,
): Board {
  const card: Card = { id: crypto.randomUUID(), title, details };
  return {
    columns: board.columns.map((column) =>
      column.id === columnId ? { ...column, cards: [...column.cards, card] } : column,
    ),
  };
}

export function updateCard(
  board: Board,
  columnId: string,
  cardId: string,
  title: string,
  details: string,
): Board {
  return {
    columns: board.columns.map((column) =>
      column.id === columnId
        ? {
            ...column,
            cards: column.cards.map((card) =>
              card.id === cardId ? { ...card, title, details } : card,
            ),
          }
        : column,
    ),
  };
}

export function deleteCard(board: Board, columnId: string, cardId: string): Board {
  return {
    columns: board.columns.map((column) =>
      column.id === columnId
        ? { ...column, cards: column.cards.filter((card) => card.id !== cardId) }
        : column,
    ),
  };
}

export function moveCard(
  board: Board,
  fromColumnId: string,
  toColumnId: string,
  cardId: string,
  index: number,
): Board {
  const fromColumn = board.columns.find((column) => column.id === fromColumnId);
  const card = fromColumn?.cards.find((item) => item.id === cardId);
  if (!fromColumn || !card) return board;

  return {
    columns: board.columns.map((column) => {
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
    }),
  };
}
