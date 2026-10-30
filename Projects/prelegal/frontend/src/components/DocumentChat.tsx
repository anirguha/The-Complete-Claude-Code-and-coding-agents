"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { type ChatMessage, sendChat } from "@/chat/api";
import { DISCLAIMER } from "@/documents/coverPage";
import type { Draft } from "@/documents/types";

/** Shown without calling the AI, so opening the page costs nothing. */
const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hi! I'll help you draft a legal agreement, such as an NDA, a cloud service agreement or a data processing agreement. What do you need, and who are the parties?",
};

type Props = {
  draft: Draft;
  onDraftChange: (draft: Draft) => void;
  /** Replaces the usual greeting, e.g. when reopening a saved document. */
  greeting?: string;
};

export function DocumentChat({ draft, onDraftChange, greeting }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    greeting ? { role: "assistant", content: greeting } : GREETING,
  ]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending]);

  async function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || pending) return;

    const sent = [...messages, { role: "user" as const, content: text }];
    setMessages(sent);
    setInput("");
    setPending(true);
    setError(null);
    try {
      const { reply, draft: updated } = await sendChat(sent, draft);
      setMessages([...sent, { role: "assistant", content: reply }]);
      onDraftChange(updated);
    } catch (err) {
      // Take the message back so the user can resend it without retyping.
      setMessages(messages);
      setInput(text);
      setError((err as Error).message);
    } finally {
      setPending(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="flex h-[32rem] flex-col rounded-lg border border-stone-200 bg-white shadow-sm lg:h-[calc(100vh-14rem)]">
      <ol aria-label="Conversation" aria-live="polite" className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message, i) => (
          <li key={i} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <p
              className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                message.role === "user" ? "bg-[#209dd7] text-white" : "bg-stone-100 text-stone-900"
              }`}
            >
              {message.content}
            </p>
          </li>
        ))}
        {pending && (
          <li className="flex justify-start">
            <p role="status" className="rounded-lg bg-stone-100 px-3 py-2 text-sm text-[#888888]">
              Thinking…
            </p>
          </li>
        )}
        <li ref={endRef} aria-hidden />
      </ol>

      <form onSubmit={handleSubmit} className="space-y-2 border-t border-stone-200 p-3">
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            aria-label="Message"
            rows={2}
            placeholder="Type your answer…"
            className="flex-1 resize-none rounded-md border border-stone-300 px-3 py-2 text-sm text-stone-900 shadow-sm focus:border-[#209dd7] focus:outline-none focus:ring-2 focus:ring-[#209dd7]/30"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            type="submit"
            disabled={pending || !input.trim()}
            className="rounded-md bg-[#753991] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#753991]/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-[#888888]">{DISCLAIMER}</p>
      </form>
    </div>
  );
}
