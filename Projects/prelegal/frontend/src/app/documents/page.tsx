import type { Metadata } from "next";
import { AuthGate } from "@/auth/AuthGate";
import { SavedDocuments } from "@/components/SavedDocuments";
import { loadDocuments } from "@/documents/loadDocuments";

export const metadata: Metadata = {
  title: "My documents | prelegal",
};

export default function DocumentsPage() {
  const documentNames = Object.fromEntries(loadDocuments().map((doc) => [doc.id, doc.name]));

  return (
    <AuthGate>
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 space-y-1">
          <h1 className="text-2xl font-bold text-[#032147]">My documents</h1>
          <p className="text-sm text-stone-600">
            Documents you have downloaded, saved in Confluence. Open one to keep editing it.
          </p>
        </header>
        <SavedDocuments documentNames={documentNames} />
      </main>
    </AuthGate>
  );
}
