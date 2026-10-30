import { afterEach, describe, expect, it, vi } from "vitest";
import { emptyDraft } from "@/documents/coverPage";
import type { Summary } from "@/documents/types";
import { listDocuments, openDocument, saveDocument } from "./api";

const saved = {
  id: 7,
  documentId: "mutual-nda",
  title: "Mutual Non-Disclosure Agreement: Acme and Globex (a1b2c3)",
  pageUrl: "https://acme.atlassian.net/wiki/spaces/SCRUM/pages/1000",
  updatedAt: "2026-10-29 10:00:00",
};
const draft = { ...emptyDraft, documentId: "mutual-nda" };
const pdf = new Blob(["%PDF-1.4"], { type: "application/pdf" });
const summary: Summary = { disclaimer: "Draft.", terms: [], partyRoles: ["Party 1", "Party 2"], parties: [] };

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

describe("listDocuments", () => {
  it("returns the user's saved documents", async () => {
    const fetchMock = mockFetch(200, [saved]);
    await expect(listDocuments()).resolves.toEqual([saved]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/documents");
  });

  it("asks the user to sign in again when the session has ended", async () => {
    mockFetch(401);
    await expect(listDocuments()).rejects.toThrow("Please sign in again.");
  });
});

describe("saveDocument", () => {
  it("posts a new document as a form with the draft, summary and named PDF", async () => {
    const fetchMock = mockFetch(201, saved);
    await expect(saveDocument(draft, summary, pdf, "NDA.pdf", null)).resolves.toEqual(saved);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/documents");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body.get("draft"))).toEqual(draft);
    expect(JSON.parse(init.body.get("summary"))).toEqual(summary);
    expect(init.body.get("pdf").name).toBe("NDA.pdf");
  });

  it("updates an already saved document", async () => {
    const fetchMock = mockFetch(200, saved);
    await saveDocument(draft, summary, pdf, "NDA.pdf", 7);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/documents/7");
    expect(init.method).toBe("PUT");
  });

  it("explains why saving failed", async () => {
    mockFetch(503);
    await expect(saveDocument(draft, summary, pdf, "NDA.pdf", null)).rejects.toThrow("not set up on this server");
    mockFetch(502);
    await expect(saveDocument(draft, summary, pdf, "NDA.pdf", null)).rejects.toThrow("Could not reach Confluence");
    mockFetch(500);
    await expect(saveDocument(draft, summary, pdf, "NDA.pdf", null)).rejects.toThrow("Could not save the document");
  });
});

describe("openDocument", () => {
  it("returns the saved document and its draft", async () => {
    const fetchMock = mockFetch(200, { saved, draft });
    await expect(openDocument(7)).resolves.toEqual({ saved, draft });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/documents/7");
  });

  it("reports a missing document", async () => {
    mockFetch(404);
    await expect(openDocument(99)).rejects.toThrow("could not be found");
  });
});
