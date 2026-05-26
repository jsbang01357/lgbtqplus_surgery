import { NormalizedDocument } from "../schemas/documents";

function safeSlug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

function baseFilename(document: NormalizedDocument): string {
  const date = document.metadata.date || "undated";
  const title = safeSlug(document.metadata.title || document.kind);
  return `${date}_${title}`;
}

export function buildRelativeOutputPath(document: NormalizedDocument): string {
  const filename = baseFilename(document);
  const patientId = document.metadata.patientId || "unknown_patient";
  const prefix = `workspace/${patientId}`;

  switch (document.kind) {
    case "lab":
      return `${prefix}/labs/${filename}.csv`;
    case "medication":
      return `${prefix}/medications/${filename}.csv`;
    case "imaging":
      return `${prefix}/imaging/${filename}.md`;
    case "pathology":
      return `${prefix}/pathology/${filename}.md`;
    case "note":
      return `${prefix}/notes/${filename}.md`;
    default:
      return `${prefix}/artifacts/${filename}.txt`;
  }
}
