import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const input = process.argv[2] || 'data/training/phase48-alpha-regime-v2.json';
const outDir = process.argv[3] || 'data/robustness';
fs.mkdirSync(outDir, { recursive: true });
const parsed = JSON.parse(fs.readFileSync(input, 'utf8'));
const originalRows = parsed.rows || parsed.dataset || parsed;
if (!Array.isArray(originalRows)) throw new Error('ROBUSTNESS_INPUT_ROWS_MISSING');

const cases = [
  { name: 'baseline', remove: [], symbols: null },
  { name: 'noRegimeInteractions', remove: ['trendReturn5','trendReturn20','trendBreakoutUp20','trendBreakdownDown20','highVolBreakoutUp20','highVolVolumeRatio20','highVolMomentum20','trendVolatility20'], symbols: null },
  { name: 'regimeCoreOnly5', remove: ['trendReturn5','trendReturn20','trendBreakoutUp20','trendBreakdownDown20','highVolBreakoutUp20','highVolVolumeRatio20','highVolMomentum20','trendVolatility20','closePosition20','closePosition60','breakoutUp20','breakdownDown20'], symbols: null },
  { name: 'largeCap3', remove: ['trendReturn5','trendReturn20','trendBreakoutUp20','trendBreakdownDown20','highVolBreakoutUp20','highVolVolumeRatio20','highVolMomentum20','trendVolatility20'], symbols: ['7203.T','6758.T','8306.T'] },
  { name: 'tech2', remove: ['trendReturn5','trendReturn20','trendBreakoutUp20','trendBreakdownDown20','highVolBreakoutUp20','highVolVolumeRatio20','highVolMomentum20','trendVolatility20'], symbols: ['9984.T','8035.T'] },
];

const lineage = parsed.lineage || parsed.datasetLineage || null;
const summaries = [];
for (const testCase of cases) {
  let rows = originalRows;
  if (testCase.symbols) rows = rows.filter((row) => testCase.symbols.includes(row.symbol));
  rows = rows.map((row) => {
    const copy = structuredClone(row);
    if (copy.features && typeof copy.features === 'object') {
      for (const key of testCase.remove) delete copy.features[key];
    }
    for (const key of testCase.remove) delete copy[key];
    return copy;
  });
  const dataset = Array.isArray(parsed) ? rows : { ...parsed, rows, lineage: lineage ? { ...lineage, datasetVersion: `phase48-robustness-${testCase.name}` } : lineage };
  const datasetPath = `${outDir}/${testCase.name}.json`;
  const modelPath = `${outDir}/${testCase.name}-model.json`;
  fs.writeFileSync(datasetPath, JSON.stringify(dataset));
  const run = spawnSync(process.execPath, [
    'tools/run_phase47_training_pipeline.mjs', '--input', datasetPath, '--output', modelPath,
    '--cost-rate', '0.001', '--min-train', '252', '--validation-size', '63', '--step', '63'
  ], { encoding: 'utf8' });
  if (run.status !== 0) {
    console.error(run.stdout); console.error(run.stderr);
    throw new Error(`ROBUSTNESS_TRAINING_FAILED:${testCase.name}`);
  }
  const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
  const wf = model.walkForward;
  const selected = wf?.ranked?.find((x) => x.modelType === wf.selectedModelType) || wf?.ranked?.[0];
  summaries.push({
    name: testCase.name,
    symbols: testCase.symbols,
    removed: testCase.remove,
    rows: rows.length,
    selectedModelType: wf?.selectedModelType ?? null,
    promotionStatus: wf?.selectedPromotionStatus ?? null,
    auc: selected?.aggregate?.auc ?? null,
    profitFactor: selected?.aggregate?.oos?.profitFactor ?? null,
    sharpe: selected?.aggregate?.oos?.sharpe ?? null,
    maxDrawdown: selected?.aggregate?.oos?.maxDrawdown ?? null,
    netReturn: selected?.aggregate?.oos?.netReturn ?? null,
    cagr: selected?.aggregate?.oos?.cagr ?? null,
    benchmarkNetReturn: selected?.aggregate?.benchmark?.netReturn ?? null,
    safety: {
      brokerWrites: model.audit?.brokerWrites ?? 0,
      excelOrderWrites: model.audit?.excelOrderWrites ?? 0,
      rssOrderCalls: model.audit?.rssOrderCalls ?? 0,
      liveOrders: model.audit?.liveOrders ?? 0,
      automaticPromotionAllowed: wf?.automaticPromotionAllowed ?? false,
      productionUpdateAllowed: wf?.productionUpdateAllowed ?? false,
    },
  });
}
const output = { phase: 48.4, summaries };
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
