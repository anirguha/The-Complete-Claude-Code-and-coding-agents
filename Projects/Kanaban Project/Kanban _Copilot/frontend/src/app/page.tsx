"use client";

import { useState, type DragEvent, type FormEvent, type KeyboardEvent } from "react";
import {
  addCard,
  deleteCard,
  initialBoard,
  moveCard,
  renameColumn,
  type ColumnId,
} from "@/lib/board";
import styles from "./page.module.css";

function Icon({
  name,
  size = 16,
}: {
  name: "plus" | "edit" | "grip" | "trash";
  size?: number;
}) {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    edit: <path d="m15 5 4 4M4 20l4.5-1 10.7-10.7a2.1 2.1 0 0 0-3-3L5.5 16 4 20Z" />,
    grip: (
      <>
        <circle cx="9" cy="6" r="1" />
        <circle cx="15" cy="6" r="1" />
        <circle cx="9" cy="12" r="1" />
        <circle cx="15" cy="12" r="1" />
        <circle cx="9" cy="18" r="1" />
        <circle cx="15" cy="18" r="1" />
      </>
    ),
    trash: <path d="M4 7h16M10 11v6M14 11v6M5 7l1 13h12l1-13M9 7V4h6v3" />,
  };

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

export default function Home() {
  const [board, setBoard] = useState(initialBoard);
  const [newCardColumn, setNewCardColumn] = useState<ColumnId | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newDetails, setNewDetails] = useState("");
  const [editingColumn, setEditingColumn] = useState<ColumnId | null>(null);
  const [columnDraft, setColumnDraft] = useState("");
  const [draggingOver, setDraggingOver] = useState<ColumnId | null>(null);

  const totalCards = board.columns.reduce((total, column) => total + column.cards.length, 0);

  function submitNewCard(event: FormEvent<HTMLFormElement>, columnId: ColumnId) {
    event.preventDefault();
    if (!newTitle.trim()) return;

    setBoard((current) =>
      addCard(current, columnId, {
        id: crypto.randomUUID(),
        title: newTitle.trim(),
        details: newDetails.trim(),
      }),
    );
    setNewTitle("");
    setNewDetails("");
    setNewCardColumn(null);
  }

  function saveColumnName(event: FormEvent<HTMLFormElement>, columnId: ColumnId) {
    event.preventDefault();
    if (columnDraft.trim()) {
      setBoard((current) => renameColumn(current, columnId, columnDraft.trim()));
    }
    setEditingColumn(null);
  }

  function cancelColumnEdit(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setEditingColumn(null);
    }
  }

  function handleDrop(event: DragEvent<HTMLElement>, destinationId: ColumnId, beforeCardId?: string) {
    event.preventDefault();
    event.stopPropagation();
    const sourceId = event.dataTransfer.getData("application/x-kanban-column") as ColumnId;
    const cardId = event.dataTransfer.getData("text/plain");
    if (sourceId && cardId) {
      setBoard((current) => moveCard(current, sourceId, destinationId, cardId, beforeCardId));
    }
    setDraggingOver(null);
  }

  return (
    <main className={styles.app}>
      <header className={styles.topbar}>
        <a className={styles.brand} href="#" aria-label="Northstar home">
          <span className={styles.brandMark} aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </span>
          <span className={styles.brandName}>northstar</span>
        </a>
        <div className={styles.topbarRight}>
          <span className={styles.workspaceLabel}>WORKSPACE</span>
          <span className={styles.workspaceName}>Studio team</span>
          <span className={styles.avatar} aria-label="Alex Morgan">
            AM
          </span>
        </div>
      </header>

      <div className={styles.workspace}>
        <nav className={styles.breadcrumb} aria-label="Breadcrumb">
          <span>Projects</span>
          <span className={styles.breadcrumbDivider}>/</span>
          <span className={styles.breadcrumbCurrent}>Product launch</span>
        </nav>

        <section className={styles.boardHeading} aria-labelledby="board-title">
          <div>
            <div className={styles.eyebrow}>
              <span className={styles.projectDot} />
              PRODUCT TEAM
            </div>
            <h1 id="board-title">Product launch</h1>
            <p className={styles.boardSubtitle}>
              A clear view of what we&apos;re making and what comes next.
            </p>
          </div>
          <div className={styles.boardStats}>
            <div className={styles.stat}>
              <span className={styles.statValue}>{totalCards}</span>
              <span className={styles.statLabel}>tasks on board</span>
            </div>
            <span className={styles.statDivider} />
            <div className={styles.updated}>
              <span className={styles.updatedDot} />
              Up to date
            </div>
          </div>
        </section>

        <section className={styles.board} aria-label="Kanban board">
          {board.columns.map((column, index) => (
            <section
              className={`${styles.column} ${draggingOver === column.id ? styles.columnOver : ""}`}
              key={column.id}
              aria-label={`${column.name} column`}
              onDragOver={(event) => {
                event.preventDefault();
                setDraggingOver(column.id);
              }}
              onDragLeave={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                  setDraggingOver(null);
                }
              }}
              onDrop={(event) => handleDrop(event, column.id)}
            >
              <header className={styles.columnHeader}>
                <div className={styles.columnTitleArea}>
                  <span className={`${styles.columnMarker} ${styles[`marker${index}`]}`} />
                  {editingColumn === column.id ? (
                    <form
                      onSubmit={(event) => saveColumnName(event, column.id)}
                      className={styles.renameForm}
                    >
                      <input
                        aria-label="Column name"
                        autoFocus
                        maxLength={28}
                        value={columnDraft}
                        onChange={(event) => setColumnDraft(event.target.value)}
                        onKeyDown={cancelColumnEdit}
                        onBlur={() => {
                          if (columnDraft.trim()) {
                            setBoard((current) => renameColumn(current, column.id, columnDraft.trim()));
                          }
                          setEditingColumn(null);
                        }}
                      />
                      <button className={styles.srOnly} type="submit">
                        Save column name
                      </button>
                    </form>
                  ) : (
                    <h2
                      title="Click to rename"
                      onClick={() => {
                        setEditingColumn(column.id);
                        setColumnDraft(column.name);
                      }}
                    >
                      {column.name}
                    </h2>
                  )}
                  <span className={styles.cardCount}>{column.cards.length}</span>
                </div>
                <button
                  className={styles.iconButton}
                  type="button"
                  aria-label={`Rename ${column.name}`}
                  onClick={() => {
                    setEditingColumn(column.id);
                    setColumnDraft(column.name);
                  }}
                >
                  <Icon name="edit" size={15} />
                </button>
              </header>

              <div className={styles.cardList}>
                {column.cards.map((card) => (
                  <article
                    className={styles.card}
                    key={card.id}
                    draggable
                    onDrop={(event) => handleDrop(event, column.id, card.id)}
                    onDragStart={(event) => {
                      event.dataTransfer.setData("text/plain", card.id);
                      event.dataTransfer.setData("application/x-kanban-column", column.id);
                      event.dataTransfer.effectAllowed = "move";
                    }}
                  >
                    <div className={styles.cardTopline}>
                      <span className={styles.dragHandle} aria-label="Drag to move card">
                        <Icon name="grip" size={16} />
                      </span>
                      <button
                        className={styles.deleteButton}
                        type="button"
                        aria-label={`Delete ${card.title}`}
                        onClick={() =>
                          setBoard((current) => deleteCard(current, column.id, card.id))
                        }
                      >
                        <Icon name="trash" size={15} />
                        <span>Delete</span>
                      </button>
                    </div>
                    <h3>{card.title}</h3>
                    <p>{card.details}</p>
                  </article>
                ))}
              </div>

              {newCardColumn === column.id ? (
                <form
                  className={styles.newCardForm}
                  onSubmit={(event) => submitNewCard(event, column.id)}
                >
                  <label>
                    <span>Title</span>
                    <input
                      autoFocus
                      maxLength={80}
                      placeholder="What needs to get done?"
                      value={newTitle}
                      onChange={(event) => setNewTitle(event.target.value)}
                    />
                  </label>
                  <label>
                    <span>Details</span>
                    <textarea
                      maxLength={240}
                      placeholder="Add a little context"
                      rows={3}
                      value={newDetails}
                      onChange={(event) => setNewDetails(event.target.value)}
                    />
                  </label>
                  <div className={styles.formActions}>
                    <button
                      className={styles.cancelButton}
                      type="button"
                      onClick={() => {
                        setNewCardColumn(null);
                        setNewTitle("");
                        setNewDetails("");
                      }}
                    >
                      Cancel
                    </button>
                    <button className={styles.saveButton} type="submit" disabled={!newTitle.trim()}>
                      Add task
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  className={styles.addButton}
                  type="button"
                  onClick={() => setNewCardColumn(column.id)}
                >
                  <Icon name="plus" size={16} />
                  Add a task
                </button>
              )}
            </section>
          ))}
        </section>

        <footer className={styles.boardFooter}>
          <span>
            <Icon name="grip" size={15} />
            Drag a task to move it between columns
          </span>
          <span>Changes are not saved after you leave this page</span>
        </footer>
      </div>
    </main>
  );
}
