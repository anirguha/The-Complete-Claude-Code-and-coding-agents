"use client";

import Link from "next/link";
import { useState } from "react";
import { buildSummary, emptyDraft, pdfFileName } from "@/documents/coverPage";
import type { DocumentInfo, Draft } from "@/documents/types";
import { type OpenedDocument, type SavedDocument, saveDocument } from "@/saved/api";
import { DocumentChat } from "./DocumentChat";
import { DocumentPreview } from "./DocumentPreview";

/**
 * Renders the document to a PDF and downloads it, returning the PDF for saving.
 * The PDF renderer is loaded on demand to keep the page light.
 */
async function downloadPdf(doc: DocumentInfo, draft: Draft): Promise<Blob> {
  const [{ pdf }, { DocumentPdf }] = await Promise.all([
    import("@react-pdf/renderer"),
    import("./DocumentPdf"),
  ]);
  const blob = await pdf(<DocumentPdf doc={doc} draft={draft} />).toBlob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = pdfFileName(doc, draft);
  link.click();
  // Some browsers start the download asynchronously, so release the blob afterwards.
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return blob;
}

type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "saved"; saved: SavedDocument }
  | { status: "error"; message: string };

function SaveStatus({ state }: { state: SaveState }) {
  if (state.status === "saving") return <p role="status" className="text-sm text-[#888888]">Saving to your documents…</p>;
  if (state.status === "saved")
    return (
      <p role="status" className="text-sm text-emerald-700">
        Saved to{" "}
        <Link href="/documents" className="font-medium underline">
          your documents
        </Link>
      </p>
    );
  if (state.status === "error")
    return (
      <p role="alert" className="text-sm text-red-700">
        Downloaded, but not saved: {state.message}
      </p>
    );
  return null;
}

/** Shown in place of the preview until the AI has chosen a document. */
function SupportedDocuments({ documents }: { documents: DocumentInfo[] }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-700">
        Tell the assistant what you need and it will pick the right agreement. Prelegal can draft:
      </p>
      <ul className="space-y-3">
        {documents.map((doc) => (
          <li key={doc.id}>
            <p className="font-semibold text-[#032147]">{doc.name}</p>
            <p className="text-sm text-[#888888]">{doc.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Props = {
  documents: DocumentInfo[];
  /** A saved document to continue working on, instead of starting a new one. */
  opened?: OpenedDocument;
};

export function DocumentBuilder({ documents, opened }: Props) {
  const [draft, setDraft] = useState<Draft>(opened?.draft ?? emptyDraft);
  const [status, setStatus] = useState<"idle" | "generating" | "error">("idle");
  // Downloading saves the document; later downloads update the same saved document.
  const [savedId, setSavedId] = useState<number | null>(opened?.saved.id ?? null);
  const [save, setSave] = useState<SaveState>({ status: "idle" });
  const doc = documents.find((d) => d.id === draft.documentId);

  async function handleDownload() {
    if (!doc) return;
    setStatus("generating");
    setSave({ status: "idle" });
    let pdf: Blob;
    try {
      pdf = await downloadPdf(doc, draft);
      setStatus("idle");
    } catch (error) {
      console.error("Failed to generate PDF", error);
      setStatus("error");
      return;
    }
    setSave({ status: "saving" });
    try {
      const saved = await saveDocument(draft, buildSummary(doc, draft), pdf, pdfFileName(doc, draft), savedId);
      setSavedId(saved.id);
      setSave({ status: "saved", saved });
    } catch (error) {
      setSave({ status: "error", message: (error as Error).message });
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      <section aria-labelledby="chat-heading" className="space-y-4">
        <h2 id="chat-heading" className="text-lg font-semibold text-stone-900">
          Chat with the assistant
        </h2>
        <DocumentChat
          draft={draft}
          onDraftChange={setDraft}
          greeting={
            opened && doc
              ? `Welcome back! This is your ${doc.name}. What would you like to change? When you're done, download the PDF again to update your saved copy.`
              : undefined
          }
        />
      </section>

      <section aria-labelledby="preview-heading" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="preview-heading" className="text-lg font-semibold text-stone-900">
              Preview
            </h2>
            {doc && (
              <span className="rounded-full bg-[#ecad0a]/20 px-3 py-1 text-xs font-semibold text-[#032147]">
                {doc.name}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <SaveStatus state={save} />
            {status === "error" && (
              <p role="alert" className="text-sm text-red-700">
                Could not generate the PDF. Please try again.
              </p>
            )}
            <button
              type="button"
              onClick={handleDownload}
              // Also disabled while saving: a second click would save a second copy of a new document.
              disabled={!doc || status === "generating" || save.status === "saving"}
              className="rounded-md bg-[#753991] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#753991]/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {status === "generating" ? "Generating…" : "Download PDF"}
            </button>
          </div>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-6 shadow-sm sm:p-10 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto">
          {doc ? (
            <DocumentPreview doc={doc} draft={draft} />
          ) : (
            <SupportedDocuments documents={documents} />
          )}
        </div>
      </section>
    </div>
  );
}
