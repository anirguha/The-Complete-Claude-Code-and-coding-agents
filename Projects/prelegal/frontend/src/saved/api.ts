/** Client for the signed-in user's saved documents, which the backend stores in Confluence. */

import type { Draft, Summary } from "@/documents/types";
import { SESSION_ENDED, request } from "@/lib/http";

export type SavedDocument = {
  id: number;
  /** The kind of document, e.g. "mutual-nda". */
  documentId: string;
  title: string;
  /** The document's page in Confluence. */
  pageUrl: string;
  updatedAt: string;
};

export type OpenedDocument = {
  saved: SavedDocument;
  draft: Draft;
};

const MESSAGES = {
  401: SESSION_ENDED,
  404: "That document could not be found.",
  502: "Could not reach Confluence. Please try again.",
  503: "Saving documents is not set up on this server.",
};

export function listDocuments(): Promise<SavedDocument[]> {
  return request("/api/documents", undefined, MESSAGES, "Could not load your documents. Please try again.");
}

/** Saves a new document, or updates the saved one with this id, attaching its PDF under the given name. */
export function saveDocument(
  draft: Draft,
  summary: Summary,
  pdf: Blob,
  pdfName: string,
  savedId: number | null,
): Promise<SavedDocument> {
  const form = new FormData();
  form.append("draft", JSON.stringify(draft));
  form.append("summary", JSON.stringify(summary));
  form.append("pdf", pdf, pdfName);
  return request(
    savedId === null ? "/api/documents" : `/api/documents/${savedId}`,
    { method: savedId === null ? "POST" : "PUT", body: form },
    MESSAGES,
    "Could not save the document. Please try again.",
  );
}

export function openDocument(id: number): Promise<OpenedDocument> {
  return request(`/api/documents/${id}`, undefined, MESSAGES, "Could not open the document. Please try again.");
}
