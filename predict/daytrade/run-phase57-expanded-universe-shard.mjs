import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { EXPANDED_UNIVERSE, EXPANDED_UNIVERSE_POLICY } from './phase57-expanded-universe.js';

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
const runtimePath = path.join(here, `.phase57-expanded-shard-${SHARD_INDEX}-runtime.mjs`);
const originalUniverse = "const universe = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];";
const originalConcurrentFetch = "const fetchedBarsBySymbol = new Map(await Promise.all(symbols.map(async symbol => [symbol, await fetchBars(symbol)])));";

let source = fs.readFileSync(sourcePath, 'utf8');
if (!source.includes(originalUniverse)) throw new Error('P23.7 shard patch failed: frozen P23.6 universe line not found');
if (!source.includes(originalConcurrentFetch)) throw new Error('P23.7 shard patch failed: P23.6 fetch line not found');

source = source.replace(originalUniverse, `const universe = ${JSON.stringify(shardSymbols)};`);
source = source.replace(originalConcurrentFetch, `const fetchedPairs = [];
for (let start = 0; start < symbols.length; start += 5) {
  const batch = symbols.slice(start, start + 5);
  fetchedPairs.push(...await Promise.all(batch.map(async symbol => [symbol, await fetchBars(symbol)])));
  if (start + 5 < symbols.length) await sleep(1000);
}
const fetchedBarsBySymbol = new Map(fetchedPairs);`);
source = source.replaceAll('57.p23.6-real', `57.p23.7-shard-${SHARD_INDEX + 1}`);
source = source.replaceAll('PHASE57_P23_6_REAL_NESTED', `PHASE57_P23_7_SHARD_${SHARD_INDEX + 1}`);

fs.writeFileSync(runtimePath, source);
try {
  await import(`${pathToFileURL(runtimePath).href}?v=${Date.now()}`);
} finally {
  fs.rmSync(runtimePath, { force: true });
}

const baseArtifact = path.resolve('artifacts/phase57-real-nested-state-machine-COMBINED.json');
if (!fs.existsSync(baseArtifact)) throw new Error('P23.7 shard base artifact missing');
const data = JSON.parse(fs.readFileSync(baseArtifact, 'utf8'));

data.phase = `57.p23.7-shard-${SHARD_INDEX + 1}`;
data.status = 'REAL_5M_EXPANDED_UNIVERSE_SHARD_NESTED_STATE_MACHINE_DEVELOPMENT_OOS_MEASURED';
data.universePolicy = EXPANDED_UNIVERSE_POLICY;
data.shardPolicy = {
  mode: 'THREE_BY_TEN_PARALLEL_DIAGNOSTIC',
  shardIndex: SHARD_INDEX,
  shardNumber: SHARD_INDEX + 1,
  shardCount: SHARD_COUNT,
  shardSize,
  shardSymbols,
  exactFrozenShard: JSON.stringify(data.symbols) === JSON.stringify(shardSymbols),
  pooledThirtySymbolReplacement: false,
  diagnosticOnly: true,
  signalThresholdsRelaxed: false,
  exitThresholdsRelaxed: false,
  outcomeDrivenPartitioning: false,
};
data.limitations = [
  ...(data.limitations || []),
  'This shard run is a parallel robustness diagnostic. It does not replace the exact pooled 30-symbol P23.7 model because each shard fits only on its own frozen 10-symbol subset.',
  'The partition is contiguous and fixed from the pre-registered 30-symbol basket before shard outcomes are observed; no outcome-driven symbol reassignment is allowed.',
];

const out = path.resolve(`artifacts/phase57-expanded-universe-shard-${SHARD_INDEX + 1}.json`);
fs.writeFileSync(out, JSON.stringify(data, null, 2));
console.log(`PHASE57_P23_7_SHARD_DONE shard=${SHARD_INDEX + 1}/${SHARD_COUNT} symbols=${shardSymbols.join(',')} output=${out}`);
