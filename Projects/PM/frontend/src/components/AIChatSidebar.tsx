"use client";

import { useState, type FormEvent } from "react";
import { api, type ChatTurn } from "@/lib/api";

type AIChatSidebarProps = {
  onBoardUpdated: () => void;
};

export const AIChatSidebar = ({ onBoardUpdated }: AIChatSidebarProps) => {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = message.trim();
    if (!question || busy) return;

    setError("");
    setMessage("");
    setBusy(true);
    const nextTurns = [...turns, { role: "user" as const, content: question }];
    setTurns(nextTurns);
    try {
      const result = await api.chat(question, turns.slice(-40));
      setTurns([...nextTurns, { role: "assistant", content: result.response }]);
      onBoardUpdated();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Chat failed."
      );
      setTurns(turns);
      setMessage(question);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex min-h-[420px] flex-col rounded-3xl border border-[var(--stroke)] bg-white/90 p-5 shadow-[var(--shadow)] xl:sticky xl:top-6 xl:h-[calc(100vh-3rem)]">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--primary-blue)]">
          Board assistant
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
          AI chat
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
          Ask questions or request changes to cards and columns. Press Enter to
          send, Shift+Enter for a new line.
        </p>
      </div>
      <div
        aria-live="polite"
        className="mt-5 flex-1 space-y-3 overflow-y-auto rounded-2xl bg-[var(--surface)] p-3"
      >
        {turns.length === 0 && (
          <p className="text-sm text-[var(--gray-text)]">
            Your conversation will appear here.
          </p>
        )}
        {turns.map((turn, index) => (
          <p
            key={`${turn.role}-${index}`}
            className={`whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-6 ${
              turn.role === "user"
                ? "ml-5 bg-[var(--navy-dark)] text-white"
                : "mr-5 bg-white text-[var(--navy-dark)]"
            }`}
          >
            {turn.content}
          </p>
        ))}
        {busy && (
          <p className="text-sm text-[var(--gray-text)]">Thinking...</p>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm font-medium text-red-700">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <label className="sr-only" htmlFor="assistant-message">
          Message the board assistant
        </label>
        <textarea
          id="assistant-message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Ask about your board..."
          rows={3}
          maxLength={4000}
          className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={busy || !message.trim()}
          className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send message
        </button>
      </form>
    </aside>
  );
};
