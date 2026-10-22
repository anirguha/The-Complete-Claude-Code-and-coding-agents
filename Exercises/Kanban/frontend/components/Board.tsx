"use client";

import {
  closestCenter,
  DndContext,
  DragOverlay,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useState, useSyncExternalStore } from "react";
import { addCard, deleteCard, moveCard, renameColumn, updateCard } from "@/lib/board";
import { initialBoard } from "@/lib/dummy-data";
import type { Board as BoardType } from "@/lib/types";
import { CardView } from "./Card";
import { Column } from "./Column";

function useInteractive() {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

export function Board() {
  const [board, setBoard] = useState<BoardType>(initialBoard);
  const [activeId, setActiveId] = useState<string | null>(null);
  const interactive = useInteractive();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const collisionDetection: CollisionDetection = (args) => {
    const activeId = String(args.active.id);
    const pointerHits = pointerWithin(args);
    const hoveredColumn =
      board.columns.find((column) =>
        pointerHits.some((hit) => String(hit.id) === column.id),
      ) ??
      board.columns.find((column) =>
        column.cards.some((card) => pointerHits.some((hit) => String(hit.id) === card.id)),
      );

    if (!hoveredColumn) return closestCenter(args);

    const containsActive = hoveredColumn.cards.some((card) => card.id === activeId);
    if (hoveredColumn.cards.length === 0 || (containsActive && hoveredColumn.cards.length === 1)) {
      const columnHit = pointerHits.find((hit) => String(hit.id) === hoveredColumn.id);
      return columnHit ? [columnHit] : [];
    }

    const closest = closestCenter({
      ...args,
      droppableContainers: args.droppableContainers.filter((container) =>
        hoveredColumn.cards.some((card) => card.id === String(container.id)),
      ),
    });
    const winner = closest[0];
    if (!winner || String(winner.id) === activeId) return [];
    return [winner];
  };

  const activeCard = activeId
    ? board.columns.flatMap((column) => column.cards).find((card) => card.id === activeId)
    : undefined;

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const cardId = String(active.id);
    const overId = String(over.id);

    setBoard((current) => {
      const fromColumn = current.columns.find((column) =>
        column.cards.some((card) => card.id === cardId),
      );
      if (!fromColumn) return current;

      const toColumn =
        current.columns.find((column) => column.id === overId) ??
        current.columns.find((column) => column.cards.some((card) => card.id === overId));
      if (!toColumn) return current;

      if (fromColumn.id === toColumn.id) {
        const oldIndex = fromColumn.cards.findIndex((card) => card.id === cardId);
        const newIndex = fromColumn.cards.findIndex((card) => card.id === overId);
        if (newIndex < 0 || oldIndex === newIndex) return current;
        return moveCard(current, fromColumn.id, toColumn.id, cardId, newIndex);
      }

      const overIndex = toColumn.cards.findIndex((card) => card.id === overId);
      const index = overIndex < 0 ? toColumn.cards.length : overIndex;
      return moveCard(current, fromColumn.id, toColumn.id, cardId, index);
    });
  }

  const columns = (
    <BoardColumns
      board={board}
      interactive={interactive}
      onRename={(columnId, name) =>
        setBoard((current) => renameColumn(current, columnId, name))
      }
      onAdd={(columnId, title, details) =>
        setBoard((current) => addCard(current, columnId, title, details))
      }
      onDelete={(columnId, cardId) =>
        setBoard((current) => deleteCard(current, columnId, cardId))
      }
      onUpdate={(columnId, cardId, title, details) =>
        setBoard((current) => updateCard(current, columnId, cardId, title, details))
      }
    />
  );

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b-4 border-yellow bg-white px-8 py-5">
        <p className="text-xs font-semibold tracking-[0.22em] text-blue uppercase">
          Single board
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Kanban</h1>
      </header>
      {interactive ? (
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={() => setActiveId(null)}
        >
          {columns}
          <DragOverlay>
            {activeCard ? <CardView card={activeCard} dragging /> : null}
          </DragOverlay>
        </DndContext>
      ) : (
        columns
      )}
    </div>
  );
}

function BoardColumns({
  board,
  interactive,
  onRename,
  onAdd,
  onDelete,
  onUpdate,
}: {
  board: BoardType;
  interactive: boolean;
  onRename: (columnId: string, name: string) => void;
  onAdd: (columnId: string, title: string, details: string) => void;
  onDelete: (columnId: string, cardId: string) => void;
  onUpdate: (columnId: string, cardId: string, title: string, details: string) => void;
}) {
  return (
    <main className="flex min-h-0 flex-1 gap-4 overflow-x-auto px-6 py-6">
      {board.columns.map((column) => (
        <Column
          key={column.id}
          column={column}
          interactive={interactive}
          onRename={(name) => onRename(column.id, name)}
          onAdd={(title, details) => onAdd(column.id, title, details)}
          onDelete={(cardId) => onDelete(column.id, cardId)}
          onUpdate={(cardId, title, details) => onUpdate(column.id, cardId, title, details)}
        />
      ))}
    </main>
  );
}
