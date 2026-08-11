import fs from 'node:fs';
import path from 'node:path';

const root = process.env.PHASE57_FULL30_ARTIFACT_DIR || 'full30-shards';

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : (entry.name.endsWith('.json') ? [full] : []);
  });
}

const files = walk(root);
if (files.length !== 3) throw new Error(`expected exactly 3 shard JSON files, found ${files.length}`);
const shards = files.map(file => JSON.parse(fs.readFileSync(file, 'utf8')));
for (const shard of shards) {
  if (shard.status !== 'REAL_HISTORICAL_CHART_PERCEPTION_REMEASUREMENT_COMPLETE') throw new Error('incomplete shard');
  if (shard.interpretation?.p23_8FrozenOutcomeReuse !== false) throw new Error('frozen P23.8 outcome reuse forbidden');
  for (const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
  ]) if (shard[key] !== false) throw new Error(`${key} must remain false`);
}

const symbols = [...new Set(shards.flatMap(shard => shard.symbols ?? []))].sort();
if (symbols.length !== 30) throw new Error(`expected 30 unique symbols, got ${symbols.length}`);

function weightedSummary(entries, key) {
  const rows = entries.map(entry => entry[key]).filter(item => item && Number(item.count) > 0);
  const count = rows.reduce((sum, row) => sum + Number(row.count), 0);
  if (!count) return { count: 0, hitRate: null, averageDirectionalReturnPct: null, averageMfePct: null, averageMaePct: null };
  const weighted = field => rows.reduce((sum, row) => sum + Number(row[field]) * Number(row.count), 0) / count;
  return {
    count,
    hitRate: weighted('hitRate'),
    averageDirectionalReturnPct: weighted('averageDirectionalReturnPct'),
    averageMfePct: weighted('averageMfePct'),
    averageMaePct: weighted('averageMaePct'),
  };
}

const setupNames = [...new Set(shards.flatMap(shard => Object.keys(shard.bySetup ?? {})))].sort();
const bySetup = Object.fromEntries(setupNames.map(setup => {
  const entries = shards.map(shard => shard.bySetup?.[setup]).filter(Boolean);
  return [setup, {
    signalCount: entries.reduce((sum, item) => sum + Number(item.signalCount || 0), 0),
    outcome30m: weightedSummary(entries, 'outcome30m'),
    outcome60m: weightedSummary(entries, 'outcome60m'),
  }];
}));

const totalDirectionalSetups = shards.reduce((sum, shard) => sum + Number(shard.totalDirectionalSetups || 0), 0);
const aggregate = {
  outcome30m: weightedSummary(shards.map(shard => shard.aggregate), 'outcome30m'),
  outcome60m: weightedSummary(shards.map(shard => shard.aggregate), 'outcome60m'),
};

const result = {
  phase: '57.p23.10c-full30-chart-perception-remeasurement',
  status: 'FULL30_CHART_PERCEPTION_REMEASUREMENT_COMPLETE',
  symbolCount: symbols.length,
  symbols,
  shardCount: shards.length,
  totalDirectionalSetups,
  aggregate,
  bySetup,
  bySymbol: Object.assign({}, ...shards.map(shard => shard.bySymbol ?? {})),
  methodology: {
    sameFrozenExpandedUniverse30: true,
    independentPerSymbolPerception: true,
    setupRulesFrozenBeforeFull30Measurement: true,
    setupThresholdsOptimizedOnFull30Outcomes: false,
    p23_8FrozenOutcomesUsedForSelection: false,
    futureOutcomesEvaluationOnly: true,
    sessionAwareHigherTimeframes: true,
    sameSessionOutcomesOnly: true,
    finalUntouchedOos: false,
    developmentMeasurementOnly: true,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
};

if (totalDirectionalSetups < 100) throw new Error(`insufficient full30 setup cardinality: ${totalDirectionalSetups}`);
fs.mkdirSync('artifacts', { recursive: true });
fs.writeFileSync('artifacts/phase57-p23-10c-full30-chart-perception.json', JSON.stringify(result, null, 2));
console.log(JSON.stringify({ status: result.status, symbolCount: result.symbolCount, totalDirectionalSetups, aggregate, bySetup }, null, 2));
