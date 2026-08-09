import { evaluateIntradayWalkForward } from './phase57-intraday-walkforward-cost.js';

export const PHASE57_P6_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_SELECTIVE_MODEL_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const clamp01 = v => Math.max(0.001, Math.min(0.999, Number(v)));

function vector(row) {
  const f = row?.features ?? {};
  const i = row?.interactions ?? {};
  return [
    1,
    Number(f.returnFromOpen ?? 0), Number(f.rangePosition ?? 0), Number(f.shortMomentum ?? 0),
    Number(f.relativeVolume ?? 0), Number(f.spreadBps ?? 0), Number(f.bookImbalance ?? 0),
    Number(f.depthImbalance ?? 0), Number(f.aggressiveBuyRatio ?? 0.5), Number(f.tradeIntensity ?? 0),
    Number(i.vwapFlow ?? 0), Number(i.rangeBookPressure ?? 0),
  ].map(v => finite(v) ? Number(v) : 0);
}

const dot = (a,b) => a.reduce((s,v,j) => s + v * (b[j] ?? 0), 0);
const sigmoid = z => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

export function fitIntradayLogisticPredictor(rows = [], { learningRate = 0.02, epochs = 160, l2 = 0.001 } = {}) {
  const data = rows.filter(r => finite(r?.label)).map(r => ({ x: vector(r), y: Number(r.label) }));
  const width = data[0]?.x.length ?? 12;
  const w = Array(width).fill(0);
  if (!data.length) return () => 0.5;
  for (let epoch = 0; epoch < epochs; epoch += 1) {
    const grad = Array(width).fill(0);
    for (const { x, y } of data) {
      const p = sigmoid(dot(w, x));
      for (let j = 0; j < width; j += 1) grad[j] += (p - y) * x[j];
    }
    for (let j = 0; j < width; j += 1) {
      const penalty = j === 0 ? 0 : l2 * w[j];
      w[j] -= learningRate * (grad[j] / data.length + penalty);
    }
  }
  return row => clamp01(sigmoid(dot(w, vector(row))));
}

export function evaluateIntradaySelectiveModel(rows = [], options = {}) {
  const thresholds = Array.isArray(options.thresholds) && options.thresholds.length ? options.thresholds : [0.55, 0.60, 0.65, 0.70];
  const evaluations = thresholds.map(threshold => evaluateIntradayWalkForward(rows, {
    ...options,
    threshold,
    fitPredictor: train => fitIntradayLogisticPredictor(train, options.model),
  }));
  const ranked = evaluations.slice().sort((a,b) => {
    const ah = a.hitRate ?? -1, bh = b.hitRate ?? -1;
    if (bh !== ah) return bh - ah;
    if (b.signalCount !== a.signalCount) return b.signalCount - a.signalCount;
    return (b.costAware?.profitFactor ?? -1) - (a.costAware?.profitFactor ?? -1);
  });
  return Object.freeze({
    phase: '57.p6',
    status: 'INTRADAY_SELECTIVE_MODEL_RESEARCH_READY',
    evaluations: Object.freeze(evaluations),
    descriptiveBest: ranked[0] ?? null,
    selectionWarning: 'Threshold comparison is descriptive research only; do not promote a threshold from outer results. Nested inner selection is required before any candidate decision.',
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_P6_SAFETY,
  });
}

export default { fitIntradayLogisticPredictor, evaluateIntradaySelectiveModel };
