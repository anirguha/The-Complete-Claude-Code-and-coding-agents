import { useState, type FormEvent } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit: (cardId: string, title: string, details: string) => void;
};

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, disabled: editing });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const startEditing = () => {
    setTitle(card.title);
    setDetails(card.details);
    setEditing(true);
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...(editing ? {} : attributes)}
      {...(editing ? {} : listeners)}
      data-testid={`card-${card.id}`}
    >
      {editing ? (
        <form
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            if (!title.trim()) return;
            onEdit(card.id, title.trim(), details.trim());
            setEditing(false);
          }}
          className="space-y-3"
        >
          <input
            aria-label={`Title for ${card.title}`}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
            maxLength={200}
            className="w-full rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm"
          />
          <textarea
            aria-label={`Details for ${card.title}`}
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            maxLength={5000}
            rows={3}
            className="w-full resize-none rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-xs font-semibold text-white"
            >
              Save changes
            </button>
            <button
              type="button"
              onClick={() => {
                setTitle(card.title);
                setDetails(card.details);
                setEditing(false);
              }}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="min-w-0">
            <h4
              className="break-words font-display text-base font-semibold text-[var(--navy-dark)]"
              onDoubleClick={startEditing}
              title="Double-click to rename"
            >
              {card.title}
            </h4>
            <p className="mt-2 break-words text-sm leading-6 text-[var(--gray-text)]">
              {card.details}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={startEditing}
              className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
              aria-label={`Edit ${card.title}`}
            >
              Rename / Edit
            </button>
            <button
              type="button"
              onClick={() => onDelete(card.id)}
              className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--navy-dark)] hover:text-[var(--navy-dark)]"
              aria-label={`Delete ${card.title}`}
            >
              Remove
            </button>
          </div>
        </div>
      )}
    </article>
  );
};
