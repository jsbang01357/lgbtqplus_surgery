import { PARSER_VERSION } from "../../core/constants";
import { BaseMetadata, MarkdownSection, ParsedChunk, StructuredMarkdownDocument } from "../../schemas/documents";

function createMetadata(chunk: ParsedChunk): BaseMetadata {
  const lower = chunk.text.toLowerCase();
  const modality =
    lower.includes("mri") ? "MRI" :
    lower.includes("ct") ? "CT" :
    lower.includes("pet") ? "PET" :
    lower.includes("x-ray") ? "X-ray" :
    lower.includes("ultrasound") || lower.includes("초음파") ? "Ultrasound" :
    "Imaging";

  return {
    patientId: chunk.patientId,
    type: "imaging",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || "imaging_report",
    modality,
    tags: ["imaging", modality.toLowerCase()],
    parserVersion: PARSER_VERSION,
    confidence: 0.84,
    reviewRequired: false,
  };
}

function extractSections(text: string): MarkdownSection[] {
  const findingsMatch = text.match(/findings[:\s]*([\s\S]*?)(?:impression[:\s]|$)/i);
  const impressionMatch = text.match(/impression[:\s]*([\s\S]*)$/i);
  const sections: MarkdownSection[] = [];

  if (findingsMatch?.[1]?.trim()) {
    sections.push({ heading: "Findings", body: findingsMatch[1].trim() });
  }
  if (impressionMatch?.[1]?.trim()) {
    sections.push({ heading: "Impression", body: impressionMatch[1].trim() });
  }
  if (sections.length === 0) {
    sections.push({ heading: "Report", body: text.trim() });
  }
  return sections;
}

export function parseImagingChunk(chunk: ParsedChunk): StructuredMarkdownDocument {
  const sections = extractSections(chunk.text);
  const metadata = createMetadata(chunk);
  metadata.reviewRequired = sections.length === 1 && sections[0].heading === "Report";

  return {
    kind: "imaging",
    metadata,
    sections,
    rawBody: chunk.text.trim(),
  };
}
