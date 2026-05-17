import { LAB_KEYWORDS_SAFE, LAB_KEYWORDS_STRICT, RECORD_STARTERS, SECTION_CANONICAL_MAP } from "./constants";

export type LineType = "lab" | "order" | "narrative" | "empty" | "header";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function cleanEmrFullwidthSpaces(text: string, preserveIndent = false): string {
  if (preserveIndent) {
    return text.replace(/\u3000/g, "    ");
  }
  return text.replace(/\u3000/g, " ");
}

export function classifyLine(line: string): LineType {
  const stripped = line.trim();
  if (!stripped) return "empty";

  if (/^(Problem|S|O|A|P(?:\(.*?\))?|기본정보|진단정보|의뢰내용|회신내용|주호소|현병력|과거력|계획)\s*>?\s*$/.test(stripped)) {
    return "header";
  }

  const hasNumber = /\d+\.?\d*/.test(stripped);
  const hasFlag = /[▲▼↑↓★]/.test(stripped) || /(?<!\w)[HL](?!\w)/.test(stripped);
  const hasUnit = /(?:mg\/dL|mmol\/L|mEq\/L|g\/dL|U\/L|μmol\/L|pg\/mL|ng\/mL|cells\/μL|mm\/hr|IU\/L|ng\/L|mcg\/L)\b|%/i.test(stripped);
  const hasRefRange = /\b\d+\.?\d*\s*[~–-]\s*\d+\.?\d*\b/.test(stripped);
  const hasLabPrefix = /^\s*\((혈액|응급|일반|화학|뇨|면역|미생물|분자|진단|수탁)\)/.test(stripped);
  const hasKwSafe = LAB_KEYWORDS_SAFE.some((keyword) => new RegExp(`\\b${escapeRegExp(keyword)}\\b`, "i").test(stripped));
  const hasKwStrict = LAB_KEYWORDS_STRICT.some((keyword) => new RegExp(`\\b${escapeRegExp(keyword)}\\b`).test(stripped));
  const hasLabKeyword = hasKwSafe || hasKwStrict;

  if (/^\s*E'\s+[\d-]+/.test(stripped)) return "lab";
  if (/^\s*(V|A)BGA\s+[\d.\-\s]+/.test(stripped)) return "lab";

  let labSignals = 0;
  if (hasFlag) labSignals += 1;
  if (hasUnit) labSignals += 1;
  if (hasRefRange) labSignals += 2;
  if (hasLabPrefix) labSignals += 1;
  if (hasLabKeyword) labSignals += 2;
  if (hasNumber && labSignals >= 2) return "lab";

  if (/^\s*\d{4}[-/.]?\d{2}[-/.]?\d{2}/.test(stripped)) {
    const parts = stripped.split(/\s+/);
    if (parts.length >= 3) return "order";
  }

  return "narrative";
}

export function normalizeSpacesForLine(line: string, lineType: LineType): string {
  if (lineType === "empty" || lineType === "header") return line;

  if (lineType === "narrative") {
    const leading = line.length - line.trimStart().length;
    const indent = leading > 0 ? " " : "";
    const body = line.trim().replace(/ {2,}/g, " ");
    return body ? indent + body : "";
  }

  if (lineType === "lab" || lineType === "order") {
    const stripped = line.trim();
    if (!stripped) return "";

    let normalized = stripped.replace(/ {3,}/g, "\t");
    normalized = normalized.replace(/\t +/g, "\t");
    normalized = normalized.replace(/ +\t/g, "\t");
    normalized = normalized.replace(/\t{2,}/g, "\t");
    return "\t" + normalized;
  }

  return line;
}

export function cleanEmrNormalizeSpaces(text: string): string {
  return text
    .split(/\r?\n/)
    .map((line) => normalizeSpacesForLine(line, classifyLine(line)))
    .join("\n");
}

export function cleanEmrBlockSeparator(text: string): string {
  const startersPattern = RECORD_STARTERS.map(escapeRegExp).join("|");
  const recordHeaderPattern = new RegExp(`^(?<type>${startersPattern})\\s*/\\s*(?<author>[^(]+)\\((?<status>[^)]+)\\)`);
  const lines = text.split(/\r?\n/);
  const result: string[] = [];
  let firstBlock = true;

  for (const line of lines) {
    const match = recordHeaderPattern.exec(line.trim());
    if (match?.groups) {
      if (!firstBlock) result.push("");
      const header = "=".repeat(50);
      result.push(header);
      result.push(`${match.groups.type} | ${match.groups.author.trim()} | ${match.groups.status.trim()}`);
      result.push(header);
      firstBlock = false;
      continue;
    }

    result.push(line);
  }

  return result.join("\n");
}

export function cleanEmrSectionHeaders(text: string): string {
  const lines = text.split(/\r?\n/);
  const result: string[] = [];
  const sectionPattern = /^\s*([^>]+?)\s*>\s*$/;

  for (const line of lines) {
    const match = sectionPattern.exec(line);
    if (!match) {
      result.push(line);
      continue;
    }

    const rawSection = match[1].trim();
    if (/\d+\s*(?:mg|mL|mmHg|%|L|kg|cm|bpm)/i.test(rawSection)) {
      result.push(line);
      continue;
    }

    const canonical = SECTION_CANONICAL_MAP[rawSection] || rawSection;
    result.push(`\n[${canonical}]`);
  }

  return result.join("\n");
}

export function cleanEmrEmptyLines(text: string): string {
  return text.replace(/\n{3,}/g, "\n\n");
}

export function normalizeEmrText(text: string): string {
  return cleanEmrEmptyLines(cleanEmrSectionHeaders(cleanEmrBlockSeparator(cleanEmrNormalizeSpaces(cleanEmrFullwidthSpaces(text)))));
}
