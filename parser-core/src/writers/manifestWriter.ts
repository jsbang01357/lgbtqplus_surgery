import { createHash } from "node:crypto";

import { NormalizedDocument, SyncManifestEntry } from "../schemas/documents";
import { renderLabCsv, renderMedicationCsv } from "./csvWriter";
import { renderMarkdownDocument } from "./markdownWriter";
import { buildRelativeOutputPath } from "./pathBuilder";

function renderDocumentContent(document: NormalizedDocument): string {
  switch (document.kind) {
    case "lab":
      return renderLabCsv(document);
    case "medication":
      return renderMedicationCsv(document);
    case "imaging":
    case "pathology":
    case "note":
      return renderMarkdownDocument(document);
    case "unknown":
      return document.rawBody;
  }
}

export function buildSyncManifestEntry(document: NormalizedDocument): SyncManifestEntry {
  const content = renderDocumentContent(document);
  const checksum = createHash("sha256").update(content).digest("hex");

  return {
    documentId: `${document.metadata.sourceArtifactId}:${buildRelativeOutputPath(document)}`,
    patientId: document.metadata.patientId,
    type: document.kind,
    relativePath: buildRelativeOutputPath(document),
    checksum,
    generatedAt: new Date().toISOString(),
    sourceArtifactId: document.metadata.sourceArtifactId,
    reviewRequired: document.metadata.reviewRequired,
    tags: document.metadata.tags,
  };
}
