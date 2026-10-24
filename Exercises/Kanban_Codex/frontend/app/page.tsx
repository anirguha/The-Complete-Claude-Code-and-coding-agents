"use client";

import Link from "next/link";
import { useEffect, useId, useReducer, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  pointerWithin,
  rectIntersection,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type KeyboardCoordinateGetter,
} from "@dnd-kit/core";
import {
  ArrowDown,
  ArrowUpRight,
  Check,
  Columns3,
  GripVertical,
  Layers2,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import {
  boardReducer,
  initialBoard,
  type Card,
  type Column,
} from "./board-state";

type Editor = { kind: "add" | "rename"; column: Column };
const keyboardCoordinates: KeyboardCoordinateGetter = (event, { context }) => {
  const direction =
    event.code === "ArrowRight" ? 1 : event.code === "ArrowLeft" ? -1 : 0;
  if (!direction) return;
  event.preventDefault();
  const ids = initialBoard.map((column) => column.id);
  const current = String(
    context.over?.id ?? context.active?.data.current?.columnId,
  );
  const target = ids[ids.indexOf(current) + direction];
  const rect = context.droppableRects.get(target);
  if (!rect || !context.collisionRect) return;
  return {
    x: rect.left + (rect.width - context.collisionRect.width) / 2,
    y: rect.top + 20,
  };
};

function CardView({
  card,
  overlay = false,
}: {
  card: Card;
  overlay?: boolean;
}) {
  return (
    <div className={overlay ? "card card-overlay" : "card-content"}>
      <h3>{card.title}</h3>
      <p>{card.details}</p>
    </div>
  );
}
function BoardCard({
  card,
  columnId,
  onDelete,
}: {
  card: Card;
  columnId: string;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, isDragging } =
    useDraggable({ id: card.id, data: { columnId } });
  return (
    <article
      ref={setNodeRef}
      className={`card ${isDragging ? "is-dragging" : ""}`}
      data-testid={`card-${card.id}`}
    >
      <div className="card-tools">
        <button
          ref={setActivatorNodeRef}
          className="icon-button drag-handle"
          {...attributes}
          {...listeners}
          aria-label={`Move ${card.title}`}
        >
          <GripVertical size={16} />
        </button>
        <button
          className="icon-button delete-button"
          aria-label={`Delete ${card.title}`}
          onClick={onDelete}
        >
          <Trash2 size={14} />
        </button>
      </div>
      <CardView card={card} />
    </article>
  );
}
function BoardColumn({
  column,
  index,
  onEdit,
  onDelete,
}: {
  column: Column;
  index: number;
  onEdit: (kind: Editor["kind"], column: Column) => void;
  onDelete: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  return (
    <section
      className={`column column-${index} ${isOver ? "is-over" : ""}`}
      aria-label={column.title}
      data-testid={`column-${column.id}`}
    >
      <div className="column-heading">
        <span className="status-dot">
          {index === 4 && <Check size={10} strokeWidth={3} />}
        </span>
        <h2>{column.title}</h2>
        <span className="count">{column.cards.length}</span>
        <button
          className="icon-button rename-button"
          aria-label={`Rename ${column.title}`}
          onClick={() => onEdit("rename", column)}
        >
          <Pencil size={14} />
        </button>
      </div>
      <div
        ref={setNodeRef}
        className="card-list"
        data-testid={`drop-${column.id}`}
      >
        {column.cards.map((card) => (
          <BoardCard
            key={card.id}
            card={card}
            columnId={column.id}
            onDelete={() => onDelete(card.id)}
          />
        ))}
        {!column.cards.length && (
          <div className="empty-column">
            <Layers2 size={22} />
            <p>A little breathing room.</p>
            <span>Add a card or drop one here.</span>
          </div>
        )}
      </div>
      <button className="add-card" onClick={() => onEdit("add", column)}>
        <Plus size={16} /> Add card
      </button>
    </section>
  );
}
function EditorDialog({
  editor,
  onClose,
  onSave,
}: {
  editor: Editor;
  onClose: () => void;
  onSave: (title: string, details: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(
    editor.kind === "rename" ? editor.column.title : "",
  );
  const [details, setDetails] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    ref.current?.showModal();
    inputRef.current?.focus();
  }, []);
  function close() {
    ref.current?.close();
    onClose();
  }
  return (
    <dialog
      ref={ref}
      className="editor-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (!title.trim()) {
            setError("Please enter a title.");
            return;
          }
          onSave(title, details);
          close();
        }}
      >
        <div className="dialog-heading">
          <div>
            <span className="eyebrow">{editor.column.title}</span>
            <h2 id={titleId}>
              {editor.kind === "add"
                ? "Make space for an idea."
                : "Give this column a name."}
            </h2>
          </div>
          <button
            className="icon-button"
            type="button"
            aria-label="Close dialog"
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <label htmlFor="editor-title">
          {editor.kind === "add" ? "Card title" : "Column name"}
        </label>
        <input
          id="editor-title"
          ref={inputRef}
          value={title}
          onChange={(event) => {
            setTitle(event.target.value);
            setError("");
          }}
          placeholder="What needs to happen?"
          aria-invalid={!!error}
          aria-describedby={error ? "title-error" : undefined}
        />
        {error && (
          <p id="title-error" role="alert" className="form-error">
            {error}
          </p>
        )}
        {editor.kind === "add" && (
          <>
            <label htmlFor="editor-details">
              Details <span>(optional)</span>
            </label>
            <textarea
              id="editor-details"
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              placeholder="A little context goes a long way."
              rows={4}
            />
          </>
        )}
        <div className="dialog-actions">
          <button className="secondary-button" type="button" onClick={close}>
            Cancel
          </button>
          <button className="primary-button" type="submit">
            {editor.kind === "add" ? "Add card" : "Save name"}
            <ArrowUpRight size={16} />
          </button>
        </div>
      </form>
    </dialog>
  );
}
export default function Home() {
  const [board, dispatch] = useReducer(boardReducer, initialBoard);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: keyboardCoordinates,
      scrollBehavior: "auto",
    }),
  );
  const activeCard = board
    .flatMap((column) => column.cards)
    .find((card) => card.id === activeId);
  const total = board.reduce((sum, column) => sum + column.cards.length, 0);
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="Forma home">
          <span className="brand-mark">
            <Columns3 size={19} />
          </span>
          forma<span className="brand-period">.</span>
        </Link>
        <span className="topbar-divider" />
        <span className="workspace-label">Your workspace</span>
        <span className="topbar-note">
          <span /> A little clarity, every day
        </span>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="small-line" /> SPACE TO MAKE THINGS HAPPEN
            </div>
            <h1>
              Good work starts here<span>.</span>
            </h1>
            <p>A home for your ideas. A little momentum for your day.</p>
          </div>
          <button
            className="primary-button new-card"
            onClick={() => setEditor({ kind: "add", column: board[0] })}
          >
            <Plus size={17} />
            New card
          </button>
        </div>
        <div className="board-toolbar">
          <div className="board-tab">
            <Columns3 size={17} />
            Project board<span className="board-total">{total}</span>
          </div>
          <span className="board-hint">
            Small steps. Steady progress.
            <ArrowDown size={14} />
          </span>
        </div>
        <DndContext
          id="forma-board"
          sensors={sensors}
          collisionDetection={(args) =>
            args.pointerCoordinates
              ? pointerWithin(args)
              : rectIntersection(args)
          }
          onDragStart={(event) => setActiveId(String(event.active.id))}
          onDragCancel={() => setActiveId(null)}
          onDragEnd={(event) => {
            if (event.over)
              dispatch({
                type: "move",
                cardId: String(event.active.id),
                columnId: String(event.over.id),
              });
            setActiveId(null);
          }}
          accessibility={{
            screenReaderInstructions: {
              draggable:
                "Press Space to pick up a card. Use Left and Right arrows to choose a column. Press Space to drop, or Escape to cancel.",
            },
          }}
        >
          <div className="board" aria-label="Project board">
            {board.map((column, index) => (
              <BoardColumn
                key={column.id}
                column={column}
                index={index}
                onEdit={(kind, column) => setEditor({ kind, column })}
                onDelete={(cardId) => dispatch({ type: "delete", cardId })}
              />
            ))}
          </div>
          <DragOverlay dropAnimation={null}>
            {activeCard ? <CardView card={activeCard} overlay /> : null}
          </DragOverlay>
        </DndContext>
        <footer className="board-footer">
          <span>
            <GripVertical size={14} />
            Grab a handle. Move an idea forward.
          </span>
          <span>Made for a clearer mind.</span>
        </footer>
      </main>
      {editor && (
        <EditorDialog
          editor={editor}
          onClose={() => setEditor(null)}
          onSave={(title, details) => {
            if (editor.kind === "rename")
              dispatch({ type: "rename", columnId: editor.column.id, title });
            else
              dispatch({
                type: "add",
                columnId: editor.column.id,
                card: { id: crypto.randomUUID(), title, details },
              });
          }}
        />
      )}
    </div>
  );
}
