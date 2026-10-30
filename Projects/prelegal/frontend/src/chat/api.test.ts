import { afterEach, describe, expect, it, vi } from "vitest";
import { emptyDraft } from "@/documents/coverPage";
import { type ChatMessage, sendChat } from "./api";

const messages: ChatMessage[] = [
  { role: "assistant", content: "Who are the parties?" },
  { role: "user", content: "Acme and Globex." },
];

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("sendChat", () => {
  it("posts the conversation and draft, and returns the reply and updated draft", async () => {
    const result = {
      reply: "Who signs for Acme?",
      draft: { ...emptyDraft, documentId: "mutual-nda", party1: { ...emptyDraft.party1, company: "Acme" } },
    };
    const fetchMock = mockFetch(200, result);

    await expect(sendChat(messages, emptyDraft)).resolves.toEqual(result);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/chat");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ messages, draft: emptyDraft });
  });

  it("asks the user to sign in again when the session has ended", async () => {
    mockFetch(401, { detail: "Not signed in" });
    await expect(sendChat(messages, emptyDraft)).rejects.toThrow("Please sign in again.");
  });

  it("reports other failures", async () => {
    mockFetch(502, { detail: "The AI assistant could not respond. Please try again." });
    await expect(sendChat(messages, emptyDraft)).rejects.toThrow("could not respond");
  });
});
