"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { type SavedDocument, listDocuments } from "@/saved/api";

/** SQLite's CURRENT_TIMESTAMP ("2026-10-29 10:00:00", in UTC) in the viewer's local time. */
function formatUpdated(updatedAt: string): string {
  return new Date(`${updatedAt.replace(" ", "T")}Z`).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** The signed-in user's saved documents, newest first. */
export function SavedDocuments({ documentNames }: { documentNames: Record<string, string> }) {
  const [saved, setSaved] = useState<SavedDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listDocuments()
      .then((documents) => active && setSaved(documents))
      .catch((err: Error) => active && setError(err.message));
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-700">
        {error}
      </p>
    );
  }
  if (saved === null) {
    return (
      <p role="status" className="text-sm text-[#888888]">
        Loading your documents…
      </p>
    );
  }
  if (saved.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-stone-300 bg-white p-10 text-center">
        <p className="font-medium text-[#032147]">No saved documents yet</p>
        <p className="mt-1 text-sm text-[#888888]">Documents are saved here when you download their PDF.</p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-md bg-[#753991] px-4 py-2 text-sm font-semibold text-white hover:bg-[#753991]/90"
        >
          Draft a document
        </Link>
      </div>
    );
  }
  return (
    <ul className="divide-y divide-stone-200 rounded-lg border border-stone-200 bg-white shadow-sm">
      {saved.map((document) => (
        <li key={document.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="min-w-0 space-y-1">
            <p className="font-semibold text-[#032147]">{document.title}</p>
            <p className="text-sm text-[#888888]">
              {documentNames[document.documentId] ?? document.documentId} · Updated {formatUpdated(document.updatedAt)}
            </p>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <a
              href={document.pageUrl}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-[#209dd7] hover:text-[#032147]"
            >
              View in Confluence
            </a>
            <Link
              href={`/?open=${document.id}`}
              className="rounded-md bg-[#753991] px-4 py-2 font-semibold text-white hover:bg-[#753991]/90"
            >
              Open
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
