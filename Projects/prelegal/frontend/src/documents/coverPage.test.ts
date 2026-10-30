import { describe, expect, it } from "vitest";
import {
  DISCLAIMER,
  NOT_APPLICABLE,
  buildCoverPage,
  buildSummary,
  coverPageText,
  emptyDraft,
  formatDate,
  pdfFileName,
} from "./coverPage";
import type { DocumentInfo, Draft } from "./types";

const csa: DocumentInfo = {
  id: "cloud-service-agreement",
  name: "Cloud Service Agreement",
  description: "SaaS terms.",
  parties: ["Provider", "Customer"],
  fields: [
    { key: "effectiveDate", label: "Effective Date", description: "Start.", type: "date" },
    { key: "governingLaw", label: "Governing Law", description: "Law." },
    { key: "dpa", label: "DPA", description: "DPA.", default: "None." },
  ],
  template: { title: "Cloud Service Agreement", blocks: [] },
};

const draft = (changes: Partial<Draft> = {}): Draft => ({
  ...emptyDraft,
  documentId: csa.id,
  fields: { effectiveDate: "", governingLaw: "", dpa: "None." },
  ...changes,
});

const field = (d: Draft, heading: string) => buildCoverPage(csa, d).fields.find((f) => f.heading === heading)?.value;

describe("buildCoverPage", () => {
  it("lists every field in order, with placeholders for blank values", () => {
    expect(buildCoverPage(csa, draft()).fields).toEqual([
      { heading: "Effective Date", value: { placeholder: "Effective Date" } },
      { heading: "Governing Law", value: { placeholder: "Governing Law" } },
      { heading: "DPA", value: { text: "None." } },
    ]);
  });

  it("fills in values, trimmed, and formats dates", () => {
    const d = draft({ fields: { effectiveDate: "2026-01-05", governingLaw: "  Delaware ", dpa: "" } });
    expect(field(d, "Governing Law")).toEqual({ text: "Delaware" });
    expect(field(d, "Effective Date")).toEqual({ text: "January 5, 2026" });
  });

  it("treats fields missing from the draft as blank", () => {
    expect(field(draft({ fields: {} }), "DPA")).toEqual({ placeholder: "DPA" });
  });

  it("shows a skipped field's default, or Not applicable when it has none", () => {
    const d = draft({ fields: { effectiveDate: "", governingLaw: "", dpa: "" }, skipped: ["dpa", "governingLaw"] });
    expect(field(d, "DPA")).toEqual({ text: "None." });
    expect(field(d, "Governing Law")).toEqual({ text: NOT_APPLICABLE });
    expect(field(d, "Effective Date")).toEqual({ placeholder: "Effective Date" });
  });

  it("prefers a value over a skip", () => {
    expect(field(draft({ fields: { governingLaw: "Delaware" }, skipped: ["governingLaw"] }), "Governing Law")).toEqual({
      text: "Delaware",
    });
  });

  it("shows skipped party details as Not applicable", () => {
    const title = buildCoverPage(csa, draft({ skipped: ["party2.title"] })).signatureRows.find((r) => r.label === "Title");
    expect(title?.values).toEqual([{ placeholder: "Provider title" }, { text: NOT_APPLICABLE }]);
  });

  it("labels each party's signature column with its role", () => {
    const d = draft({ party1: { ...emptyDraft.party1, company: "Acme" } });
    const company = buildCoverPage(csa, d).signatureRows.find((r) => r.label === "Company");
    expect(company?.values).toEqual([{ text: "Acme" }, { placeholder: "Customer company" }]);
  });
});

describe("buildSummary", () => {
  it("gives the cover page as text, with blanks as Not provided and no signature rows", () => {
    const d = draft({
      fields: { effectiveDate: "2026-01-05", governingLaw: "", dpa: "" },
      skipped: ["dpa"],
      party1: { ...emptyDraft.party1, company: "Acme" },
    });
    const summary = buildSummary(csa, d);
    expect(summary.disclaimer).toBe(DISCLAIMER);
    expect(summary.partyRoles).toEqual(["Provider", "Customer"]);
    expect(summary.terms).toEqual([
      { label: "Effective Date", values: ["January 5, 2026"] },
      { label: "Governing Law", values: ["Not provided"] },
      { label: "DPA", values: ["None."] },
    ]);
    expect(summary.parties.map((row) => row.label)).toEqual(["Print Name", "Title", "Company", "Notice Address"]);
    expect(summary.parties[2]).toEqual({ label: "Company", values: ["Acme", "Not provided"] });
  });
});

describe("coverPageText", () => {
  it("names the document and its effective date", () => {
    expect(coverPageText(csa).signingStatement).toBe(
      "By signing this Cover Page, each party agrees to enter into this Cloud Service Agreement as of the Effective Date.",
    );
  });

  it("uses a document's own effective date label", () => {
    const baa = { ...csa, name: "Business Associate Agreement", fields: [
      { key: "baaEffectiveDate", label: "BAA Effective Date", description: "Start.", type: "date" as const },
    ] };
    expect(coverPageText(baa).signingStatement).toMatch(/as of the BAA Effective Date\.$/);
  });

  it("falls back to the last signature for documents without an effective date", () => {
    const sla = { ...csa, name: "Service Level Agreement", fields: csa.fields.slice(1) };
    expect(coverPageText(sla).signingStatement).toMatch(/as of the date of the last signature below\.$/);
  });
});

describe("formatDate", () => {
  it("returns an empty string for invalid input", () => {
    expect(formatDate("")).toBe("");
    expect(formatDate("next Monday")).toBe("");
  });
});

describe("pdfFileName", () => {
  it("includes the document and both company names when present", () => {
    const d = draft({
      party1: { ...emptyDraft.party1, company: "Acme, Inc." },
      party2: { ...emptyDraft.party2, company: "Globex" },
    });
    expect(pdfFileName(csa, d)).toBe("Cloud-Service-Agreement-Acme-Inc-Globex.pdf");
  });

  it("falls back to the document name", () => {
    expect(pdfFileName(csa, draft())).toBe("Cloud-Service-Agreement.pdf");
  });
});
