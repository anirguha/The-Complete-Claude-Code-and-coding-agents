export type Card = { id: string; title: string; details: string };
export type Column = { id: string; title: string; cards: Card[] };
export const initialBoard: Column[] = [
  {
    id: "ideas",
    title: "Backlog",
    cards: [
      {
        id: "c1",
        title: "A little inspiration",
        details: "Collect references for a calmer, more thoughtful workspace.",
      },
      {
        id: "c2",
        title: "Map the first impression",
        details:
          "Sketch the journey from a blank page to that first small win.",
      },
      {
        id: "c3",
        title: "Make room for the details",
        details:
          "Explore the small touches that make everyday work feel better.",
      },
    ],
  },
  {
    id: "next",
    title: "Up next",
    cards: [
      {
        id: "c4",
        title: "Find our visual direction",
        details: "A warm palette, generous space, and a little personality.",
      },
      {
        id: "c5",
        title: "Write like a human",
        details: "Keep the language clear, useful, and welcoming.",
      },
    ],
  },
  {
    id: "doing",
    title: "In progress",
    cards: [
      {
        id: "c6",
        title: "Build the essentials",
        details: "Focus on the few things that help a team move forward.",
      },
      {
        id: "c7",
        title: "Sweat the small stuff",
        details:
          "Give every interaction a purpose. Then make it feel effortless.",
      },
    ],
  },
  {
    id: "review",
    title: "In review",
    cards: [
      {
        id: "c8",
        title: "Take a fresh look",
        details: "Walk through the experience with a new pair of eyes.",
      },
    ],
  },
  {
    id: "done",
    title: "Done",
    cards: [
      {
        id: "c9",
        title: "Start with a simple idea",
        details: "One shared space. A clear next step. Less noise.",
      },
    ],
  },
];
export type Action =
  | { type: "add"; columnId: string; card: Card }
  | { type: "delete"; cardId: string }
  | { type: "rename"; columnId: string; title: string }
  | { type: "move"; cardId: string; columnId: string };
export function boardReducer(board: Column[], action: Action): Column[] {
  switch (action.type) {
    case "add":
      if (!action.card.title.trim()) return board;
      return board.map((column) =>
        column.id === action.columnId
          ? {
              ...column,
              cards: [
                ...column.cards,
                {
                  ...action.card,
                  title: action.card.title.trim(),
                  details: action.card.details.trim(),
                },
              ],
            }
          : column,
      );
    case "delete":
      return board.map((column) =>
        column.cards.some((card) => card.id === action.cardId)
          ? {
              ...column,
              cards: column.cards.filter((card) => card.id !== action.cardId),
            }
          : column,
      );
    case "rename":
      if (!action.title.trim()) return board;
      return board.map((column) =>
        column.id === action.columnId
          ? { ...column, title: action.title.trim() }
          : column,
      );
    case "move": {
      const source = board.find((column) =>
        column.cards.some((card) => card.id === action.cardId),
      );
      const card = source?.cards.find((card) => card.id === action.cardId);
      if (
        !card ||
        source?.id === action.columnId ||
        !board.some((column) => column.id === action.columnId)
      )
        return board;
      return board.map((column) =>
        column.id === source?.id
          ? {
              ...column,
              cards: column.cards.filter((item) => item.id !== card.id),
            }
          : column.id === action.columnId
            ? { ...column, cards: [...column.cards, card] }
            : column,
      );
    }
  }
}
