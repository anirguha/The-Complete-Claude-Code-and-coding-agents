import type { Board } from "./types";

export const initialBoard: Board = {
  columns: [
    {
      id: "backlog",
      name: "Backlog",
      cards: [
        {
          id: "launch-brief",
          title: "Draft the launch brief",
          details:
            "Capture the audience, the promise, and the one metric that matters.",
        },
        {
          id: "competitor-notes",
          title: "Collect competitor notes",
          details:
            "Three products, what they do well, and where we can be clearer.",
        },
      ],
    },
    {
      id: "todo",
      name: "To Do",
      cards: [
        {
          id: "hero-copy",
          title: "Write the hero copy",
          details: "One headline, one subhead, and a single call to action.",
        },
        {
          id: "empty-states",
          title: "Design empty states",
          details: "A quiet prompt for columns that have no cards yet.",
        },
      ],
    },
    {
      id: "doing",
      name: "In Progress",
      cards: [
        {
          id: "palette",
          title: "Apply the color palette",
          details: "Navy headings, blue counts, purple actions, yellow highlights.",
        },
      ],
    },
    {
      id: "review",
      name: "Review",
      cards: [
        {
          id: "qa-pass",
          title: "QA the drag and drop",
          details: "Move a card across columns and drop one onto an empty column.",
        },
      ],
    },
    {
      id: "done",
      name: "Done",
      cards: [
        {
          id: "scaffold",
          title: "Scaffold the app",
          details: "Next.js, Tailwind, and a single client-rendered board.",
        },
        {
          id: "seed-data",
          title: "Seed the dummy board",
          details: "Five columns with a few cards so the board is never blank.",
        },
      ],
    },
  ],
};
