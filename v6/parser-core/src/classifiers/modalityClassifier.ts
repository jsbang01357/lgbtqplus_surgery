import { IMAGING_KEYWORDS, LAB_KEYWORDS_SAFE, LAB_KEYWORDS_STRICT, LAB_SECTION_HINTS, MEDICATION_KEYWORDS, NOTE_TITLE_PATTERNS, PATHOLOGY_KEYWORDS } from "../core/constants";
import { ChunkClassification, ParsedChunk } from "../schemas/documents";

function includesAny(text: string, keywords: readonly string[]): string[] {
  return keywords.filter((keyword) => text.includes(keyword.toLowerCase()));
}

function countLabLikeLines(text: string): number {
  return text
    .split(/\r?\n/)
    .filter((line) => /\b\d+(?:\.\d+)?\s*(mg\/dL|mmol\/L|mEq\/L|g\/dL|U\/L|%)\b/i.test(line))
    .length;
}

export function classifyChunk(chunk: ParsedChunk): ChunkClassification {
  const text = chunk.text.toLowerCase();
  const reasons: string[] = [];

  const imagingHits = includesAny(text, IMAGING_KEYWORDS.map((keyword) => keyword.toLowerCase()));
  if (imagingHits.length > 0 && (text.includes("findings") || text.includes("impression"))) {
    reasons.push(`imaging:${imagingHits.slice(0, 3).join(",")}`);
    return { type: "imaging", confidence: 0.93, reasons };
  }

  const pathologyHits = includesAny(text, PATHOLOGY_KEYWORDS.map((keyword) => keyword.toLowerCase()));
  if (pathologyHits.length > 0 && (text.includes("diagnosis") || text.includes("specimen"))) {
    reasons.push(`pathology:${pathologyHits.slice(0, 3).join(",")}`);
    return { type: "pathology", confidence: 0.92, reasons };
  }

  const medicationHits = includesAny(text, MEDICATION_KEYWORDS.map((keyword) => keyword.toLowerCase()));
  if (medicationHits.length >= 2 && /\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml)\b/i.test(chunk.text)) {
    reasons.push(`medication:${medicationHits.slice(0, 3).join(",")}`);
    return { type: "medication", confidence: 0.86, reasons };
  }

  const labHits = includesAny(text, [...LAB_KEYWORDS_SAFE, ...LAB_KEYWORDS_STRICT].map((keyword) => keyword.toLowerCase()));
  const labSectionHits = includesAny(text, LAB_SECTION_HINTS);
  const labLikeLines = countLabLikeLines(chunk.text);
  if ((labHits.length > 0 || labSectionHits.length > 0) && labLikeLines > 0) {
    reasons.push(`lab:${[...labHits.slice(0, 3), ...labSectionHits.slice(0, 2)].join(",")}`);
    return { type: "lab", confidence: labLikeLines >= 2 ? 0.9 : 0.8, reasons };
  }

  if (NOTE_TITLE_PATTERNS.some((pattern) => pattern.test(chunk.text))) {
    reasons.push("note:title_pattern");
    return { type: "note", confidence: 0.8, reasons };
  }

  if (/\b(subjective|objective|assessment|plan)\b/i.test(chunk.text) || /\b주호소|현병력|과거력|계획\b/.test(chunk.text)) {
    reasons.push("note:soap_sections");
    return { type: "note", confidence: 0.76, reasons };
  }

  reasons.push("fallback:unknown");
  return { type: "unknown", confidence: 0.35, reasons };
}
