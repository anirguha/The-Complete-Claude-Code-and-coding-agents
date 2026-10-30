"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { DocumentInfo } from "@/documents/types";
import { type OpenedDocument, openDocument } from "@/saved/api";
import { DocumentBuilder } from "./DocumentBuilder";

type Loaded = { id: number } & ({ opened: OpenedDocument } | { error: string });

/** The document builder: a new document, or the saved one named by ?open=<id>. */
export function Workspace({ documents }: { documents: DocumentInfo[] }) {
  const openId = Number(useSearchParams().get("open")) || null;
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (openId === null) return;
    let active = true;
    openDocument(openId)
      .then((opened) => active && setLoaded({ id: openId, opened }))
      .catch((error: Error) => active && setLoaded({ id: openId, error: error.message }));
    return () => {
      active = false;
    };
  }, [openId]);

  if (openId === null) return <DocumentBuilder key="new" documents={documents} />;

  const current = loaded?.id === openId ? loaded : null;
  if (current === null) {
    return (
      <p role="status" className="py-12 text-center text-sm text-[#888888]">
        Opening your document…
      </p>
    );
  }
  if ("error" in current) {
    return (
      <div role="alert" className="space-y-3 py-12 text-center text-sm">
        <p className="text-red-700">{current.error}</p>
        <p>
          <Link href="/documents" className="font-medium text-[#209dd7] underline">
            Back to your documents
          </Link>
        </p>
      </div>
    );
  }
  return <DocumentBuilder key={openId} documents={documents} opened={current.opened} />;
}
