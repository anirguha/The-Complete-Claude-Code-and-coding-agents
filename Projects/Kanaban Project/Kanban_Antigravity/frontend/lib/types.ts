export interface Card {
  id: string;
  title: string;
  details: string;
}

export interface Column {
  id: string;
  title: string;
  cards: Card[];
}

export type BoardAction =
  | { type: "add"; columnId: string; card: Card }
  | { type: "delete"; cardId: string }
  | { type: "rename"; columnId: string; title: string }
  | { type: "move"; activeId: string; overId: string }
  | { type: "reset" };
