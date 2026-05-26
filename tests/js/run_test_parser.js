const fs = require('fs');
const { execSync } = require('child_process');

const text = fs.readFileSync("변영* 검사통합.txt", "utf-8");
const payload = {
  artifact: {
    artifactId: "test-123",
    patientId: "patient_001",
    source: "emr",
    sourcePath: "변영* 검사통합.txt",
    rawText: text
  }
};

const result = execSync("node parser-core/dist/cli.js", {
  input: JSON.stringify(payload),
  encoding: "utf-8"
});

const parsed = JSON.parse(result);
console.log(`Total documents: ${parsed.documents.length}`);
parsed.documents.forEach((doc, idx) => {
  console.log(`\n--- Document ${idx + 1}: ${doc.kind} ---`);
  console.log(`Path: ${doc.relativePath}`);
  console.log(`Summary:`, doc.extra);
  if (doc.kind === 'lab') {
      const lines = doc.content.split('\n');
      console.log(`Sample CSV:\n${lines.slice(0, 10).join('\n')}`);
  }
});
