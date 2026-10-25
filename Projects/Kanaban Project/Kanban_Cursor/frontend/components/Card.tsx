"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useState, type ReactNode } from "react";
import type { Card } from "@/lib/types";

export function CardView({
  card,
  onDelete,
  onUpdate,
  dragging = false,
  handle,
}: {
  card: Card;
  onDelete?: (cardId: string) => void;
  onUpdate?: (cardId: string, title: string, details: string) => void;
  dragging?: boolean;
  handle?: ReactNode;
}) {
  const [editingTitle, setEditingTitle] = useState(false);
  const [editingDetails, setEditingDetails] = useState(false);
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);

  function commitTitle() {
    const next = title.trim();
    if (next && next !== card.title) onUpdate?.(card.id, next, card.details);
    else setTitle(card.title);
    setEditingTitle(false);
  }

  function commitDetails() {
    const next = details.trim();
    if (next !== card.details) onUpdate?.(card.id, card.title, next);
    setEditingDetails(false);
  }

  return (
    <article
      data-testid={`card-${card.id}`}
      className={`rounded-xl border border-navy/10 bg-card px-3.5 py-3 shadow-sm ${
        dragging ? "shadow-lg ring-2 ring-yellow" : ""
      }`}
    >
      {handle ?? (
        <div className="mb-2 flex h-6 items-center justify-center" aria-hidden="true">
          <span className="h-1 w-10 rounded-full bg-yellow" />
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        {editingTitle ? (
          <input
            aria-label="Card title"
            autoFocus
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            onBlur={commitTitle}
            onPointerDown={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.currentTarget.blur();
              if (event.key === "Escape") {
                setTitle(card.title);
                setEditingTitle(false);
              }
            }}
            className="w-full rounded-md border border-blue bg-white px-2 py-1 text-sm font-semibold text-navy outline-none"
          />
        ) : (
          <h3 className="min-w-0 flex-1 text-sm font-semibold leading-5 text-navy">
            <button
              type="button"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={() => {
                setTitle(card.title);
                setEditingTitle(true);
              }}
              className="w-full text-left"
            >
              {card.title}
            </button>
          </h3>
        )}
        {onDelete ? (
          <button
            type="button"
            aria-label={`Delete ${card.title}`}
            onPointerDown={(event) => event.stopPropagation()}
            onClick={() => onDelete(card.id)}
            className="shrink-0 text-lg leading-none text-muted hover:text-purple"
          >
            ×
          </button>
        ) : null}
      </div>
      {editingDetails ? (
        <input
          aria-label="Card details"
          autoFocus
          value={details}
          onChange={(event) => setDetails(event.target.value)}
          onBlur={commitDetails}
          onPointerDown={(event) => event.stopPropagation()}
          onKeyDown={(event) => {
            if (event.key === "Enter") event.currentTarget.blur();
            if (event.key === "Escape") {
              setDetails(card.details);
              setEditingDetails(false);
            }
          }}
          className="mt-1.5 w-full rounded-md border border-blue bg-white px-2 py-1 text-sm text-navy outline-none"
        />
      ) : (
        <button
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => {
            setDetails(card.details);
            setEditingDetails(true);
          }}
          className="mt-1.5 w-full text-left text-sm leading-5 text-muted"
        >
          {card.details || "Add details"}
        </button>
      )}
    </article>
  );
}

export function SortableCard({
  card,
  onDelete,
  onUpdate,
}: {
  card: Card;
  onDelete: (cardId: string) => void;
  onUpdate: (cardId: string, title: string, details: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
    >
      <CardView
        card={card}
        onDelete={onDelete}
        onUpdate={onUpdate}
        handle={
          <button
            type="button"
            aria-label={`Drag ${card.title}`}
            ref={setActivatorNodeRef}
            {...attributes}
            {...listeners}
            className="mb-2 flex h-6 w-full cursor-grab items-center justify-center rounded-md active:cursor-grabbing"
          >
            <span className="h-1 w-10 rounded-full bg-yellow" />
          </button>
        }
      />
    </div>
  );
}
