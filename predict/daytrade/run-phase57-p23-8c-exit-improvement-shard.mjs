import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { EXPANDED_UNIVERSE, EXPANDED_UNIVERSE_POLICY } from './phase57-expanded-universe.js';
import {
  P23_8C_EXIT_CANDIDATES,
  P23_8C_METHOD_POLICY,
  PHASE57_P23_8C_SAFETY,
} from './phase57-p23-8c-exit-candidates.js';

const SHARD_COUNT = Number(process.env.PHASE57_SHARD_COUNT || 3);
const SHARD_INDEX = Number(process.env.PHASE57_SHARD_INDEX || 0);
if (!Number.isInteger(SHARD_COUNT) || SHARD_COUNT <= 0) throw new Error('PHASE57_SHARD_COUNT must be a positive integer');
if (!Number.isInteger(SHARD_INDEX) || SHARD_INDEX < 0 || SHARD_INDEX >= SHARD_COUNT) throw new Error('PHASE57_SHARD_INDEX out of range');
if (EXPANDED_UNIVERSE.length % SHARD_COUNT !== 0) throw new Error('Frozen universe must divide evenly across shards');

const shardSize = EXPANDED_UNIVERSE.length / SHARD_COUNT;
const shardSymbols = EXPANDED_UNIVERSE.slice(SHARD_INDEX * shardSize, (SHARD_INDEX + 1) * shardSize);
if (!shardSymbols.length) throw new Error('empty shard');

process.env.PHASE57_SCOPE = 'COMBINED';

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.join(here, 'run-phase57-real-nested-state-machine.mjs');
const runtimePath = path.join(here, `.phase57-p23-8c-exit-shard-${SHARD_INDEX}-runtime.mjs`);
const originalUniverse = "const universe = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];";
const originalConcurrentFetch = "const fetchedBarsBySymbol = new Map(await Promise.all(symbols.map(async symbol => [symbol, await fetchBars(symbol)])));";
const nestedMarker = 'const nestedStateMachine = evaluateRealNestedStateMachine(exitRows, nestedSessionPolicy);';
const summaryMarker = 'const summary = {';

let source = fs.readFileSync(sourcePath, 'utf8');
for (const [marker, label] of [
  [originalUniverse, 'frozen P23.6 universe'],
  [originalConcurrentFetch, 'P23.6 concurrent fetch'],
  [nestedMarker, 'nested state-machine evaluation'],
  [summaryMarker, 'summary object'],
]) {
  if (!source.includes(marker)) throw new Error(`P23.8C source patch failed: ${label} marker not found`);
}

source = `import { evaluateNestedEntryExitQuality } from './phase57-entry-exit-quality.js';\nimport { P23_8C_EXIT_CANDIDATES } from './phase57-p23-8c-exit-candidates.js';\n${source}`;
source = source.replace(originalUniverse, `const universe = ${JSON.stringify(shardSymbols)};`);
source = source.replace(originalConcurrentFetch, `const fetchedPairs = [];
for (let start = 0; start < symbols.length; start += 5) {
  const batch = symbols.slice(start, start + 5);
  fetchedPairs.push(...await Promise.all(batch.map(async symbol => [symbol, await fetchBars(symbol)])));
  if (start + 5 < symbols.length) await sleep(1000);
}
const fetchedBarsBySymbol = new Map(fetchedPairs);`);
source = source.replace(nestedMarker, `const nestedStateMachine = evaluateRealNestedStateMachine(exitRows, { ...nestedSessionPolicy, candidates: P23_8C_EXIT_CANDIDATES });\nconst p23_8cEntryExitQuality = evaluateNestedEntryExitQuality({ rows: exitRows, nestedResult: nestedStateMachine });`);
source = source.replace(summaryMarker, `${summaryMarker}\n  entryExitQuality: p23_8cEntryExitQuality,`);
source = source.replaceAll('57.p23.6-real', `57.p23.8c-exit-shard-${SHARD_INDEX + 1}`);
source = source.replaceAll('PHASE57_P23_6_REAL_NESTED', `PHASE57_P23_8C_EXIT_SHARD_${SHARD_INDEX + 1}`);

fs.writeFileSync(runtimePath, source);
try {
  await import(`${pathToFileURL(runtimePath).href}?v=${Date.now()}`);
} finally {
  fs.rmSync(runtimePath, { force: true });
}

const baseArtifact = path.resolve('artifacts/phase57-real-nested-state-machine-COMBINED.json');
if (!fs.existsSync(baseArtifact)) throw new Error('P23.8C base artifact missing');
const data = JSON.parse(fs.readFileSync(baseArtifact, 'utf8'));

const candidateIds = P23_8C_EXIT_CANDIDATES.map(candidate => candidate.id);
const nestedCandidateIds = (data.nestedStateMachine?.stateMachine?.candidateUniverse || []).map(candidate => candidate.id);

data.phase = `57.p23.8c-exit-improvement-shard-${SHARD_INDEX + 1}`;
data.status = 'REAL_5M_P23_8C_EXIT_IMPROVEMENT_SHARD_DEVELOPMENT_OOS_MEASURED';
data.universePolicy = EXPANDED_UNIVERSE_POLICY;
data.exitImprovementPolicy = {
  mode: 'THREE_BY_TEN_PARALLEL_EXIT_IMPROVEMENT_DEVELOPMENT_DIAGNOSTIC',
  shardIndex: SHARD_INDEX,
  shardNumber: SHARD_INDEX + 1,
  shardCount: SHARD_COUNT,
  shardSize,
  shardSymbols,
  exactFrozenShard: JSON.stringify(data.symbols) === JSON.stringify(shardSymbols),
  candidateIds,
  exactFrozenCandidateUniverse: JSON.stringify(candidateIds) === JSON.stringify(nestedCandidateIds),
  ...P23_8C_METHOD_POLICY,
};
data.p23_8cSafety = PHASE57_P23_8C_SAFETY;
data.limitations = [
  ...(data.limitations || []),
  'P23.8C reuses the recent development window after P23.8 diagnostics informed candidate design; any improvement is development evidence only and cannot be treated as fresh untouched OOS evidence.',
  'Future extrema, MFE, MAE, capture and giveback remain evaluation-only and never participate in candidate selection or trade decisions.',
  'The 10-symbol shards are robustness diagnostics and do not replace a pooled 30-symbol or future fresh-market evaluation.',
];

const out = path.resolve(`artifacts/phase57-p23-8c-exit-improvement-shard-${SHARD_INDEX + 1}.json`);
fs.writeFileSync(out, JSON.stringify(data, null, 2));
console.log(`PHASE57_P23_8C_EXIT_SHARD_DONE shard=${SHARD_INDEX + 1}/${SHARD_COUNT} symbols=${shardSymbols.join(',')} output=${out}`);
