import { IMAGING_MODALITY_TITLES, LAB_SECTION_HINTS, NOTE_TITLE_PATTERNS, PATHOLOGY_KEYWORDS } from "../core/constants";
import { ParsedChunk, SourceArtifact } from "../schemas/documents";

const DATE_RE = /\b(20\d{2}[-/.]\d{2}[-/.]\d{2})\b/;
const SEPARATOR_RE = /^={10,}$/;
const FINDINGS_RE = /^findings[:\s]/i;
const IMPRESSION_RE = /^impression[:\s]/i;

type ChunkMode = "unknown" | "note" | "lab" | "imaging" | "pathology";

function slugifyChunkTitle(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function isLabSectionHeader(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) return false;
  const inner = trimmed.slice(1, -1).trim().toLowerCase();
  return LAB_SECTION_HINTS.some((hint) => inner.includes(hint));
}

function isImagingTitle(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  if (FINDINGS_RE.test(trimmed) || IMPRESSION_RE.test(trimmed)) return false;
  return IMAGING_MODALITY_TITLES.some((title) => new RegExp(`\\b${title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i").test(trimmed));
}

function isPathologyTitle(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  return PATHOLOGY_KEYWORDS.some((keyword) => trimmed.toLowerCase().includes(keyword.toLowerCase()));
}

function inferChunkMode(lines: string[]): ChunkMode {
  const text = lines.join("\n");
  if (NOTE_TITLE_PATTERNS.some((pattern) => pattern.test(text)) || /\bsubjective|objective|assessment|plan\b/i.test(text)) {
    return "note";
  }
  if (FINDINGS_RE.test(text) || IMPRESSION_RE.test(text) || isImagingTitle(text)) {
    return "imaging";
  }
  if (isPathologyTitle(text)) {
    return "pathology";
  }
  if (lines.some((line) => isLabSectionHeader(line)) || lines.some((line) => /\b\d+(?:\.\d+)?\s*(mg\/dL|mmol\/L|mEq\/L|g\/dL|U\/L|%)\b/i.test(line))) {
    return "lab";
  }
  return "unknown";
}

function shouldStartNewChunk(current: string[], line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed || current.length === 0) return false;
  if (SEPARATOR_RE.test(trimmed)) return true;
  if (NOTE_TITLE_PATTERNS.some((pattern) => pattern.test(trimmed))) return true;
  if (DATE_RE.test(trimmed) && /note|report|summary|consult|discharge/i.test(trimmed)) return true;

  const currentMode = inferChunkMode(current);
  if (isLabSectionHeader(trimmed) && currentMode === "note") {
    return true;
  }
  if (isImagingTitle(trimmed) && currentMode !== "imaging") {
    return true;
  }
  if (isPathologyTitle(trimmed) && currentMode !== "pathology") {
    return true;
  }
  return false;
}

function inferChunkTitle(text: string): string | undefined {
  const firstContentLine = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);

  if (!firstContentLine) return undefined;
  return slugifyChunkTitle(firstContentLine);
}

function inferChunkDate(text: string): string | undefined {
  const match = DATE_RE.exec(text);
  if (!match) return undefined;
  return match[1].replace(/\./g, "-").replace(/\//g, "-");
}

export function splitEmrIntoChunks(artifact: SourceArtifact): ParsedChunk[] {
  const lines = artifact.rawText.split(/\r?\n/);
  const buckets: string[][] = [];
  let current: string[] = [];

  for (const line of lines) {
    if (shouldStartNewChunk(current, line)) {
      buckets.push(current);
      current = [];
    }
    current.push(line);
  }

  if (current.length > 0) {
    buckets.push(current);
  }

  if (buckets.length === 0) {
    buckets.push([artifact.rawText]);
  }

  const parsedChunks: ParsedChunk[] = [];
  let lastKnownDate: string | undefined;

  buckets.forEach((bucket, index) => {
    const text = bucket.join("\n").trim();
    if (!text) return;

    const title = inferChunkTitle(text);
    const date = inferChunkDate(text) || lastKnownDate;
    if (date) {
      lastKnownDate = date;
    }
    parsedChunks.push({
      chunkId: `${artifact.artifactId}-chunk-${String(index + 1).padStart(3, "0")}`,
      patientId: artifact.patientId,
      sourceArtifactId: artifact.artifactId,
      index,
      title,
      date,
      text,
      hints: [
        ...(title ? [`title:${title}`] : []),
        ...(date ? [`date:${date}`] : []),
      ],
    });
  });

  return parsedChunks;
}
