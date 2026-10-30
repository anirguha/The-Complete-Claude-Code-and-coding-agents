import { Document, Link, Page, StyleSheet, Text, View } from "@react-pdf/renderer";
import { DISCLAIMER, buildCoverPage, coverPageText } from "@/documents/coverPage";
import type { DocumentInfo, Draft, FieldValue, Run } from "@/documents/types";

const styles = StyleSheet.create({
  page: {
    paddingVertical: 56,
    paddingHorizontal: 64,
    fontFamily: "Times-Roman",
    fontSize: 10.5,
    lineHeight: 1.45,
  },
  title: { fontFamily: "Times-Bold", fontSize: 18, textAlign: "center", marginBottom: 4 },
  subtitle: { fontSize: 9, textAlign: "center", color: "#57534e", marginBottom: 12 },
  paragraph: { marginBottom: 10, textAlign: "justify" },
  clause: { marginBottom: 5, textAlign: "justify" },
  fieldHeading: { fontFamily: "Times-Bold", fontSize: 11.5 },
  field: { marginBottom: 8 },
  bold: { fontFamily: "Times-Bold" },
  term: { fontFamily: "Times-Bold" },
  link: { color: "#3730a3" },
  placeholder: { color: "#b45309" },
  table: { marginTop: 4, marginBottom: 12, borderTop: "1pt solid #a8a29e", borderLeft: "1pt solid #a8a29e" },
  row: { flexDirection: "row" },
  cell: { flexGrow: 1, flexBasis: 0, padding: 5, minHeight: 26, borderRight: "1pt solid #a8a29e", borderBottom: "1pt solid #a8a29e" },
  labelCell: { flexGrow: 0, flexShrink: 0, flexBasis: "26%", fontFamily: "Times-Bold" },
  headerCell: { fontFamily: "Times-Bold", textAlign: "center", textTransform: "uppercase" },
  hint: { fontFamily: "Times-Italic", fontSize: 8, color: "#57534e" },
  footnote: { fontSize: 8, color: "#57534e" },
  disclaimer: { fontFamily: "Times-Italic", fontSize: 9.5, marginBottom: 12, padding: 8, border: "1pt solid #ecad0a" },
});

/** Left indent, in points, per clause nesting level. */
const INDENT = 18;

function Runs({ runs }: { runs: Run[] }) {
  return runs.map((run, i) => {
    if (run.bold) return <Text key={i} style={styles.bold}>{run.text}</Text>;
    if (run.term) return <Text key={i} style={styles.term}>{run.text}</Text>;
    if (run.href)
      return (
        <Link key={i} src={run.href} style={styles.link}>
          {run.text}
        </Link>
      );
    return <Text key={i}>{run.text}</Text>;
  });
}

function Value({ value }: { value: FieldValue | null }) {
  if (value === null) return null;
  if ("text" in value) return <Text>{value.text}</Text>;
  return <Text style={styles.placeholder}>[{value.placeholder}]</Text>;
}

type Props = {
  doc: DocumentInfo;
  draft: Draft;
};

/** The completed document as a PDF: the Cover Page followed by the Standard Terms. */
export function DocumentPdf({ doc, draft }: Props) {
  const coverPage = buildCoverPage(doc, draft);
  const text = coverPageText(doc);

  return (
    <Document title={doc.name} subject={doc.name}>
      <Page size="LETTER" style={styles.page}>
        <Text style={styles.title}>{doc.name}</Text>
        <Text style={styles.subtitle}>COVER PAGE</Text>
        <Text style={styles.disclaimer}>{DISCLAIMER}</Text>
        <Text style={styles.paragraph}>{text.intro}</Text>

        {coverPage.fields.map((field) => (
          <View key={field.heading} style={styles.field} wrap={false}>
            <Text style={styles.fieldHeading}>{field.heading}</Text>
            <Value value={field.value} />
          </View>
        ))}

        <Text style={styles.paragraph}>{text.signingStatement}</Text>

        <View style={styles.table}>
          <View style={styles.row} wrap={false}>
            <View style={[styles.cell, styles.labelCell]} />
            {doc.parties.map((role) => (
              <Text key={role} style={[styles.cell, styles.headerCell]}>
                {role}
              </Text>
            ))}
          </View>
          {coverPage.signatureRows.map((row) => (
            <View key={row.label} style={styles.row} wrap={false}>
              <View style={[styles.cell, styles.labelCell]}>
                <Text>{row.label}</Text>
                {row.hint && <Text style={styles.hint}>{row.hint}</Text>}
              </View>
              {row.values.map((value, i) => (
                <View key={i} style={styles.cell}>
                  <Value value={value} />
                </View>
              ))}
            </View>
          ))}
        </View>

        <Text style={styles.footnote}>{text.attribution}</Text>
      </Page>

      <Page size="LETTER" style={styles.page}>
        <Text style={[styles.title, { marginBottom: 12 }]}>{doc.template.title}</Text>
        {doc.template.blocks.map((block, i) => (
          <Text
            key={i}
            style={[styles.clause, { marginLeft: block.depth * INDENT, marginTop: block.depth === 0 ? 6 : 0 }]}
          >
            {block.marker && `${block.marker}. `}
            <Runs runs={block.runs} />
          </Text>
        ))}
      </Page>
    </Document>
  );
}
