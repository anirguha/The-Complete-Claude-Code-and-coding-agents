import { DISCLAIMER, buildCoverPage, coverPageText } from "@/documents/coverPage";
import type { Block, DocumentInfo, Draft, FieldValue, Run } from "@/documents/types";

function Runs({ runs }: { runs: Run[] }) {
  return runs.map((run, i) => {
    if (run.bold) return <strong key={i}>{run.text}</strong>;
    if (run.term)
      return (
        <span key={i} className="font-medium text-[#209dd7] underline decoration-dotted">
          {run.text}
        </span>
      );
    if (run.href)
      return (
        <a key={i} href={run.href} className="break-all text-[#209dd7] underline" target="_blank" rel="noreferrer">
          {run.text}
        </a>
      );
    return <span key={i}>{run.text}</span>;
  });
}

function Value({ value }: { value: FieldValue | null }) {
  if (value === null) return null;
  if ("text" in value) return <span className="whitespace-pre-line">{value.text}</span>;
  return (
    <span className="rounded bg-amber-100 px-1 text-amber-800">[{value.placeholder}]</span>
  );
}

const INDENT = ["", "ml-6", "ml-12", "ml-16"];

function Clause({ block }: { block: Block }) {
  return (
    <p className={`${INDENT[Math.min(block.depth, INDENT.length - 1)]} ${block.depth === 0 ? "mt-4" : ""}`}>
      {block.marker && <span className="mr-1">{block.marker}.</span>}
      <Runs runs={block.runs} />
    </p>
  );
}

type Props = {
  doc: DocumentInfo;
  draft: Draft;
};

/** The completed document as it will appear in the downloaded PDF. */
export function DocumentPreview({ doc, draft }: Props) {
  const coverPage = buildCoverPage(doc, draft);
  const text = coverPageText(doc);

  return (
    <article className="space-y-6 font-serif text-[15px] leading-relaxed text-stone-900">
      <header className="space-y-3">
        <h1 className="text-center text-2xl font-bold text-[#032147]">{doc.name}</h1>
        <p className="text-center text-sm uppercase tracking-wide text-[#888888]">Cover Page</p>
        <p className="rounded-md border border-[#ecad0a]/50 bg-[#ecad0a]/10 px-4 py-3 font-sans text-sm text-[#032147]">
          {DISCLAIMER}
        </p>
        <p>{text.intro}</p>
      </header>

      <dl className="space-y-4">
        {coverPage.fields.map((field) => (
          <div key={field.heading}>
            <dt className="font-bold">{field.heading}</dt>
            <dd>
              <Value value={field.value} />
            </dd>
          </div>
        ))}
      </dl>

      <p>{text.signingStatement}</p>

      <table className="w-full table-fixed border-collapse text-sm">
        <thead>
          <tr>
            <th className="w-1/4 border border-stone-300 p-2" />
            {doc.parties.map((role) => (
              <th key={role} className="border border-stone-300 p-2 uppercase">
                {role}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {coverPage.signatureRows.map((row) => (
            <tr key={row.label}>
              <th scope="row" className="border border-stone-300 p-2 text-left align-top font-semibold">
                {row.label}
                {row.hint && <div className="text-xs font-normal text-stone-500">{row.hint}</div>}
              </th>
              {row.values.map((value, i) => (
                <td key={i} className="h-10 border border-stone-300 p-2 align-top break-words">
                  <Value value={value} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <p className="text-xs text-stone-500">{text.attribution}</p>

      <section className="space-y-1 border-t border-stone-300 pt-6">
        <h2 className="text-center text-xl font-bold text-[#032147]">{doc.template.title}</h2>
        {doc.template.blocks.map((block, i) => (
          <Clause key={i} block={block} />
        ))}
      </section>
    </article>
  );
}
