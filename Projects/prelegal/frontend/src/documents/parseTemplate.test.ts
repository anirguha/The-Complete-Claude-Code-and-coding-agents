import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseInline, parseTemplate } from "./parseTemplate";
import type { Template } from "./types";

const projectRoot = path.join(__dirname, "..", "..", "..");
const read = (file: string) => fs.readFileSync(path.join(projectRoot, file), "utf-8");
const definitions: { id: string; template: string }[] = JSON.parse(read("documents.json")).documents;
const allText = (template: Template) => template.blocks.flatMap((b) => b.runs.map((r) => r.text)).join("");

describe("parseInline", () => {
  it("splits bold, defined terms and links into runs", () => {
    expect(
      parseInline('A **bold** <span class="keyterms_link">Governing Law</span> [site](https://x.test).'),
    ).toEqual([
      { text: "A " },
      { text: "bold", bold: true },
      { text: " " },
      { text: "Governing Law", term: true },
      { text: " " },
      { text: "site", href: "https://x.test" },
      { text: "." },
    ]);
  });

  it("makes clause headings bold, drops empty anchors and links autolinks", () => {
    expect(
      parseInline(
        '<span class="header_3" id="1.1">Access and Use. </span><span id="8.1"></span>See <https://commonpaper.com>.',
      ),
    ).toEqual([
      { text: "Access and Use.", bold: true },
      { text: "See " },
      { text: "https://commonpaper.com", href: "https://commonpaper.com" },
      { text: "." },
    ]);
  });

  it("parses terms inside bold passages and terms or anchors with ids", () => {
    expect(
      parseInline(
        '**Cap is the <span class="keyterms_link">General Cap Amount</span>.** <span id="13.1">**"Affiliate"**</span> <span class="coverpage_link" id="7.1">Provider</span>',
      ),
    ).toEqual([
      { text: "Cap is the ", bold: true },
      { text: "General Cap Amount", term: true, bold: true },
      { text: ".", bold: true },
      { text: " " },
      { text: '"Affiliate"', bold: true },
      { text: " " },
      { text: "Provider", term: true },
    ]);
  });

  it("returns plain text as a single run", () => {
    expect(parseInline("plain")).toEqual([{ text: "plain" }]);
  });
});

describe("parseTemplate", () => {
  it("reads nested numbered, lettered and roman clauses", () => {
    const template = parseTemplate(
      "# Title\n\n1. <span class=\"header_2\" id=\"1\">First</span>\n    1. Sub clause.\n        a. Item.\n            iv. Deep.\n\nClosing words.\n",
    );
    expect(template.title).toBe("Title");
    expect(template.blocks.map((b) => [b.depth, b.marker])).toEqual([
      [0, "1"],
      [1, "1"],
      [2, "a"],
      [3, "iv"],
      [0, undefined],
    ]);
    expect(template.blocks[0].runs).toEqual([{ text: "First", bold: true }]);
  });

  it("rejects a template without a title or clauses", () => {
    expect(() => parseTemplate("1. No title")).toThrow("no title");
    expect(() => parseTemplate("# Empty\n")).toThrow("no clauses");
  });
});

describe.each(definitions)("the $id template", ({ template: file }) => {
  const template = parseTemplate(read(file));

  it("parses into titled, numbered clauses", () => {
    expect(template.title).not.toBe("");
    expect(template.blocks[0]).toMatchObject({ depth: 0, marker: "1" });
    expect(template.blocks.filter((b) => b.marker).length).toBeGreaterThan(5);
  });

  it("marks defined terms and leaves no raw markup in the text", () => {
    expect(template.blocks.some((b) => b.runs.some((r) => r.term))).toBe(true);
    expect(allText(template)).not.toMatch(/\*\*|<span|<\/span>|\]\(|<https?:/);
  });
});
