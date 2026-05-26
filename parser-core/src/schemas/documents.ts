export type DocumentKind =
  | "lab"
  | "medication"
  | "imaging"
  | "pathology"
  | "note"
  | "unknown";

export type NoteSubtype =
  | "progress_note"
  | "admission_note"
  | "consult_note"
  | "discharge_summary"
  | "clinical_note";

export interface SourceArtifact {
  artifactId: string;
  patientId: string;
  source: "emr" | "pdf" | "image" | "ocr" | "manual";
  sourcePath: string;
  capturedAt?: string;
  filename?: string;
  contentType?: string;
  rawText: string;
}

export interface BaseMetadata {
  patientId: string;
  type: DocumentKind;
  source: SourceArtifact["source"];
  sourceArtifactId: string;
  sourcePath: string;
  date?: string;
  department?: string;
  title?: string;
  modality?: string;
  bodyPart?: string;
  tags: string[];
  parserVersion: string;
  confidence: number;
  reviewRequired: boolean;
}

export interface ParsedChunk {
  chunkId: string;
  patientId: string;
  sourceArtifactId: string;
  index: number;
  title?: string;
  date?: string;
  text: string;
  hints: string[];
}

export interface ChunkClassification {
  type: DocumentKind;
  confidence: number;
  reasons: string[];
}

export interface LabRow {
  date?: string;
  panel?: string;
  testName: string;
  value: string;
  unit?: string;
  referenceRange?: string;
  flag?: "high" | "low" | "normal" | "unknown" | "up" | "down";
  rawLine: string;
}

export interface MedicationRow {
  date?: string;
  medication: string;
  dose?: string;
  unit?: string;
  route?: string;
  frequency?: string;
  status?: "start" | "continue" | "stop" | "change" | "unknown";
  rawLine: string;
}

export interface MarkdownSection {
  heading: string;
  body: string;
}

export interface StructuredLabDocument {
  kind: "lab";
  metadata: BaseMetadata;
  rows: LabRow[];
  unparsedLines: string[];
}

export interface StructuredMedicationDocument {
  kind: "medication";
  metadata: BaseMetadata;
  rows: MedicationRow[];
  unparsedLines: string[];
}

export interface StructuredMarkdownDocument {
  kind: "imaging" | "pathology" | "note";
  metadata: BaseMetadata;
  sections: MarkdownSection[];
  rawBody: string;
}

export interface UnknownDocument {
  kind: "unknown";
  metadata: BaseMetadata;
  rawBody: string;
}

export type NormalizedDocument =
  | StructuredLabDocument
  | StructuredMedicationDocument
  | StructuredMarkdownDocument
  | UnknownDocument;

export interface SyncManifestEntry {
  documentId: string;
  patientId: string;
  type: DocumentKind;
  relativePath: string;
  checksum?: string;
  generatedAt: string;
  sourceArtifactId: string;
  reviewRequired: boolean;
  tags: string[];
}
