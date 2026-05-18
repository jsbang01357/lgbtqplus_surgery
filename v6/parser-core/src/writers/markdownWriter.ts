import { StructuredMarkdownDocument } from "../schemas/documents";
import { renderFrontmatter } from "./frontmatter";

export function renderMarkdownDocument(document: StructuredMarkdownDocument): string {
  const sections = document.sections
    .map((section) => `# ${section.heading}\n\n${section.body}`.trim())
    .join("\n\n");

  return `${renderFrontmatter(document.metadata)}\n\n${sections}\n`;
}
