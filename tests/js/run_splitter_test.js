const fs = require('fs');
const { splitEmrIntoChunks } = require('../../v6/parser-core/dist/splitters/emrChunkSplitter');

const text = fs.readFileSync("변영* 검사통합.txt", "utf-8");
const artifact = { artifactId: "test", patientId: "p1", rawText: text };
const chunks = splitEmrIntoChunks(artifact);
console.log(`Split into ${chunks.length} chunks`);
chunks.forEach((c, idx) => {
    console.log(`\nChunk ${idx + 1} (${c.text.split('\n').length} lines):`);
    console.log(c.text.slice(0, 100) + "...");
});
