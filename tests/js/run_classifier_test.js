const fs = require('fs');
const { splitEmrIntoChunks } = require('../../v6/parser-core/dist/splitters/emrChunkSplitter');
const { classifyChunk } = require('../../v6/parser-core/dist/classifiers/modalityClassifier');

const text = fs.readFileSync("변영* 검사통합.txt", "utf-8");
const artifact = { artifactId: "test", patientId: "p1", rawText: text };
const chunks = splitEmrIntoChunks(artifact);
chunks.forEach((c, idx) => {
    const classResult = classifyChunk(c);
    console.log(`Chunk ${idx + 1}: ${classResult.type} (reasons: ${classResult.reasons.join(' | ')})`);
});
