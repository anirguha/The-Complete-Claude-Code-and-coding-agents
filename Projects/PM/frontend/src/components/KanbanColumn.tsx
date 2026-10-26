import { useRef, useState } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onEditCard: (cardId: string, title: string, details: string) => void;
};

const ColumnTitleInput = ({
  title,
  onCommit,
}: {
  title: string;
  onCommit: (title: string) => void;
}) => {
  const [draft, setDraft] = useState<string | null>(null);
  const cancelled = useRef(false);

  return (
    <input
      value={draft ?? title}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        const next = draft?.trim();
        if (!cancelled.current && next && next !== title) onCommit(next);
        cancelled.current = false;
        setDraft(null);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") cancelled.current = true;
        if (event.key === "Enter" || event.key === "Escape") {
          event.currentTarget.blur();
        }
      }}
      maxLength={100}
      className="mt-3 w-full bg-transparent font-display text-lg font-semibold text-[var(--navy-dark)] outline-none"
      aria-label="Column title"
    />
  );
};

export const KanbanColumn = ({
  column,
  cards,
  onRename,
  onAddCard,
  onDeleteCard,
  onEditCard,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[360px] min-w-0 flex-col md:min-h-[520px] rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-4 shadow-[var(--shadow)] transition",
        isOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-3">
            <div className="h-2 w-10 rounded-full bg-[var(--accent-yellow)]" />
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              {cards.length} cards
            </span>
          </div>
          <ColumnTitleInput
            title={column.title}
            onCommit={(title) => onRename(column.id, title)}
          />
        </div>
      </div>
      <div className="mt-4 flex flex-1 flex-col gap-3">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onEdit={onEditCard}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
