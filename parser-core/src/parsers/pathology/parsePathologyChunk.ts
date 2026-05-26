import { PARSER_VERSION } from "../../core/constants";
import { BaseMetadata, MarkdownSection, ParsedChunk, StructuredMarkdownDocument } from "../../schemas/documents";

function createMetadata(chunk: ParsedChunk): BaseMetadata {
  return {
    patientId: chunk.patientId,
    type: "pathology",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || "pathology_report",
    tags: ["pathology"],
    parserVersion: PARSER_VERSION,
    confidence: 0.82,
    reviewRequired: false,
  };
}

function sectionFromRegex(text: string, label: string, regex: RegExp): MarkdownSection | null {
  const match = regex.exec(text);
  if (!match?.[1]?.trim()) return null;
  return { heading: label, body: match[1].trim() };
}

export function parsePathologyChunk(chunk: ParsedChunk): StructuredMarkdownDocument {
  const sections = [
    sectionFromRegex(chunk.text, "Specimen", /specimen[:\s]*([\s\S]*?)(?:diagnosis[:\s]|comment[:\s]|$)/i),
    sectionFromRegex(chunk.text, "Diagnosis", /diagnosis[:\s]*([\s\S]*?)(?:comment[:\s]|gross[:\s]|$)/i),
    sectionFromRegex(chunk.text, "Comment", /comment[:\s]*([\s\S]*)$/i),
  ].filter((section): section is MarkdownSection => section !== null);

  if (sections.length === 0) {
    sections.push({ heading: "Report", body: chunk.text.trim() });
  }

  const metadata = createMetadata(chunk);
  metadata.reviewRequired = sections.length === 1 && sections[0].heading === "Report";

  return {
    kind: "pathology",
    metadata,
    sections,
    rawBody: chunk.text.trim(),
  };
}
