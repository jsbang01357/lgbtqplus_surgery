import { buildSyncManifestEntry } from "./writers/manifestWriter";
import { buildRelativeOutputPath } from "./writers/pathBuilder";
import { renderLabCsv, renderMedicationCsv } from "./writers/csvWriter";
import { renderMarkdownDocument } from "./writers/markdownWriter";
import { runNormalizationPipeline } from "./pipeline/runNormalizationPipeline";
import { NormalizedDocument, SourceArtifact } from "./schemas/documents";

interface CliInput {
  artifact: SourceArtifact;
}

interface CliDocument {
  kind: NormalizedDocument["kind"];
  metadata: NormalizedDocument["metadata"];
  relativePath: string;
  content: string;
  extra?: Record<string, unknown>;
}

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

function summarizeDocument(document: NormalizedDocument): Record<string, unknown> | undefined {
  switch (document.kind) {
    case "lab":
      return {
        rowCount: document.rows.length,
        unparsedCount: document.unparsedLines.length,
      };
    case "medication":
      return {
        rowCount: document.rows.length,
        unparsedCount: document.unparsedLines.length,
      };
    case "imaging":
    case "pathology":
    case "note":
      return {
        sectionCount: document.sections.length,
      };
    default:
      return undefined;
  }
}

async function readJsonFromStdin(): Promise<CliInput> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8")) as CliInput;
}

async function main(): Promise<void> {
  const payload = await readJsonFromStdin();
  const documents = runNormalizationPipeline(payload.artifact);
  const responseDocuments: CliDocument[] = documents.map((document) => ({
    kind: document.kind,
    metadata: document.metadata,
    relativePath: buildRelativeOutputPath(document),
    content: renderDocumentContent(document),
    extra: summarizeDocument(document),
  }));

  const manifest = documents.map((document) => buildSyncManifestEntry(document));
  process.stdout.write(JSON.stringify({ ok: true, documents: responseDocuments, manifest }));
}

main().catch((error) => {
  process.stderr.write(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
