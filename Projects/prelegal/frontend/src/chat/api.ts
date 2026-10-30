/** Client for the backend's AI chat, which picks a document and drafts it from the conversation. */

import type { Draft } from "@/documents/types";
import { SESSION_ENDED, postJson, request } from "@/lib/http";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatResult = {
  reply: string;
  /** The whole draft, with the AI's changes from this turn applied (possibly a newly chosen document). */
  draft: Draft;
};

/** Sends the whole conversation and the current draft; the backend keeps no chat state. */
export function sendChat(messages: ChatMessage[], draft: Draft): Promise<ChatResult> {
  return request(
    "/api/chat",
    postJson({ messages, draft }),
    { 401: SESSION_ENDED },
    "The AI assistant could not respond. Please try again.",
  );
}
