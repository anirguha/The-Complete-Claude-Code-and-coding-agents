"use client";

import Link from "next/link";
import {
  useEffect,
  useId,
  useReducer,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  closestCenter,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  pointerWithin,
  useDroppable,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
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
import { initialBoard } from "../lib/initialData";
import { kanbanReducer } from "../lib/kanbanReducer";
import { Card, Column } from "../lib/types";

function useInteractive() {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

function CardView({
  card,
  onDelete,
  dragging = false,
}: {
  card: Card;
  onDelete?: () => void;
  dragging?: boolean;
}) {
  return (
    <article
      className={`card ${dragging ? "is-dragging card-overlay" : ""}`}
      data-testid={`card-${card.id}`}
    >
      <div className="card-tools">
        <span className="icon-button drag-handle">
          <GripVertical size={16} />
        </span>
        {onDelete && (
          <button
            className="icon-button delete-button"
            aria-label={`Delete ${card.title}`}
            onClick={onDelete}
            type="button"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
      <h3>{card.title}</h3>
      {card.details ? <p>{card.details}</p> : null}
    </article>
  );
}

function SortableCardItem({
  card,
  onDelete,
}: {
  card: Card;
  onDelete: () => void;
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
        opacity: isDragging ? 0.35 : 1,
      }}
    >
      <article
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
            type="button"
          >
            <GripVertical size={16} />
          </button>
          <button
            className="icon-button delete-button"
            aria-label={`Delete ${card.title}`}
            onClick={onDelete}
            type="button"
          >
            <Trash2 size={14} />
          </button>
        </div>
        <h3>{card.title}</h3>
        {card.details ? <p>{card.details}</p> : null}
      </article>
    </div>
  );
}

function ColumnContainer({
  column,
  index,
  interactive,
  onAddCard,
  onRenameColumn,
  onDeleteCard,
}: {
  column: Column;
  index: number;
  interactive: boolean;
  onAddCard: () => void;
  onRenameColumn: (newTitle: string) => void;
  onDeleteCard: (cardId: string) => void;
}) {
  const { setNodeRef } = useDroppable({ id: column.id });

  const [isEditing, setIsEditing] = useState(false);
  const [columnName, setColumnName] = useState(column.title);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  function handleSaveRename() {
    const trimmed = columnName.trim();
    if (!trimmed) {
      setError("Please enter a column name.");
      return;
    }
    setError("");
    onRenameColumn(trimmed);
    setIsEditing(false);
  }

  function handleCancelRename() {
    setError("");
    setColumnName(column.title);
    setIsEditing(false);
  }

  function handleBlur() {
    const trimmed = columnName.trim();
    if (!trimmed) {
      setColumnName(column.title);
      setError("");
      setIsEditing(false);
    } else {
      handleSaveRename();
    }
  }

  return (
    <section
      className={`column column-${index}`}
      aria-label={column.title}
      data-testid={`column-${column.id}`}
    >
      <div className="column-heading">
        <span className="status-dot">
          {index === 4 && <Check size={10} strokeWidth={3} />}
        </span>

        {isEditing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSaveRename();
            }}
            className="column-rename-form"
          >
            <input
              ref={inputRef}
              value={columnName}
              onChange={(e) => {
                setColumnName(e.target.value);
                setError("");
              }}
              onBlur={handleBlur}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSaveRename();
                }
                if (e.key === "Escape") {
                  handleCancelRename();
                }
              }}
              aria-label="Column name"
              className="column-rename-input"
              aria-invalid={!!error}
            />
            <button
              type="submit"
              className="icon-button save-rename-btn"
              aria-label="Save name"
              title="Save name"
              onMouseDown={(e) => e.preventDefault()}
            >
              <Check size={15} strokeWidth={2.5} />
            </button>
            <button
              type="button"
              className="icon-button cancel-rename-btn"
              aria-label="Cancel rename"
              title="Cancel"
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleCancelRename}
            >
              <X size={15} strokeWidth={2.5} />
            </button>
          </form>
        ) : (
          <div className="column-title-group">
            <button
              type="button"
              className="column-title-btn"
              onClick={() => {
                setColumnName(column.title);
                setIsEditing(true);
              }}
              title="Click to rename"
            >
              <h2>{column.title}</h2>
            </button>
            <button
              className="icon-button rename-button"
              aria-label={`Rename ${column.title}`}
              onClick={() => {
                setColumnName(column.title);
                setIsEditing(true);
              }}
              type="button"
              title="Rename column"
            >
              <Pencil size={13} />
            </button>
          </div>
        )}

        <span className="column-count">{column.cards.length}</span>
      </div>

      {error && isEditing && (
        <div role="alert" className="form-error" style={{ marginBottom: 8 }}>
          {error}
        </div>
      )}

      <div
        ref={setNodeRef}
        className="card-list"
        data-testid={`drop-${column.id}`}
      >
        {interactive ? (
          <SortableContext
            items={column.cards.map((c) => c.id)}
            strategy={verticalListSortingStrategy}
          >
            {column.cards.map((card) => (
              <SortableCardItem
                key={card.id}
                card={card}
                onDelete={() => onDeleteCard(card.id)}
              />
            ))}
          </SortableContext>
        ) : (
          column.cards.map((card) => (
            <CardView
              key={card.id}
              card={card}
              onDelete={() => onDeleteCard(card.id)}
            />
          ))
        )}

        {column.cards.length === 0 && (
          <div className="empty-column">
            <Layers2 size={24} />
            <p>No cards in this column.</p>
            <span>Add a new card or drag one here.</span>
          </div>
        )}
      </div>

      <button className="add-card-button" onClick={onAddCard} type="button">
        <Plus size={16} /> Add card
      </button>
    </section>
  );
}

function AddCardModal({
  column,
  onClose,
  onSave,
}: {
  column: Column;
  onClose: () => void;
  onSave: (title: string, details: string) => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const titleId = useId();
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      dialog.showModal();
    }
    inputRef.current?.focus();
    return () => {
      if (dialog && dialog.open) {
        dialog.close();
      }
    };
  }, []);

  function handleClose() {
    if (dialogRef.current?.open) {
      dialogRef.current.close();
    }
    onClose();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please enter a title.");
      return;
    }
    onSave(title, details);
    handleClose();
  }

  return (
    <dialog
      ref={dialogRef}
      className="editor-dialog"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        handleClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <form noValidate onSubmit={handleSubmit}>
        <div className="dialog-heading">
          <div>
            <span className="eyebrow">{column.title}</span>
            <h2 id={titleId}>Create a new card</h2>
          </div>
          <button
            className="icon-button"
            type="button"
            aria-label="Close dialog"
            onClick={handleClose}
          >
            <X size={20} />
          </button>
        </div>

        <label htmlFor="modal-title">Card title</label>
        <input
          id="modal-title"
          ref={inputRef}
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setError("");
          }}
          placeholder="What task needs to be completed?"
          aria-invalid={!!error}
          aria-describedby={error ? "title-error" : undefined}
        />
        {error && (
          <p id="title-error" role="alert" className="form-error">
            {error}
          </p>
        )}

        <label htmlFor="modal-details">
          Details <span>(optional)</span>
        </label>
        <textarea
          id="modal-details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          placeholder="Add relevant context, acceptance criteria, or links"
          rows={4}
        />

        <div className="dialog-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={handleClose}
          >
            Cancel
          </button>
          <button className="primary-button" type="submit">
            Add card
            <ArrowUpRight size={16} />
          </button>
        </div>
      </form>
    </dialog>
  );
}

export default function Home() {
  const [board, dispatch] = useReducer(kanbanReducer, initialBoard);
  const [addCardColumn, setAddCardColumn] = useState<Column | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const interactive = useInteractive();

  const lastTriggerRef = useRef<HTMLButtonElement | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const collisionDetection: CollisionDetection = (args) => {
    if (args.pointerCoordinates) {
      const pointerHits = pointerWithin(args);
      const hoveredColumn =
        board.find((column) =>
          pointerHits.some((hit) => String(hit.id) === column.id),
        ) ??
        board.find((column) =>
          column.cards.some((card) =>
            pointerHits.some((hit) => String(hit.id) === card.id),
          ),
        );

      if (!hoveredColumn) return [];

      const activeCardId = String(args.active.id);
      const containsActive = hoveredColumn.cards.some(
        (card) => card.id === activeCardId,
      );
      const columnContainer = args.droppableContainers.find(
        (c) => String(c.id) === hoveredColumn.id,
      );
      const fallbackHit = columnContainer
        ? [{ id: columnContainer.id, data: { droppableContainer: columnContainer } }]
        : [];

      if (
        hoveredColumn.cards.length === 0 ||
        (containsActive && hoveredColumn.cards.length === 1)
      ) {
        const columnHit = pointerHits.find(
          (hit) => String(hit.id) === hoveredColumn.id,
        );
        return columnHit ? [columnHit] : fallbackHit;
      }

      const closest = closestCenter({
        ...args,
        droppableContainers: args.droppableContainers.filter((container) =>
          hoveredColumn.cards.some((card) => card.id === String(container.id)),
        ),
      });
      const winner = closest[0];
      if (winner && String(winner.id) !== activeCardId) return [winner];

      const columnHit = pointerHits.find(
        (hit) => String(hit.id) === hoveredColumn.id,
      );
      return columnHit ? [columnHit] : fallbackHit;
    }

    return closestCenter(args);
  };

  const activeCard = activeId
    ? board.flatMap((col) => col.cards).find((card) => card.id === activeId)
    : undefined;

  const totalCards = board.reduce((sum, col) => sum + col.cards.length, 0);

  function openAddModal(column: Column, trigger?: HTMLButtonElement | null) {
    if (trigger) lastTriggerRef.current = trigger;
    setAddCardColumn(column);
  }

  function closeAddModal() {
    setAddCardColumn(null);
    lastTriggerRef.current?.focus();
  }

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const cardId = String(active.id);
    const overId = String(over.id);

    if (cardId === overId) return;

    dispatch({
      type: "move",
      activeId: cardId,
      overId,
    });
  }

  const columnsMarkup = (
    <div className="board" aria-label="Project board">
      {board.map((column, index) => (
        <ColumnContainer
          key={column.id}
          column={column}
          index={index}
          interactive={interactive}
          onAddCard={() => openAddModal(column)}
          onRenameColumn={(title) =>
            dispatch({
              type: "rename",
              columnId: column.id,
              title,
            })
          }
          onDeleteCard={(cardId) =>
            dispatch({ type: "delete", cardId })
          }
        />
      ))}
    </div>
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="Antigravity Kanban home">
          <span className="brand-mark">
            <Columns3 size={18} />
          </span>
          antigravity<span className="brand-period">.</span>
        </Link>
        <span className="topbar-divider" />
        <span className="workspace-label">Team Workspace</span>
        <span className="topbar-note">
          <span className="topbar-dot" /> Antigravity Project Board
        </span>
      </header>

      <main>
        <div className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="eyebrow-accent" /> Streamlined Project Flow
            </div>
            <h1>
              Execution starts here<span>.</span>
            </h1>
            <p className="heading-description">
              A clean, focused space to coordinate tasks and maintain team momentum.
            </p>
          </div>
          <button
            className="primary-button"
            onClick={(e) => openAddModal(board[0], e.currentTarget)}
            type="button"
          >
            <Plus size={16} />
            New card
          </button>
        </div>

        <div className="board-toolbar">
          <div className="board-tab">
            <Columns3 size={16} />
            Project board<span className="board-total">{totalCards}</span>
          </div>
          <span className="board-hint">
            Drag cards within or between columns
            <ArrowDown size={14} />
          </span>
        </div>

        {interactive ? (
          <DndContext
            id="antigravity-board"
            sensors={sensors}
            collisionDetection={collisionDetection}
            onDragStart={handleDragStart}
            onDragCancel={() => setActiveId(null)}
            onDragEnd={handleDragEnd}
          >
            {columnsMarkup}
            <DragOverlay dropAnimation={null}>
              {activeCard ? <CardView card={activeCard} dragging /> : null}
            </DragOverlay>
          </DndContext>
        ) : (
          columnsMarkup
        )}

        <footer className="board-footer">
          <span className="footer-tip">
            <GripVertical size={14} />
            Use handles to arrange cards within columns or move across columns.
          </span>
          <span>Antigravity Kanban MVP</span>
        </footer>
      </main>

      {addCardColumn && (
        <AddCardModal
          column={addCardColumn}
          onClose={closeAddModal}
          onSave={(title, details) => {
            dispatch({
              type: "add",
              columnId: addCardColumn.id,
              card: {
                id: `card-${crypto.randomUUID()}`,
                title,
                details,
              },
            });
          }}
        />
      )}
    </div>
  );
}
