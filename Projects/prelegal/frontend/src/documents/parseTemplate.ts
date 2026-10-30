import type { Block, Run, Template } from "./types";

/** Anchor spans like <span id="8.1"></span>, which only mark clause numbers; their content is kept. */
const ANCHOR_PATTERN = /<span id="[^"]*">(.*?)<\/span>/g;

/**
 * The inline markup used by the templates: clause heading spans, defined-term spans
 * (coverpage_link, keyterms_link, orderform_link, ...), bold, links and autolinks.
 */
const INLINE_PATTERN =
  /<span class="header_\d"[^>]*>(.+?)<\/span>|<span class="\w+_link"[^>]*>(.+?)<\/span>|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|<(https?:\/\/[^>]+)>/g;

/** A numbered or lettered clause ("1.", "a.", "iv."), indented four spaces per level. */
const CLAUSE_PATTERN = /^( *)([0-9]+|[a-z]+)\.\s+(.*)$/;

/** Parses a template's inline markup into runs of text. */
export function parseInline(markup: string): Run[] {
  const source = markup.replace(ANCHOR_PATTERN, "$1");
  const runs: Run[] = [];
  let last = 0;
  for (const match of source.matchAll(INLINE_PATTERN)) {
    if (match.index > last) runs.push({ text: source.slice(last, match.index) });
    const [, heading, term, bold, linkText, href, autolink] = match;
    if (heading !== undefined) runs.push({ text: heading.trim(), bold: true });
    // Bold passages can contain defined terms, so their contents are parsed too.
    else if (bold !== undefined) runs.push(...parseInline(bold).map((run) => ({ ...run, bold: true })));
    else if (term !== undefined) runs.push({ text: term, term: true });
    else if (linkText !== undefined) runs.push({ text: linkText, href });
    else if (autolink !== undefined) runs.push({ text: autolink, href: autolink });
    last = match.index + match[0].length;
  }
  if (last < source.length) runs.push({ text: source.slice(last) });
  return runs;
}

/** Parses a standard terms template: a "# " title followed by nested numbered clauses and paragraphs. */
export function parseTemplate(markdown: string): Template {
  let title: string | undefined;
  const blocks: Block[] = [];
  for (const line of markdown.split("\n")) {
    if (!line.trim()) continue;
    if (title === undefined && line.startsWith("# ")) {
      title = line.slice(2).trim();
      continue;
    }
    const clause = line.match(CLAUSE_PATTERN);
    if (clause) {
      const [, indent, marker, text] = clause;
      blocks.push({ depth: Math.floor(indent.length / 4), marker, runs: parseInline(text.trim()) });
    } else {
      blocks.push({ depth: Math.floor((line.length - line.trimStart().length) / 4), runs: parseInline(line.trim()) });
    }
  }
  if (title === undefined) throw new Error("Template has no title");
  if (blocks.length === 0) throw new Error(`Template "${title}" has no clauses`);
  return { title, blocks };
}
