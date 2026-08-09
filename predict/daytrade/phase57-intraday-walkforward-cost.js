import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P5_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_OOS_COST_RESEARCH_ONLY',
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
const clamp01 = v => Math.max(0, Math.min(1, Number(v)));

function sortRows(rows = []) {
  return (Array.isArray(rows) ? rows : [])
    .filter(r => r?.pointInTimeValid !== false && r?.featureCutoff && r?.outcomeAt && finite(r?.label))
    .filter(r => Date.parse(r.featureCutoff) < Date.parse(r.outcomeAt))
    .slice()
    .sort((a,b) => a.featureCutoff.localeCompare(b.featureCutoff));
}

export function buildIntradayWalkForwardFolds(rows = [], { trainFraction = 0.6, testFraction = 0.1, minTrainRows = 20 } = {}) {
  const ordered = sortRows(rows);
  if (!ordered.length) return Object.freeze([]);
  const initialTrain = Math.max(minTrainRows, Math.floor(ordered.length * trainFraction));
  const testSize = Math.max(1, Math.floor(ordered.length * testFraction));
  const folds = [];
  for (let testStart = initialTrain, fold = 0; testStart < ordered.length; testStart += testSize, fold += 1) {
    const testEnd = Math.min(ordered.length, testStart + testSize);
    const trainCutoff = ordered[testStart - 1]?.featureCutoff ?? null;
    const train = ordered.slice(0, testStart).filter(r => Date.parse(r.outcomeAt) <= Date.parse(trainCutoff));
    const test = ordered.slice(testStart, testEnd);
    if (train.length < minTrainRows || !test.length) continue;
    folds.push(Object.freeze({ fold, train: Object.freeze(train), test: Object.freeze(test), trainCutoff, testStart: test[0].featureCutoff, testEnd: test.at(-1).featureCutoff }));
  }
  return Object.freeze(folds);
}

function brier(signals) {
  if (!signals.length) return null;
  return signals.reduce((s,x) => s + (x.probability - x.label) ** 2, 0) / signals.length;
}

function maxDrawdown(returns) {
  let equity = 1, peak = 1, max = 0;
  for (const r of returns) {
    equity *= 1 + r / 100;
    peak = Math.max(peak, equity);
    max = Math.max(max, peak > 0 ? (peak - equity) / peak : 0);
  }
  return max;
}

export function evaluateIntradayWalkForward(rows = [], {
  fitPredictor,
  threshold = 0.55,
  feePercent = 0.0,
  slippagePercent = 0.05,
  delayCostPercent = 0.0,
  trainFraction = 0.6,
  testFraction = 0.1,
  minTrainRows = 20,
} = {}) {
  if (typeof fitPredictor !== 'function') throw new TypeError('fitPredictor must be a function');
  const folds = buildIntradayWalkForwardFolds(rows, { trainFraction, testFraction, minTrainRows });
  const signals = [];
  const foldSummaries = [];
  for (const fold of folds) {
    const predictor = fitPredictor(fold.train);
    if (typeof predictor !== 'function') throw new TypeError('fitPredictor must return a predictor function');
    const foldSignals = [];
    for (const row of fold.test) {
      const p = clamp01(predictor(row));
      const confidence = Math.max(p, 1 - p);
      if (confidence < threshold) continue;
      const prediction = p >= 0.5 ? 1 : 0;
      const correct = prediction === Number(row.label);
      const grossReturn = correct ? Number(row.barrierBps ?? 20) / 100 : -Number(row.barrierBps ?? 20) / 100;
      const signal = Object.freeze({ fold: fold.fold, symbol: row.symbol, featureCutoff: row.featureCutoff, outcomeAt: row.outcomeAt, label: Number(row.label), probability: p, confidence, prediction, correct, grossReturn, feePercent, slippagePercent, delayCostPercent });
      signals.push(signal); foldSignals.push(signal);
    }
    foldSummaries.push(Object.freeze({ fold: fold.fold, trainRows: fold.train.length, testRows: fold.test.length, signals: foldSignals.length, trainCutoff: fold.trainCutoff, testStart: fold.testStart, testEnd: fold.testEnd }));
  }
  const cost = evaluateCostAwareStrategy(signals, { feePercent, slippagePercent, delayCostPercent });
  const netReturns = cost.trades.map(t => t.netReturn);
  return Object.freeze({
    phase: '57.p5',
    status: signals.length ? 'INTRADAY_WALK_FORWARD_OOS_READY' : 'NO_OOS_SIGNALS',
    folds: Object.freeze(foldSummaries),
    signalCount: signals.length,
    hitRate: signals.length ? signals.filter(s => s.correct).length / signals.length : null,
    coverage: sortRows(rows).length ? signals.length / sortRows(rows).length : 0,
    brierScore: brier(signals),
    costAware: Object.freeze({ sampleCount: cost.sampleCount, grossAverageReturn: cost.grossAverageReturn, netAverageReturn: cost.netAverageReturn, profitFactor: cost.profitFactor, winRate: cost.winRate, maxDrawdown: maxDrawdown(netReturns), feePercent, slippagePercent, delayCostPercent }),
    pointInTime: Object.freeze({ trainingRequiresOutcomeAtOnOrBeforeFoldCutoff: true, testRowsNeverUsedForFit: true }),
    outerOnly: true,
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
    safety: PHASE57_P5_SAFETY,
  });
}

export default { buildIntradayWalkForwardFolds, evaluateIntradayWalkForward };
