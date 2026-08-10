import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { EXPANDED_UNIVERSE, EXPANDED_UNIVERSE_POLICY } from './phase57-expanded-universe.js';

process.env.PHASE57_SCOPE = 'COMBINED';

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.join(here, 'run-phase57-real-nested-state-machine.mjs');
const runtimePath = path.join(here, '.phase57-expanded-runtime.mjs');
const originalUniverse = "const universe = ['7203.T', '6758.T', '9984.T', '8306.T', '8035.T'];";
const originalConcurrentFetch = "const fetchedBarsBySymbol = new Map(await Promise.all(symbols.map(async symbol => [symbol, await fetchBars(symbol)])));";

let source = fs.readFileSync(sourcePath, 'utf8');
if (!source.includes(originalUniverse)) throw new Error('P23.7 source patch failed: frozen P23.6 universe line not found');
if (!source.includes(originalConcurrentFetch)) throw new Error('P23.7 source patch failed: P23.6 fetch line not found');

source = source.replace(originalUniverse, `const universe = ${JSON.stringify(EXPANDED_UNIVERSE)};`);
source = source.replace(originalConcurrentFetch, `const fetchedPairs = [];
for (let start = 0; start < symbols.length; start += 5) {
  const batch = symbols.slice(start, start + 5);
  fetchedPairs.push(...await Promise.all(batch.map(async symbol => [symbol, await fetchBars(symbol)])));
  if (start + 5 < symbols.length) await sleep(1000);
}
const fetchedBarsBySymbol = new Map(fetchedPairs);`);
source = source.replaceAll('57.p23.6-real', '57.p23.7-expanded-universe');
source = source.replaceAll('PHASE57_P23_6_REAL_NESTED', 'PHASE57_P23_7_EXPANDED_NESTED');

fs.writeFileSync(runtimePath, source);
try {
  await import(`${pathToFileURL(runtimePath).href}?v=${Date.now()}`);
} finally {
  fs.rmSync(runtimePath, { force: true });
}

const baseArtifact = path.resolve('artifacts/phase57-real-nested-state-machine-COMBINED.json');
if (!fs.existsSync(baseArtifact)) throw new Error('P23.7 base artifact missing after expanded run');
const data = JSON.parse(fs.readFileSync(baseArtifact, 'utf8'));
data.phase = '57.p23.7-expanded-universe';
data.status = 'REAL_5M_EXPANDED_UNIVERSE_NESTED_STATE_MACHINE_DEVELOPMENT_OOS_MEASURED';
data.universePolicy = EXPANDED_UNIVERSE_POLICY;
data.expansionIntegrity = {
  symbolCount: data.symbols?.length ?? 0,
  exactFrozenUniverse: JSON.stringify(data.symbols) === JSON.stringify(EXPANDED_UNIVERSE),
  signalThresholdsRelaxedForSampleExpansion: false,
  exitThresholdsRelaxedForSampleExpansion: false,
  p23_6OutcomeDrivenSymbolSelection: false,
  fetchBatchSize: 5,
};
data.limitations = [
  ...(data.limitations || []),
  'P23.7 expands the pre-registered symbol basket only; entry thresholds, nested selection objective, explicit cost, and state-machine candidate universe are not loosened to manufacture sample size.',
  'The 30-symbol basket is a fixed development universe, not a claim of formal index membership or an exhaustive liquidity ranking.',
];
const out = path.resolve('artifacts/phase57-expanded-universe-state-machine-COMBINED.json');
fs.writeFileSync(out, JSON.stringify(data, null, 2));
console.log(`PHASE57_P23_7_EXPANDED_UNIVERSE_DONE ${out}`);
