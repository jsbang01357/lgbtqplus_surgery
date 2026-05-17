import { StructuredLabDocument, StructuredMedicationDocument } from "../schemas/documents";

function escapeCsv(value: string | undefined): string {
  const normalized = value ?? "";
  if (/[",\n]/.test(normalized)) {
    return `"${normalized.replace(/"/g, '""')}"`;
  }
  return normalized;
}

export function renderLabCsv(document: StructuredLabDocument): string {
  const header = ["date", "panel", "test_name", "value", "unit", "reference_range", "flag"];
  const rows = document.rows.map((row) =>
    [
      row.date,
      row.panel,
      row.testName,
      row.value,
      row.unit,
      row.referenceRange,
      row.flag,
    ]
      .map(escapeCsv)
      .join(","),
  );

  return [header.join(","), ...rows].join("\n");
}

export function renderMedicationCsv(document: StructuredMedicationDocument): string {
  const header = ["date", "medication", "dose", "unit", "route", "frequency", "status"];
  const rows = document.rows.map((row) =>
    [
      row.date,
      row.medication,
      row.dose,
      row.unit,
      row.route,
      row.frequency,
      row.status,
    ]
      .map(escapeCsv)
      .join(","),
  );

  return [header.join(","), ...rows].join("\n");
}
