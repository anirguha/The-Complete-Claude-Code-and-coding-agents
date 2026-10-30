import "server-only";
import fs from "node:fs";
import path from "node:path";
import { parseTemplate } from "./parseTemplate";
import type { DocumentInfo } from "./types";

/** documents.json and the shared Common Paper templates live one level above the frontend app. */
const PROJECT_ROOT = path.join(process.cwd(), "..");

type DocumentDefinition = Omit<DocumentInfo, "template"> & { template: string };

/** Reads every document Prelegal can draft, with its parsed standard terms. Runs at build time. */
export function loadDocuments(): DocumentInfo[] {
  const read = (file: string) => fs.readFileSync(path.join(PROJECT_ROOT, file), "utf-8");
  const { documents } = JSON.parse(read("documents.json")) as { documents: DocumentDefinition[] };
  return documents.map((doc) => ({ ...doc, template: parseTemplate(read(doc.template)) }));
}
