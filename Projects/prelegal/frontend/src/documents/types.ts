/** A run of inline text parsed from a template, with optional formatting. */
export type Run = {
  text: string;
  bold?: boolean;
  /** A defined term that refers back to a Cover Page field, e.g. "Governing Law". */
  term?: boolean;
  href?: string;
};

/** A numbered clause or sub-clause ("1.", "a.", "iv."), or an unnumbered paragraph. */
export type Block = {
  /** Nesting level: 0 for top-level clauses. */
  depth: number;
  /** The clause marker without its dot, or undefined for a paragraph. */
  marker?: string;
  runs: Run[];
};

/** A Common Paper standard terms template, parsed. */
export type Template = {
  title: string;
  blocks: Block[];
};

/** A document's key term, as defined in documents.json at the project root. */
export type DocumentField = {
  /** A camelCase identifier, used as the key in Draft.fields. */
  key: string;
  label: string;
  /** Guidance for the AI on what to ask for. */
  description: string;
  type?: "text" | "longtext" | "date";
  /** Offered as the usual choice, and shown in the document if the user skips the field. */
  default?: string;
};

/** A document Prelegal can draft, with its parsed standard terms. */
export type DocumentInfo = {
  id: string;
  name: string;
  description: string;
  /** The two parties' roles, e.g. ["Provider", "Customer"]. */
  parties: [string, string];
  fields: DocumentField[];
  template: Template;
};

export type Party = {
  name: string;
  title: string;
  company: string;
  noticeAddress: string;
};

/** The document being drafted. Mirrors Draft in backend/app/documents.py. */
export type Draft = {
  /** Null until the user and the AI settle on a document. */
  documentId: string | null;
  /** Field values by DocumentField.key; dates are ISO (yyyy-mm-dd). */
  fields: Record<string, string>;
  party1: Party;
  party2: Party;
  /** Items the user chose to skip: field keys, or party details such as "party1.title". */
  skipped: string[];
};

/** A filled-in value, or a placeholder shown when the value is still blank. */
export type FieldValue = { text: string } | { placeholder: string };

export type CoverPageField = {
  heading: string;
  value: FieldValue;
};

export type SignatureRow = {
  label: string;
  hint?: string;
  values: [FieldValue | null, FieldValue | null];
};

export type CoverPage = {
  fields: CoverPageField[];
  signatureRows: SignatureRow[];
};

export type SummaryRow = {
  label: string;
  /** One value for a key term; one per party for a party detail. */
  values: string[];
};

/** The Cover Page as plain text, stored on the saved document's Confluence page. */
export type Summary = {
  disclaimer: string;
  terms: SummaryRow[];
  partyRoles: [string, string];
  parties: SummaryRow[];
};
