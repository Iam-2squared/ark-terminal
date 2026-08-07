import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const input = process.argv[2] || 'data/training/phase48-alpha-regime-v2.json';
const outDir = process.argv[3] || 'data/stable-feature-selection';
fs.mkdirSync(outDir, { recursive: true });

const parsed = JSON.parse(fs.readFileSync(input, 'utf8'));
const originalRows = parsed.rows || parsed.dataset || parsed;
if (!Array.isArray(originalRows)) throw new Error('STABLE_SELECTION_INPUT_ROWS_MISSING');

const interactionFeatures = [
  'trendReturn5Interaction','trendReturn20Interaction','trendBreakoutInteraction','trendBreakdownInteraction',
  'highVolBreakoutInteraction','highVolVolumeInteraction','highVolMomentumInteraction','trendVolatilityInteraction'
];
const chartFeatures = ['closePosition20','closePosition60','breakoutUp20','breakdownDown20'];
const regimeCore = ['regimeTrend','regimeVolatility','regimeCode'];

const candidates = [
  { name: 'baseline', remove: [] },
  { name: 'dropInteractions', remove: interactionFeatures },
  { name: 'dropInteractionsAndChart', remove: [...interactionFeatures, ...chartFeatures] },
  { name: 'regimeCorePlusBase', remove: [...interactionFeatures, ...chartFeatures] },
  { name: 'baseWithoutRegime', remove: [...interactionFeatures, ...chartFeatures, ...regimeCore] },
];

const results = [];
for (const candidate of candidates) {
  const rows = originalRows.map((row) => {
    const copy = structuredClone(row);
    if (copy.features && typeof copy.features === 'object') {
      for (const key of candidate.remove) delete copy.features[key];
    }
    for (const key of candidate.remove) delete copy[key];
    return copy;
  });
  const dataset = Array.isArray(parsed) ? rows : { ...parsed, rows };
  const datasetPath = `${outDir}/${candidate.name}.json`;
  const modelPath = `${outDir}/${candidate.name}-model.json`;
  fs.writeFileSync(datasetPath, JSON.stringify(dataset));
  const run = spawnSync(process.execPath, [
    'tools/run_phase47_training_pipeline.mjs', '--input', datasetPath, '--output', modelPath,
    '--cost-rate', '0.001', '--min-train', '252', '--validation-size', '63', '--step', '63'
  ], { encoding: 'utf8' });
  if (run.status !== 0) {
    console.error(run.stdout); console.error(run.stderr);
    throw new Error(`STABLE_SELECTION_TRAINING_FAILED:${candidate.name}`);
  }
  const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
  const wf = model.walkForward;
  const selected = wf?.ranked?.find((x) => x.modelType === wf.selectedModelType) || wf?.ranked?.[0];
  const aggregate = selected?.aggregate || {};
  const oos = aggregate.oos || {};
  const benchmark = aggregate.benchmark || {};
  const score = [
    Number.isFinite(aggregate.auc) ? aggregate.auc : -Infinity,
    Number.isFinite(oos.profitFactor) ? oos.profitFactor : -Infinity,
    Number.isFinite(oos.sharpe) ? oos.sharpe : -Infinity,
    Number.isFinite(oos.maxDrawdown) ? -oos.maxDrawdown : -Infinity,
  ];
  results.push({
    name: candidate.name,
    removed: candidate.remove,
    selectedModelType: wf?.selectedModelType ?? null,
    promotionStatus: wf?.selectedPromotionStatus ?? null,
    auc: aggregate.auc ?? null,
    profitFactor: oos.profitFactor ?? null,
    sharpe: oos.sharpe ?? null,
    maxDrawdown: oos.maxDrawdown ?? null,
    netReturn: oos.netReturn ?? null,
    cagr: oos.cagr ?? null,
    benchmarkNetReturn: benchmark.netReturn ?? null,
    safety: {
      brokerWrites: model.audit?.brokerWrites ?? 0,
      excelOrderWrites: model.audit?.excelOrderWrites ?? 0,
      rssOrderCalls: model.audit?.rssOrderCalls ?? 0,
      liveOrders: model.audit?.liveOrders ?? 0,
      automaticPromotionAllowed: wf?.automaticPromotionAllowed ?? false,
      productionUpdateAllowed: wf?.productionUpdateAllowed ?? false,
    },
    score,
  });
}

results.sort((a, b) => {
  for (let i = 0; i < a.score.length; i += 1) {
    if (b.score[i] !== a.score[i]) return b.score[i] - a.score[i];
  }
  return a.name.localeCompare(b.name);
});

const output = {
  phase: 48.5,
  policy: 'OOS metrics only; no promotion, no production update, no broker writes',
  selectedCandidate: results[0]?.name ?? null,
  candidates: results,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
