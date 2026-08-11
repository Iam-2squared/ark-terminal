import fs from 'node:fs';
import path from 'node:path';
import {
  P23_14_BLIND_REASONER_POLICY,
  PHASE57_P23_14_SAFETY,
  buildBlindReasoningPrediction,
} from './phase57-p23-14-blind-reasoner-benchmark.js';

const inputDir = process.argv[2] ?? 'artifacts/p23-14-input';
const files = fs.readdirSync(inputDir).filter(name => name.endsWith('.json')).sort();
if (!files.length) throw new Error('no P23.14 source shards found');

const mean = values => values.length ? values.reduce((a,b) => a + Number(b), 0) / values.length : null;
function pf(returns) {
  const gains = returns.filter(x => x > 0).reduce((a,b) => a + b, 0);
  const losses = -returns.filter(x => x < 0).reduce((a,b) => a + b, 0);
  return losses > 0 ? gains / losses : gains > 0 ? Infinity : null;
}
function summarize(rows) {
  const valid = rows.filter(row => Number.isFinite(Number(row.directionalReturnPct)));
  const returns = valid.map(row => Number(row.directionalReturnPct));
  return {
    count: valid.length,
    hitRate: valid.length ? valid.filter(row => row.hit).length / valid.length : null,
    averageDirectionalReturnPct: mean(returns),
    averageNetAfterCostPct: mean(returns.map(x => x - 0.05)),
    profitFactor: pf(returns.map(x => x - 0.05)),
    averageMfePct: mean(valid.map(row => Number(row.mfePct)).filter(Number.isFinite)),
    averageMaePct: mean(valid.map(row => Number(row.maePct)).filter(Number.isFinite)),
    averageConfidence: mean(valid.map(row => Number(row.confidenceScore)).filter(Number.isFinite)),
  };
}
function group(rows, keyFn) {
  const m = new Map();
  for (const row of rows) {
    const key = keyFn(row);
    if (!m.has(key)) m.set(key, []);
    m.get(key).push(row);
  }
  return Object.fromEntries([...m].map(([k,v]) => [k, summarize(v)]));
}

const sourceRecords = [];
const symbols = new Set();
for (const file of files) {
  const payload = JSON.parse(fs.readFileSync(path.join(inputDir, file), 'utf8'));
  if (payload.status !== 'VISUAL_CHART_REASONING_DEVELOPMENT_MEASURED') throw new Error(`unexpected source status in ${file}`);
  for (const symbol of payload.symbols ?? []) symbols.add(symbol);
  for (const row of payload.records ?? []) sourceRecords.push(row);
}
if (!sourceRecords.length) throw new Error('no P23.14 source records');

const frozenPredictions = sourceRecords.map(row => buildBlindReasoningPrediction(row));
for (const p of frozenPredictions) {
  if (p.futureOutcomeVisible !== false || p.outcomeUsedForPrediction !== false || p.thresholdSearchPerformed !== false) throw new Error('blind freeze violation');
}

const outcomeMap = new Map(sourceRecords.map(row => [`${row.symbol}|${row.featureCutoff}|${row.setup}`, row.outcome60m ?? null]));
const evaluated = frozenPredictions.map(prediction => {
  const outcome = outcomeMap.get(prediction.key);
  return {
    ...prediction,
    hit: outcome?.hit ?? null,
    directionalReturnPct: outcome?.directionalReturnPct ?? null,
    mfePct: outcome?.mfePct ?? null,
    maePct: outcome?.maePct ?? null,
    outcomeJoinedAfterPredictionFreeze: true,
  };
}).filter(row => Number.isFinite(Number(row.directionalReturnPct)));

const result = {
  phase: '57.p23.14-blind-reasoner-benchmark',
  status: 'BLIND_REASONER_BENCHMARK_MEASURED',
  symbolCount: symbols.size,
  sourceShardCount: files.length,
  sourceRecordCount: sourceRecords.length,
  evaluatedCount: evaluated.length,
  policy: P23_14_BLIND_REASONER_POLICY,
  aggregate: summarize(evaluated),
  byConfidenceBand: group(evaluated, row => row.confidenceBand),
  bySetup: group(evaluated, row => row.setup),
  byDirection: group(evaluated, row => row.direction),
  byHigherTimeframeContext: group(evaluated, row => row.higherTimeframeContext),
  methodology: {
    developmentUniverseOnly: true,
    freshHoldoutConsumed: false,
    untouchedTemporalOos: false,
    causalVisualFieldsOnlyAtPredictionTime: true,
    outcomeFieldsStrippedBeforeReasoning: true,
    predictionFrozenBeforeOutcomeJoin: true,
    outcomeJoinedAfterPredictionFreeze: true,
    thresholdSearchPerformed: false,
    predictionUsedAsEntryGate: false,
    externalVisionModelCalled: false,
    deterministicManifestReasonerOnly: true,
    sameSession60mOutcomeEvaluation: true,
    transactionCostPct: 0.05,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  transmitted: false,
  ...PHASE57_P23_14_SAFETY,
};
for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  if (result[key] !== false) throw new Error(`${key} must remain false`);
}
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-14-blind-reasoner-benchmark.json', JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
