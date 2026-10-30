import type { CoverPage, DocumentInfo, Draft, FieldValue, Party, Summary } from "./types";

const emptyParty = (): Party => ({ name: "", title: "", company: "", noticeAddress: "" });

/** A draft before any document has been chosen. */
export const emptyDraft: Draft = {
  documentId: null,
  fields: {},
  party1: emptyParty(),
  party2: emptyParty(),
  skipped: [],
};

/** Shown in the app, on the PDF's Cover Page and (through buildSummary) on the saved Confluence page. */
export const DISCLAIMER =
  "This document is an AI-assisted draft. Its finalization is subject to review and approval by the parties and their legal advisers.";

/** Shown for a skipped item that has no default. */
export const NOT_APPLICABLE = "Not applicable.";

/** A filled-in value; when blank, the text for a skipped item if given, otherwise a placeholder. */
function value(text: string | undefined, placeholder: string, skippedText?: string): FieldValue {
  const trimmed = text?.trim();
  if (trimmed) return { text: trimmed };
  return skippedText ? { text: skippedText } : { placeholder };
}

/** Formats an ISO date (yyyy-mm-dd) as e.g. "October 28, 2026", independent of the viewer's time zone. */
export function formatDate(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** Builds the filled-in Cover Page shown in both the preview and the PDF. */
export function buildCoverPage(doc: DocumentInfo, draft: Draft): CoverPage {
  const [role1, role2] = doc.parties;
  // Item keys match the backend's: a field key, or a party detail such as "party1.title".
  const skippedText = (key: string, fallback = NOT_APPLICABLE) =>
    draft.skipped.includes(key) ? fallback : undefined;
  const party = (key: keyof Party, placeholder: string) =>
    [
      value(draft.party1[key], `${role1} ${placeholder}`, skippedText(`party1.${key}`)),
      value(draft.party2[key], `${role2} ${placeholder}`, skippedText(`party2.${key}`)),
    ] as [FieldValue, FieldValue];

  return {
    fields: doc.fields.map((field) => {
      const text = draft.fields[field.key] ?? "";
      return {
        heading: field.label,
        value: value(
          field.type === "date" ? formatDate(text) : text,
          field.label,
          skippedText(field.key, field.default || NOT_APPLICABLE),
        ),
      };
    }),
    signatureRows: [
      { label: "Signature", values: [null, null] },
      { label: "Print Name", values: party("name", "name") },
      { label: "Title", values: party("title", "title") },
      { label: "Company", values: party("company", "company") },
      {
        label: "Notice Address",
        hint: "Use either email or postal address",
        values: party("noticeAddress", "notice address"),
      },
      { label: "Date", values: [null, null] },
    ],
  };
}

/**
 * The Cover Page as plain text, as the backend stores it on the saved document's Confluence page
 * (Summary in backend/app/routers/documents.py), so the page shows exactly what the PDF does.
 */
export function buildSummary(doc: DocumentInfo, draft: Draft): Summary {
  const coverPage = buildCoverPage(doc, draft);
  const text = (value: FieldValue | null) => (value && "text" in value ? value.text : "Not provided");
  return {
    disclaimer: DISCLAIMER,
    terms: coverPage.fields.map((field) => ({ label: field.heading, values: [text(field.value)] })),
    partyRoles: doc.parties,
    // Signature and Date rows are left blank for signing, so they are not part of the summary.
    parties: coverPage.signatureRows
      .filter((row) => row.values.some((value) => value !== null))
      .map((row) => ({ label: row.label, values: row.values.map(text) })),
  };
}

/** The Cover Page's opening and closing prose, shared by the preview and the PDF. */
export function coverPageText(doc: DocumentInfo) {
  // Most documents start on an "Effective Date" (the BAA's is the "BAA Effective Date"); some have none.
  const effectiveDate = doc.fields.find((field) => field.type === "date" && field.label.endsWith("Effective Date"));
  const start = effectiveDate ? `the ${effectiveDate.label}` : "the date of the last signature below";
  return {
    intro: `This ${doc.name} consists of this Cover Page and the Common Paper Standard Terms that follow. Capitalized terms used in the Standard Terms have the meanings given on this Cover Page, which controls over any conflict with the Standard Terms.`,
    signingStatement: `By signing this Cover Page, each party agrees to enter into this ${doc.name} as of ${start}.`,
    attribution: `Based on the Common Paper ${doc.name} standard terms, free to use under CC BY 4.0.`,
  };
}

/** A file name such as "Cloud-Service-Agreement-Acme-Globex.pdf". */
export function pdfFileName(doc: DocumentInfo, draft: Draft): string {
  const slug = (s: string) =>
    s
      .trim()
      .replace(/[^A-Za-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  const parts = [slug(doc.name), slug(draft.party1.company), slug(draft.party2.company)].filter(Boolean);
  return `${parts.join("-")}.pdf`;
}
