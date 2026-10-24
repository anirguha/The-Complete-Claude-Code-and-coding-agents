export type ColumnId = "ideas" | "planned" | "in-progress" | "review" | "done";

export type Card = {
  id: string;
  title: string;
  details: string;
};

export type Column = {
  id: ColumnId;
  name: string;
  cards: Card[];
};

export type Board = {
  columns: Column[];
};

export const initialBoard: Board = {
  columns: [
    {
      id: "ideas",
      name: "Ideas",
      cards: [
        {
          id: "idea-01",
          title: "Explore a calmer onboarding",
          details: "Map the first five minutes and remove anything that feels like work.",
        },
        {
          id: "idea-02",
          title: "Collect launch stories",
          details: "Find a few early users willing to share how they work today.",
        },
      ],
    },
    {
      id: "planned",
      name: "Planned",
      cards: [
        {
          id: "plan-01",
          title: "Define the first-run experience",
          details: "Agree on the smallest useful path from sign-up to first success.",
        },
        {
          id: "plan-02",
          title: "Prepare the launch checklist",
          details: "Bring product, support, and communications into one shared plan.",
        },
        {
          id: "plan-03",
          title: "Review empty states",
          details: "Make sure every quiet screen still tells people what to do next.",
        },
      ],
    },
    {
      id: "in-progress",
      name: "In progress",
      cards: [
        {
          id: "work-01",
          title: "Build the welcome flow",
          details: "Keep setup short, friendly, and easy to skip when it is not needed.",
        },
        {
          id: "work-02",
          title: "Polish the project overview",
          details: "Bring the important details forward without adding more noise.",
        },
      ],
    },
    {
      id: "review",
      name: "In review",
      cards: [
        {
          id: "review-01",
          title: "Finalize the visual direction",
          details: "Check color, type, and spacing across the core product screens.",
        },
        {
          id: "review-02",
          title: "Check the mobile layout",
          details: "Walk through key screens at narrow widths before sign-off.",
        },
      ],
    },
    {
      id: "done",
      name: "Done",
      cards: [
        {
          id: "done-01",
          title: "Choose the launch audience",
          details: "Start with a small group of teams who will give honest feedback.",
        },
        {
          id: "done-02",
          title: "Agree on the product promise",
          details: "Describe the one thing the product should make noticeably easier.",
        },
      ],
    },
  ],
};

export function addCard(board: Board, columnId: ColumnId, card: Card): Board {
  return {
    columns: board.columns.map((column) =>
      column.id === columnId ? { ...column, cards: [...column.cards, card] } : column,
    ),
  };
}

export function deleteCard(board: Board, columnId: ColumnId, cardId: string): Board {
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
  sourceId: ColumnId,
  destinationId: ColumnId,
  cardId: string,
  beforeCardId?: string,
): Board {
  const card = board.columns
    .find((column) => column.id === sourceId)
    ?.cards.find((item) => item.id === cardId);
  if (!card || beforeCardId === cardId) return board;

  return {
    columns: board.columns.map((column) => {
      const cards = column.id === sourceId ? column.cards.filter((item) => item.id !== cardId) : column.cards;
      if (column.id !== destinationId) return { ...column, cards };
      const index = cards.findIndex((item) => item.id === beforeCardId);
      return {
        ...column,
        cards: index === -1 ? [...cards, card] : [...cards.slice(0, index), card, ...cards.slice(index)],
      };
    }),
  };
}

export function renameColumn(board: Board, columnId: ColumnId, name: string): Board {
  return {
    columns: board.columns.map((column) =>
      column.id === columnId ? { ...column, name } : column,
    ),
  };
}
