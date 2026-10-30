import { AuthGate } from "@/auth/AuthGate";
import { Suspense } from "react";
import { Workspace } from "@/components/Workspace";
import { loadDocuments } from "@/documents/loadDocuments";

export default function Home() {
  const documents = loadDocuments();

  return (
    <AuthGate>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 space-y-1">
          <h1 className="text-2xl font-bold text-[#032147]">Legal Document Creator</h1>
          <p className="text-sm text-stone-600">
            Chat with the AI assistant to draft an agreement from Common Paper&apos;s standard terms,
            then download it as a PDF.
          </p>
        </header>
        {/* The workspace reads ?open=<id>, which is only known in the browser. */}
        <Suspense>
          <Workspace documents={documents} />
        </Suspense>
      </main>
    </AuthGate>
  );
}
