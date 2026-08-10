import fs from 'node:fs';
import path from 'node:path';
import { CHART_QUALITY_HOLDOUT_UNIVERSE, CHART_QUALITY_HOLDOUT_POLICY } from './phase57-chart-quality-holdout-universe.js';
import { PHASE57_CHART_PERCEPTION_SAFETY } from './phase57-chart-perception-2.js';

const root = process.argv[2] ?? 'artifacts/p23-10e-shards';

function filesRecursively(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...filesRecursively(p));
    else if (entry.isFile() && entry.name.endsWith('.json')) out.push(p);
  }
  return out;
}

const files = filesRecursively(root).filter(file => file.includes('phase57-p23-10d-setup-quality'));
if (files.length !== 3) throw new Error(`expected exactly 3 shard json files, got ${files.length}`);

const shards = files.map(file => JSON.parse(fs.readFileSync(file, 'utf8')));
const seenSymbols = shards.flatMap(shard => shard.symbols ?? []);
if (seenSymbols.length !== 30 || new Set(seenSymbols).size !== 30) throw new Error('holdout aggregate must contain exactly 30 unique symbols');
for (const symbol of CHART_QUALITY_HOLDOUT_UNIVERSE) if (!seenSymbols.includes(symbol)) throw new Error(`missing holdout symbol ${symbol}`);
for (const symbol of seenSymbols) if (!CHART_QUALITY_HOLDOUT_UNIVERSE.includes(symbol)) throw new Error(`unexpected symbol ${symbol}`);

const records = shards.flatMap(shard => shard.records ?? []);
if (!records.length) throw new Error('no holdout records');

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
}
function summarize(rows, key) {
  const valid = rows.filter(row => row[key]);
  return {
    count: valid.length,
    hitRate: valid.length ? valid.filter(row => row[key].hit).length / valid.length : null,
    averageDirectionalReturnPct: valid.length ? mean(valid.map(row => row[key].directionalReturnPct)) : null,
    averageMfePct: valid.length ? mean(valid.map(row => row[key].mfePct)) : null,
    averageMaePct: valid.length ? mean(valid.map(row => row[key].maePct)) : null,
  };
}
function group(rows, keyFn) {
  const groups = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return Object.fromEntries([...groups.entries()].map(([key, values]) => [key, {
    signalCount: values.length,
    outcome30m: summarize(values, 'outcome30m'),
    outcome60m: summarize(values, 'outcome60m'),
  }]));
}

const q4 = records.filter(row => row.qualityBand === 'Q4_HIGH');
const result = {
  phase: '57.p23.10e-cross-symbol-oos',
  status: 'CROSS_SYMBOL_OOS_CHART_QUALITY_REMEASUREMENT_COMPLETE',
  symbols: CHART_QUALITY_HOLDOUT_UNIVERSE,
  symbolCount: CHART_QUALITY_HOLDOUT_UNIVERSE.length,
  totalDirectionalSetups: records.length,
  aggregate: {
    outcome30m: summarize(records, 'outcome30m'),
    outcome60m: summarize(records, 'outcome60m'),
  },
  q4High: {
    signalCount: q4.length,
    coverageAmongDirectionalSetups: q4.length / records.length,
    outcome30m: summarize(q4, 'outcome30m'),
    outcome60m: summarize(q4, 'outcome60m'),
  },
  byQualityBand: group(records, row => row.qualityBand),
  bySetupQualityBand: group(records, row => `${row.setup}|${row.qualityBand}`),
  bySetup: group(records, row => row.setup),
  holdoutPolicy: CHART_QUALITY_HOLDOUT_POLICY,
  methodology: {
    crossSymbolOos: true,
    temporalFreshOos: false,
    disjointFromDevelopment30: true,
    setupRulesFrozenBeforeHoldoutOutcomes: true,
    qualityScoreFrozenBeforeHoldoutOutcomes: true,
    qualityBandsFrozenBeforeHoldoutOutcomes: true,
    outcomeBasedRetuningAllowed: false,
    futureOutcomesEvaluationOnly: true,
    sameSessionOutcomesOnly: true,
    finalUntouchedTemporalOos: false,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  transmitted: false,
  ...PHASE57_CHART_PERCEPTION_SAFETY,
};

for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) if (result[key] !== false) throw new Error(`${key} must remain false`);

fs.mkdirSync('artifacts', { recursive: true });
fs.writeFileSync('artifacts/phase57-p23-10e-cross-symbol-oos.json', JSON.stringify(result, null, 2));
console.log(JSON.stringify({
  status: result.status,
  symbolCount: result.symbolCount,
  totalDirectionalSetups: result.totalDirectionalSetups,
  aggregate: result.aggregate,
  q4High: result.q4High,
  bySetupQualityBand: result.bySetupQualityBand,
}, null, 2));
