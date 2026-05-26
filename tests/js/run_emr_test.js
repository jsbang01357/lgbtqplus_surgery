const fs = require('fs');
const { execSync } = require('child_process');

const filePath = "tests/변영* EMR.txt";
const text = fs.readFileSync(filePath, "utf-8");
const payload = {
  artifact: {
    artifactId: "test-emr-dump",
    patientId: "patient_emr",
    source: "emr",
    sourcePath: filePath,
    rawText: text
  }
};

try {
  const result = execSync("node parser-core/dist/cli.js", {
    input: JSON.stringify(payload),
    encoding: "utf-8"
  });

  const parsed = JSON.parse(result);
  console.log(`\n=== EMR Parsing Result ===`);
  console.log(`Total chunks extracted: ${parsed.documents.length}\n`);

  const modalityCount = {};
  
  parsed.documents.forEach((doc, idx) => {
    modalityCount[doc.kind] = (modalityCount[doc.kind] || 0) + 1;
    console.log(`[${String(idx + 1).padStart(2, '0')}] ${doc.kind.toUpperCase()}`);
    console.log(`    Path: ${doc.relativePath}`);
    
    if (doc.kind === 'lab' || doc.kind === 'medication') {
        const rowCount = doc.content.split('\n').length - 6; // Subtract metadata headers + header row
        console.log(`    Rows: ${rowCount}`);
    } else {
        const size = Buffer.byteLength(doc.content, 'utf8');
        console.log(`    Size: ${size} bytes`);
    }
  });
  
  console.log(`\n=== Summary ===`);
  console.log(modalityCount);

} catch (err) {
  console.error("Test failed:", err.message);
}
