import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const input = process.argv[2] || 'data/training/phase49-expanded.json';
const outDir = process.argv[3] || 'data/phase49-robustness';
fs.mkdirSync(outDir, { recursive: true });

const parsed = JSON.parse(fs.readFileSync(input, 'utf8'));
const originalRows = parsed.rows || parsed.dataset || parsed;
if (!Array.isArray(originalRows)) throw new Error('PHASE49_INPUT_ROWS_MISSING');

const availableSymbols = [...new Set(originalRows.map((row) => row.symbol).filter(Boolean))].sort();
const groups = [
  { name: 'all', symbols: null },
  { name: 'core5', symbols: ['7203.T','6758.T','9984.T','8306.T','8035.T'] },
  { name: 'banks', symbols: ['8306.T','8316.T','8411.T'] },
  { name: 'autos', symbols: ['7203.T','7267.T','7201.T'] },
  { name: 'electronics', symbols: ['6758.T','8035.T','6501.T','6954.T'] },
  { name: 'trading', symbols: ['8058.T','8001.T','8031.T'] },
];

const summaries = [];
for (const group of groups) {
  const selectedSymbols = group.symbols ? group.symbols.filter((s) => availableSymbols.includes(s)) : availableSymbols;
  if (selectedSymbols.length < 2) continue;
  const rows = originalRows.filter((row) => selectedSymbols.includes(row.symbol));
  const dataset = Array.isArray(parsed)
    ? rows
    : {
        ...parsed,
        rows,
        lineage: parsed.lineage
          ? { ...parsed.lineage, datasetVersion: `phase49-${group.name}` }
          : parsed.lineage,
      };

  const datasetPath = `${outDir}/${group.name}.json`;
  const modelPath = `${outDir}/${group.name}-model.json`;
  fs.writeFileSync(datasetPath, JSON.stringify(dataset));

  const run = spawnSync(process.execPath, [
    'tools/run_phase47_training_pipeline.mjs',
    '--input', datasetPath,
    '--output', modelPath,
    '--cost-rate', '0.001',
    '--min-train', '252',
    '--validation-size', '63',
    '--step', '63',
  ], { encoding: 'utf8' });

  if (run.status !== 0) {
    console.error(run.stdout);
    console.error(run.stderr);
    throw new Error(`PHASE49_TRAINING_FAILED:${group.name}`);
  }

  const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
  const wf = model.walkForward;
  const selected = wf?.ranked?.find((x) => x.modelType === wf.selectedModelType) || wf?.ranked?.[0];

  summaries.push({
    name: group.name,
    symbols: selectedSymbols,
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

const output = {
  phase: 49,
  sourceRows: originalRows.length,
  availableSymbols,
  summaries,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
