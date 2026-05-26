import { classifyChunk } from "../classifiers/modalityClassifier";
import { normalizeEmrText } from "../core/textNormalizer";
import { parseImagingChunk } from "../parsers/imaging/parseImagingChunk";
import { parseLabChunk } from "../parsers/labs/parseLabChunk";
import { parseMedicationChunk } from "../parsers/medications/parseMedicationChunk";
import { parseClinicalNoteChunk } from "../parsers/notes/parseClinicalNoteChunk";
import { parsePathologyChunk } from "../parsers/pathology/parsePathologyChunk";
import { BaseMetadata, NormalizedDocument, ParsedChunk, SourceArtifact } from "../schemas/documents";
import { splitEmrIntoChunks } from "../splitters/emrChunkSplitter";
import { PARSER_VERSION } from "../core/constants";

function createUnknownDocument(chunk: ParsedChunk): NormalizedDocument {
  const metadata: BaseMetadata = {
    patientId: chunk.patientId,
    type: "unknown",
    source: "emr",
    sourceArtifactId: chunk.sourceArtifactId,
    sourcePath: "",
    date: chunk.date,
    title: chunk.title || "unknown_chunk",
    tags: ["unknown"],
    parserVersion: PARSER_VERSION,
    confidence: 0.2,
    reviewRequired: true,
  };

  return {
    kind: "unknown",
    metadata,
    rawBody: chunk.text,
  };
}

export function runNormalizationPipeline(artifact: SourceArtifact): NormalizedDocument[] {
  const normalizedArtifact: SourceArtifact = {
    ...artifact,
    rawText: normalizeEmrText(artifact.rawText),
  };

  const chunks = splitEmrIntoChunks(normalizedArtifact);
  return chunks.map((chunk) => {
    const classification = classifyChunk(chunk);
    switch (classification.type) {
      case "lab":
        return parseLabChunk(chunk);
      case "medication":
        return parseMedicationChunk(chunk);
      case "imaging":
        return parseImagingChunk(chunk);
      case "pathology":
        return parsePathologyChunk(chunk);
      case "note":
        return parseClinicalNoteChunk(chunk);
      default:
        return createUnknownDocument(chunk);
    }
  });
}
