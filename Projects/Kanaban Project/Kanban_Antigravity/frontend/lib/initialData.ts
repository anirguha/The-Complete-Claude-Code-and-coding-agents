import { Column } from "./types";

export const initialBoard: Column[] = [
  {
    id: "backlog",
    title: "Backlog",
    cards: [
      {
        id: "card-1",
        title: "Explore agent orchestration workflows",
        details: "Analyze multi-agent coordination patterns and state propagation between tasks.",
      },
      {
        id: "card-2",
        title: "Refactor telemetry pipeline",
        details: "Streamline event logging to minimize overhead and improve payload consistency.",
      },
      {
        id: "card-3",
        title: "Audit keyboard navigation flows",
        details: "Ensure every interactive control is fully operable via tab and arrow keys.",
      },
    ],
  },
  {
    id: "ready",
    title: "Ready",
    cards: [
      {
        id: "card-4",
        title: "Define brand typography tokens",
        details: "Consolidate heading hierarchy, line heights, and letter spacing tokens.",
      },
      {
        id: "card-5",
        title: "Implement drag overlay feedback",
        details: "Provide visual cues during active dragging with subtle elevation and tilt.",
      },
    ],
  },
  {
    id: "in-progress",
    title: "In Progress",
    cards: [
      {
        id: "card-6",
        title: "Construct accessible modal dialogs",
        details: "Implement native dialog elements with backdrop blur and focus restoration.",
      },
      {
        id: "card-7",
        title: "Design responsive column layout",
        details: "Enable smooth horizontal scrolling on smaller viewports with scroll snapping.",
      },
    ],
  },
  {
    id: "in-review",
    title: "In Review",
    cards: [
      {
        id: "card-8",
        title: "Validate color contrast ratios",
        details: "Verify all text elements satisfy WCAG AA contrast standards against backgrounds.",
      },
    ],
  },
  {
    id: "done",
    title: "Done",
    cards: [
      {
        id: "card-9",
        title: "Scaffold Next.js project architecture",
        details: "Set up client-rendered application baseline with TypeScript and Vitest tooling.",
      },
    ],
  },
];
