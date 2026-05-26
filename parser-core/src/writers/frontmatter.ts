import { BaseMetadata } from "../schemas/documents";

function yamlValue(value: string | number | boolean | undefined): string {
  if (value === undefined) return "";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return `"${value.replace(/"/g, '\\"')}"`;
}

export function renderFrontmatter(metadata: BaseMetadata): string {
  const lines = [
    "---",
    `type: ${yamlValue(metadata.type)}`,
    `source: ${yamlValue(metadata.source)}`,
    `patient_id: ${yamlValue(metadata.patientId)}`,
    `source_artifact_id: ${yamlValue(metadata.sourceArtifactId)}`,
    `source_path: ${yamlValue(metadata.sourcePath)}`,
    `date: ${yamlValue(metadata.date)}`,
    `department: ${yamlValue(metadata.department)}`,
    `title: ${yamlValue(metadata.title)}`,
    `modality: ${yamlValue(metadata.modality)}`,
    `body_part: ${yamlValue(metadata.bodyPart)}`,
    `parser_version: ${yamlValue(metadata.parserVersion)}`,
    `confidence: ${yamlValue(metadata.confidence)}`,
    `review_required: ${yamlValue(metadata.reviewRequired)}`,
    "tags:",
    ...metadata.tags.map((tag) => `  - "${tag.replace(/"/g, '\\"')}"`),
    "---",
  ];

  return lines.filter((line) => line !== "").join("\n");
}
