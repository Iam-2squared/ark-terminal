import fs from 'node:fs';

const modelDir = process.argv[2] || 'data/phase49-robustness';
const outDir = process.argv[3] || 'data/phase49-diagnostics';
fs.mkdirSync(outDir, { recursive: true });

const files = fs.readdirSync(modelDir).filter((name) => name.endsWith('-model.json')).sort();
if (!files.length) throw new Error('PHASE49_DIAGNOSTIC_MODELS_MISSING');

const finite = (value) => Number.isFinite(Number(value)) ? Number(value) : null;
const median = (values) => {
  const xs = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!xs.length) return null;
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
};

const groups = [];
for (const file of files) {
  const model = JSON.parse(fs.readFileSync(`${modelDir}/${file}`, 'utf8'));
  const wf = model.walkForward;
  const ranked = wf?.ranked || [];
  const selected = ranked.find((x) => x.modelType === wf?.selectedModelType) || ranked[0];
  if (!selected) continue;

  const folds = (selected.folds || []).map((fold) => ({
    fold: fold.fold,
    testStart: fold.testStart,
    testEnd: fold.testEnd,
    selectedThreshold: finite(fold.selectedThreshold),
    auc: finite(fold.metrics?.auc),
    profitFactor: finite(fold.metrics?.profitFactor),
    sharpe: finite(fold.metrics?.sharpe),
    maxDrawdown: finite(fold.metrics?.maxDrawdown),
    netReturn: finite(fold.metrics?.netReturn),
    cagr: finite(fold.metrics?.cagr),
    tradeCount: finite(fold.metrics?.tradeCount),
  }));

  const positiveNet = folds.filter((f) => (f.netReturn ?? 0) > 0).length;
  const pfAbove1 = folds.filter((f) => (f.profitFactor ?? 0) > 1).length;
  const sharpePositive = folds.filter((f) => (f.sharpe ?? 0) > 0).length;
  const aucAbove053 = folds.filter((f) => (f.auc ?? 0) >= 0.53).length;
  const sortedByReturn = [...folds].sort((a, b) => (b.netReturn ?? -Infinity) - (a.netReturn ?? -Infinity));

  groups.push({
    name: file.replace(/-model\.json$/, ''),
    selectedModelType: wf?.selectedModelType ?? null,
    promotionStatus: wf?.selectedPromotionStatus ?? null,
    foldCount: folds.length,
    stability: {
      positiveNetFoldRate: folds.length ? positiveNet / folds.length : null,
      profitFactorAbove1FoldRate: folds.length ? pfAbove1 / folds.length : null,
      positiveSharpeFoldRate: folds.length ? sharpePositive / folds.length : null,
      aucAbove053FoldRate: folds.length ? aucAbove053 / folds.length : null,
      medianAuc: median(folds.map((f) => f.auc)),
      medianProfitFactor: median(folds.map((f) => f.profitFactor)),
      medianSharpe: median(folds.map((f) => f.sharpe)),
      medianMaxDrawdown: median(folds.map((f) => f.maxDrawdown)),
      medianNetReturn: median(folds.map((f) => f.netReturn)),
    },
    bestFoldsByNetReturn: sortedByReturn.slice(0, 3),
    worstFoldsByNetReturn: sortedByReturn.slice(-3).reverse(),
    folds,
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
  phase: 49.1,
  purpose: 'Temporal OOS fold stability diagnostics; no live trading actions',
  groups,
};
fs.writeFileSync(`${outDir}/summary.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output, null, 2));
