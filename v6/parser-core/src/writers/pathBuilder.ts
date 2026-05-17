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

  switch (document.kind) {
    case "lab":
      return `labs/${filename}.csv`;
    case "medication":
      return `medications/${filename}.csv`;
    case "imaging":
      return `imaging/${filename}.md`;
    case "pathology":
      return `pathology/${filename}.md`;
    case "note":
      return `notes/${filename}.md`;
    default:
      return `artifacts/${filename}.txt`;
  }
}
