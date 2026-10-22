"use client";

import { useDndContext, useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useState } from "react";
import type { Column as ColumnType } from "@/lib/types";
import { CardView, SortableCard } from "./Card";

export function Column({
  column,
  interactive,
  onRename,
  onAdd,
  onDelete,
  onUpdate,
}: {
  column: ColumnType;
  interactive: boolean;
  onRename: (name: string) => void;
  onAdd: (title: string, details: string) => void;
  onDelete: (cardId: string) => void;
  onUpdate: (cardId: string, title: string, details: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(column.name);
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");

  function commitName() {
    const next = name.trim();
    if (next) onRename(next);
    else setName(column.name);
    setEditing(false);
  }

  return (
    <section
      data-testid={`column-${column.id}`}
      className="flex min-w-[250px] flex-1 flex-col rounded-2xl bg-white shadow-sm ring-1 ring-navy/5"
    >
      <header className="flex items-center gap-3 px-3.5 pt-4 pb-2">
        <div className="min-w-0 flex-1">
          {editing ? (
            <input
              aria-label="Column name"
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              onBlur={commitName}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
                if (event.key === "Escape") {
                  setName(column.name);
                  setEditing(false);
                }
              }}
              className="w-full rounded-md border border-blue bg-white px-2 py-1 text-base font-semibold text-navy outline-none"
            />
          ) : (
            <h2>
              <button
                type="button"
                onClick={() => {
                  setName(column.name);
                  setEditing(true);
                }}
                className="w-full truncate text-left text-base font-semibold text-navy"
              >
                {column.name}
              </button>
            </h2>
          )}
        </div>
        <span className="text-sm font-semibold text-blue">{column.cards.length}</span>
      </header>
      {interactive ? (
        <SortableCardList column={column} onDelete={onDelete} onUpdate={onUpdate} />
      ) : (
        <div className="flex min-h-28 flex-1 flex-col gap-2.5 overflow-y-auto px-3 py-2">
          {column.cards.map((card) => (
            <CardView key={card.id} card={card} onDelete={onDelete} onUpdate={onUpdate} />
          ))}
        </div>
      )}
      <form
        className="space-y-2 border-t border-navy/5 p-3"
        onSubmit={(event) => {
          event.preventDefault();
          const nextTitle = title.trim();
          if (!nextTitle) return;
          onAdd(nextTitle, details.trim());
          setTitle("");
          setDetails("");
        }}
      >
        <input
          aria-label="Title"
          placeholder="Title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="w-full rounded-lg border border-navy/10 px-3 py-2 text-sm text-navy outline-none placeholder:text-muted focus:border-blue"
        />
        <input
          aria-label="Details"
          placeholder="Details"
          value={details}
          onChange={(event) => setDetails(event.target.value)}
          className="w-full rounded-lg border border-navy/10 px-3 py-2 text-sm text-navy outline-none placeholder:text-muted focus:border-blue"
        />
        <button
          type="submit"
          className="w-full rounded-lg bg-purple px-3 py-2 text-sm font-semibold text-white hover:opacity-90"
        >
          Add
        </button>
      </form>
    </section>
  );
}

function SortableCardList({
  column,
  onDelete,
  onUpdate,
}: {
  column: ColumnType;
  onDelete: (cardId: string) => void;
  onUpdate: (cardId: string, title: string, details: string) => void;
}) {
  const { setNodeRef } = useDroppable({ id: column.id });
  const { active, over } = useDndContext();
  const overThisColumn =
    over?.id === column.id || column.cards.some((card) => card.id === over?.id);
  const highlighted = Boolean(active) && overThisColumn;

  return (
    <div
      ref={setNodeRef}
      className={`flex min-h-28 flex-1 flex-col gap-2.5 overflow-y-auto px-3 py-2 ${
        highlighted ? "rounded-xl ring-2 ring-yellow" : ""
      }`}
    >
      <SortableContext
        items={column.cards.map((card) => card.id)}
        strategy={verticalListSortingStrategy}
      >
        {column.cards.map((card) => (
          <SortableCard key={card.id} card={card} onDelete={onDelete} onUpdate={onUpdate} />
        ))}
      </SortableContext>
    </div>
  );
}
