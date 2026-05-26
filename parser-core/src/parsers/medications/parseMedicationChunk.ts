import { PARSER_VERSION } from "../../core/constants";
import { BaseMetadata, MedicationRow, ParsedChunk, StructuredMedicationDocument } from "../../schemas/documents";

const MED_PATTERN = /^(?<medication>[A-Za-z0-9가-힣\/\-\(\) ]+?)\s+(?<dose>\d+(?:\.\d+)?)\s*(?<unit>mg|mcg|g|mL|tab|cap)?\s*(?<route>PO|IV|IM|SC|PRN|P\/O)?\s*(?<frequency>BID|TID|QID|qd|daily|qhs|q\d+h)?/i;

function detectStatus(line: string): MedicationRow["status"] {
  if (/stop|discontinue|중단/i.test(line)) return "stop";
  if (/change|increase|decrease|변경|증량|감량/i.test(line)) return "change";
  if (/start|begin|new|시작/i.test(line)) return "start";
  if (/continue|유지/i.test(line)) return "continue";
  return "unknown";
}

function createMetadata(chunk: ParsedChunk, confidence: number): BaseMetadata {
  return {
    patientId: chunk.patientId,
    type: "medication",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || "medications",
    tags: ["medication", "emr"],
    parserVersion: PARSER_VERSION,
    confidence,
    reviewRequired: false,
  };
}

export function parseMedicationChunk(chunk: ParsedChunk): StructuredMedicationDocument {
  const rows: MedicationRow[] = [];
  const unparsedLines: string[] = [];

  for (const rawLine of chunk.text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;

    const match = MED_PATTERN.exec(line);
    if (!match?.groups) {
      unparsedLines.push(line);
      continue;
    }

    rows.push({
      date: chunk.date,
      medication: match.groups.medication.trim(),
      dose: match.groups.dose,
      unit: match.groups.unit || undefined,
      route: match.groups.route || undefined,
      frequency: match.groups.frequency || undefined,
      status: detectStatus(line),
      rawLine: line,
    });
  }

  const confidence = rows.length > 0 ? 0.7 : 0.3;
  const metadata = createMetadata(chunk, confidence);
  metadata.reviewRequired = rows.length === 0 || unparsedLines.length > rows.length;

  return {
    kind: "medication",
    metadata,
    rows,
    unparsedLines,
  };
}
