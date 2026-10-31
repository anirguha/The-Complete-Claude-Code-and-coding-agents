"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { describeTrade, describeWatchlistChange } from "@/lib/chatActions";
import type { ChatActions as Actions, ChatResponse } from "@/lib/types";

interface Message {
  key: string;
  role: "user" | "assistant";
  content: string;
  actions: Actions | null;
}

export function ChatActionList({ actions }: { actions: Actions | null }) {
  if (!actions) return null;
  const trades = actions.trades ?? [];
  const changes = actions.watchlist_changes ?? [];
  if (trades.length === 0 && changes.length === 0) return null;
  const rows = [
    ...trades.map((t) => ({ status: t.status, text: describeTrade(t), ok: t.status === "executed" })),
    ...changes.map((c) => ({ status: c.status, text: describeWatchlistChange(c), ok: c.status === "applied" })),
  ];
  return (
    <ul className="mt-1.5 space-y-1">
      {rows.map((row, i) => (
        <li
          key={i}
          data-testid="chat-action"
          data-status={row.status}
          className={`flex gap-1.5 border-l-2 bg-raised px-2 py-1 text-[12px] ${
            row.ok ? "border-l-up text-ink" : "border-l-down text-down"
          }`}
        >
          <span aria-hidden="true">{row.ok ? "✓" : "✕"}</span>
          <span className="num">{row.text}</span>
        </li>
      ))}
    </ul>
  );
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div data-testid="chat-message" data-role={message.role} className={isUser ? "pl-6" : "pr-2"}>
      <div className={`text-[11px] ${isUser ? "text-right text-faint" : "text-amber"}`}>
        {isUser ? "You" : "FinAlly"}
      </div>
      <p
        className={`whitespace-pre-wrap break-words ${
          isUser ? "rounded-sm bg-raised px-2 py-1.5" : "py-0.5"
        }`}
      >
        {message.content}
      </p>
      <ChatActionList actions={message.actions} />
    </div>
  );
}

const responseHasActions = (r: ChatResponse) =>
  (r.trades?.length ?? 0) > 0 || (r.watchlist_changes?.length ?? 0) > 0;

export function ChatPanel({
  open,
  onClose,
  onActions,
}: {
  open: boolean;
  onClose: () => void;
  onActions: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const counter = useRef(0);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .chatHistory()
      .then((history) => {
        if (cancelled) return;
        const loaded = history.map((m, i) => ({
          key: `history-${i}`,
          role: m.role,
          content: m.content,
          actions: m.actions,
        }));
        // Anything sent while history was loading stays after it.
        setMessages((current) => [...loaded, ...current]);
      })
      .catch((e) => console.warn("Couldn't load chat history", e));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const element = scroller.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, loading, open]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    setError(null);
    setMessages((m) => [...m, { key: `local-${counter.current++}`, role: "user", content: text, actions: null }]);
    setLoading(true);
    try {
      const response = await api.chat(text);
      setMessages((m) => [
        ...m,
        {
          key: `local-${counter.current++}`,
          role: "assistant",
          content: response.message,
          actions: { trades: response.trades ?? [], watchlist_changes: response.watchlist_changes ?? [] },
        },
      ]);
      if (responseHasActions(response)) onActions();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "FinAlly didn't reply. Send your message again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside
      aria-label="AI chat"
      hidden={!open}
      className="fixed bottom-0 right-0 top-[58px] z-30 w-full max-w-[380px] flex-col border-l border-edge bg-pane data-[open=true]:flex desk:static desk:z-auto desk:w-[340px] desk:max-w-none"
      data-open={open}
    >
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-edge bg-strip px-2.5">
        <h2 className="text-[12px] font-semibold">AI assistant</h2>
        <button
          type="button"
          aria-label="Close AI chat"
          onClick={onClose}
          className="flex h-5 w-5 cursor-pointer items-center justify-center rounded-sm text-[15px] leading-none text-dim hover:bg-edge hover:text-ink"
        >
          ×
        </button>
      </header>
      <div ref={scroller} className="pane-scroll flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-2.5">
        {messages.length === 0 && !loading ? (
          <div className="my-auto text-dim">
            <p className="mb-1.5 text-ink">Ask about your portfolio, or tell FinAlly what to do.</p>
            <p>“How concentrated am I?”</p>
            <p>“Buy 5 NVDA.”</p>
            <p>“Add PYPL to my watchlist.”</p>
          </div>
        ) : null}
        {messages.map((message) => (
          <ChatMessage key={message.key} message={message} />
        ))}
        {loading ? (
          <div data-testid="chat-loading" role="status" className="flex items-center gap-1.5 text-dim">
            <span className="flex gap-1" aria-hidden="true">
              <span className="thinking-dot" />
              <span className="thinking-dot" />
              <span className="thinking-dot" />
            </span>
            FinAlly is thinking
          </div>
        ) : null}
        {error ? (
          <p role="alert" data-testid="chat-error" className="text-down">
            {error}
          </p>
        ) : null}
      </div>
      <form onSubmit={send} className="flex shrink-0 gap-1.5 border-t border-edge p-2">
        <input
          data-testid="chat-input"
          aria-label="Message FinAlly"
          className="field"
          placeholder="Message FinAlly"
          value={draft}
          autoComplete="off"
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          data-testid="chat-send"
          className="btn-submit shrink-0"
          disabled={loading || !draft.trim()}
        >
          Send
        </button>
      </form>
    </aside>
  );
}
