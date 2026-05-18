import { PARSER_VERSION } from "../../core/constants";
import { BaseMetadata, LabRow, ParsedChunk, StructuredLabDocument } from "../../schemas/documents";

const UNIT_RE = /^(?:mg\/dL|mmol\/L|mEq\/L|g\/dL|U\/L|IU\/L|ng\/mL|pg\/mL|%|fL|pg|sec|cells\/HPF|\/LPF|×10[³\^]3?\/㎕|×10\^6\/㎕|g\/㎗|mm\/h|mL\/min\/1\.73m²|copies\/mL|log\s+copies\/mL|Ratio|Index|units|mIU\/L|nmol\/L|μg\/dL|mcg\/dL|μU\/mL|mU\/L)$/i;
const FLAG_RE = /^[▲▼HL]$/i;
const COLUMN_HEADER_RE = /^\s*(검사명|Test)\s+/i;

function normalizeLine(line: string): string {
  return line.replace(/\u3000/g, "  ").replace(/\t/g, "  ").trimEnd().replace(/ {2,}/g, "  ");
}

function splitColumns(line: string): string[] {
  return line.trim().split(/[ \t]{2,}/).filter(Boolean);
}

function inferFlag(value: string, ref: string): LabRow["flag"] {
  if (value.endsWith("▲") || /\bH\b/i.test(value)) return "high";
  if (value.endsWith("▼") || /\bL\b/i.test(value)) return "low";

  const numericValue = parseFloat(value.replace(/[^\d.-]/g, ""));
  const rangeMatch = ref.match(/(-?\d+(?:\.\d+)?)\s*[~-]\s*(-?\d+(?:\.\d+)?)/);
  if (!Number.isNaN(numericValue) && rangeMatch) {
    const low = parseFloat(rangeMatch[1]);
    const high = parseFloat(rangeMatch[2]);
    if (numericValue < low) return "low";
    if (numericValue > high) return "high";
    return "normal";
  }

  return "unknown";
}

function parseRow(line: string, panel?: string, date?: string): LabRow | null {
  const normalized = normalizeLine(line);
  if (!normalized || COLUMN_HEADER_RE.test(normalized)) return null;
  const parts = splitColumns(normalized);
  if (parts.length < 2) return null;

  let testName = parts[0].trim();
  let value = parts[1].trim();
  let unit = "";
  let referenceRange = "";

  if (parts.length >= 3) {
    const third = parts[2].trim();
    if (UNIT_RE.test(third)) {
      unit = third;
      referenceRange = parts.slice(3).join(" ").trim();
    } else if (FLAG_RE.test(third)) {
      value = `${value} ${third}`.trim();
      const fourth = parts[3]?.trim() || "";
      if (UNIT_RE.test(fourth)) {
        unit = fourth;
        referenceRange = parts.slice(4).join(" ").trim();
      } else {
        referenceRange = parts.slice(3).join(" ").trim();
      }
    } else {
      referenceRange = parts.slice(2).join(" ").trim();
    }
  }

  testName = testName.replace(/^[\s.·‥∙⋅•ㆍ-]+/, "").trim();
  if (!testName || !value) return null;

  return {
    date,
    panel,
    testName,
    value,
    unit: unit || undefined,
    referenceRange: referenceRange || undefined,
    flag: inferFlag(value, referenceRange),
    rawLine: normalized,
  };
}

function createMetadata(chunk: ParsedChunk, confidence: number): BaseMetadata {
  return {
    patientId: chunk.patientId,
    type: "lab",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || "lab_results",
    tags: ["lab", "emr"],
    parserVersion: PARSER_VERSION,
    confidence,
    reviewRequired: false,
  };
}

export function parseLabChunk(chunk: ParsedChunk): StructuredLabDocument {
  const rows: LabRow[] = [];
  const unparsedLines: string[] = [];
  let panel = chunk.title || "Lab";

  for (const rawLine of chunk.text.split(/\r?\n/)) {
    const stripped = rawLine.trim();
    if (!stripped) continue;

    if (/^\[[^\]]+\]$/.test(stripped)) {
      panel = stripped.slice(1, -1).trim() || panel;
      continue;
    }

    const parsed = parseRow(stripped, panel, chunk.date);
    if (parsed) {
      rows.push(parsed);
    } else if (!/^(findings|impression|diagnosis)$/i.test(stripped)) {
      unparsedLines.push(stripped);
    }
  }

  const confidence = rows.length > 0 ? 0.82 : 0.35;
  const metadata = createMetadata(chunk, confidence);
  metadata.reviewRequired = rows.length === 0 || unparsedLines.length > rows.length;

  return {
    kind: "lab",
    metadata,
    rows,
    unparsedLines,
  };
}
