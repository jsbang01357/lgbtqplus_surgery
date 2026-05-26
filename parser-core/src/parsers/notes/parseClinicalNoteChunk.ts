import { PARSER_VERSION } from "../../core/constants";
import { BaseMetadata, MarkdownSection, NoteSubtype, ParsedChunk, StructuredMarkdownDocument } from "../../schemas/documents";

function detectSubtype(text: string): NoteSubtype {
  if (/discharge/i.test(text)) return "discharge_summary";
  if (/admission/i.test(text)) return "admission_note";
  if (/consult/i.test(text)) return "consult_note";
  if (/progress/i.test(text)) return "progress_note";
  return "clinical_note";
}

function createMetadata(chunk: ParsedChunk, subtype: NoteSubtype): BaseMetadata {
  return {
    patientId: chunk.patientId,
    type: "note",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || subtype,
    tags: ["note", subtype],
    parserVersion: PARSER_VERSION,
    confidence: 0.78,
    reviewRequired: false,
  };
}

function extractNoteSections(text: string): MarkdownSection[] {
  const labels = [
    "Subjective",
    "Objective",
    "Assessment",
    "Plan",
    "주호소",
    "현병력",
    "과거력",
    "계획",
  ];

  const lines = text.split(/\r?\n/);
  const sections: MarkdownSection[] = [];
  let currentHeading = "Note";
  let buffer: string[] = [];

  const flush = () => {
    const body = buffer.join("\n").trim();
    if (body) {
      sections.push({ heading: currentHeading, body });
    }
    buffer = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    const matchedLabel = labels.find((label) => new RegExp(`^${label}\\s*[:>]?\\s*$`, "i").test(trimmed));
    if (matchedLabel) {
      flush();
      currentHeading = matchedLabel;
      continue;
    }
    buffer.push(line);
  }
  flush();

  if (sections.length === 0) {
    sections.push({ heading: "Note", body: text.trim() });
  }
  return sections;
}

export function parseClinicalNoteChunk(chunk: ParsedChunk): StructuredMarkdownDocument {
  const subtype = detectSubtype(chunk.text);
  const sections = extractNoteSections(chunk.text);
  const metadata = createMetadata(chunk, subtype);
  metadata.reviewRequired = sections.length === 1 && sections[0].heading === "Note";

  return {
    kind: "note",
    metadata,
    sections,
    rawBody: chunk.text.trim(),
  };
}
