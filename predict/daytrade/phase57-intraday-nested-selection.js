import { buildIntradayWalkForwardFolds } from './phase57-intraday-walkforward-cost.js';
import { fitIntradayLogisticPredictor } from './phase57-intraday-selective-model.js';
import { evaluateCostAwareStrategy } from '../strategy/cost-aware-evaluation.js';

export const PHASE57_P7_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_NESTED_SELECTION_RESEARCH_ONLY',
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

const clamp01 = v => Math.max(0.001, Math.min(0.999, Number(v)));

function scoreSignals(rows, predictor, threshold, costs) {
  const signals = [];
  for (const row of rows) {
    const p = clamp01(predictor(row));
    const confidence = Math.max(p, 1 - p);
    if (confidence < threshold) continue;
    const prediction = p >= 0.5 ? 1 : 0;
    const correct = prediction === Number(row.label);
    const grossReturn = correct ? Number(row.barrierBps ?? 20) / 100 : -Number(row.barrierBps ?? 20) / 100;
    signals.push({ probability: p, confidence, prediction, label: Number(row.label), correct, grossReturn, ...costs });
  }
  const costAware = evaluateCostAwareStrategy(signals, costs);
  return {
    signalCount: signals.length,
    hitRate: signals.length ? signals.filter(s => s.correct).length / signals.length : null,
    netAverageReturn: costAware.netAverageReturn,
    profitFactor: costAware.profitFactor,
  };
}

function rankCandidate(a, b) {
  const aNet = Number.isFinite(a.netAverageReturn) ? a.netAverageReturn : -Infinity;
  const bNet = Number.isFinite(b.netAverageReturn) ? b.netAverageReturn : -Infinity;
  if (bNet !== aNet) return bNet - aNet;
  const aHit = Number.isFinite(a.hitRate) ? a.hitRate : -Infinity;
  const bHit = Number.isFinite(b.hitRate) ? b.hitRate : -Infinity;
  if (bHit !== aHit) return bHit - aHit;
  if (b.signalCount !== a.signalCount) return b.signalCount - a.signalCount;
  return a.threshold - b.threshold;
}

export function selectInnerThreshold(trainRows = [], options = {}) {
  const thresholds = Array.isArray(options.thresholds) && options.thresholds.length ? options.thresholds : [0.55, 0.60, 0.65, 0.70];
  const innerFolds = buildIntradayWalkForwardFolds(trainRows, {
    trainFraction: options.innerTrainFraction ?? 0.6,
    testFraction: options.innerTestFraction ?? 0.15,
    minTrainRows: options.innerMinTrainRows ?? Math.max(10, Math.floor((options.minTrainRows ?? 20) / 2)),
  });
  const costs = {
    feePercent: options.feePercent ?? 0,
    slippagePercent: options.slippagePercent ?? 0.05,
    delayCostPercent: options.delayCostPercent ?? 0,
  };
  const candidates = thresholds.map(threshold => {
    let signals = 0, correct = 0, netWeighted = 0;
    for (const fold of innerFolds) {
      const predictor = fitIntradayLogisticPredictor(fold.train, options.model);
      const scored = scoreSignals(fold.test, predictor, threshold, costs);
      signals += scored.signalCount;
      correct += scored.hitRate === null ? 0 : scored.hitRate * scored.signalCount;
      netWeighted += scored.netAverageReturn === null ? 0 : scored.netAverageReturn * scored.signalCount;
    }
    return Object.freeze({
      threshold,
      innerFoldCount: innerFolds.length,
      signalCount: signals,
      hitRate: signals ? correct / signals : null,
      netAverageReturn: signals ? netWeighted / signals : null,
    });
  });
  const eligible = candidates.filter(c => c.signalCount >= (options.minInnerSignals ?? 1));
  const ranked = (eligible.length ? eligible : candidates).slice().sort(rankCandidate);
  return Object.freeze({ selectedThreshold: ranked[0]?.threshold ?? thresholds[0], candidates: Object.freeze(candidates), innerFoldCount: innerFolds.length });
}

export function evaluateNestedIntradaySelection(rows = [], options = {}) {
  const outerFolds = buildIntradayWalkForwardFolds(rows, {
    trainFraction: options.trainFraction ?? 0.6,
    testFraction: options.testFraction ?? 0.1,
    minTrainRows: options.minTrainRows ?? 20,
  });
  const costs = {
    feePercent: options.feePercent ?? 0,
    slippagePercent: options.slippagePercent ?? 0.05,
    delayCostPercent: options.delayCostPercent ?? 0,
  };
  const outerResults = [];
  for (const fold of outerFolds) {
    const selection = selectInnerThreshold(fold.train, options);
    const predictor = fitIntradayLogisticPredictor(fold.train, options.model);
    const scored = scoreSignals(fold.test, predictor, selection.selectedThreshold, costs);
    outerResults.push(Object.freeze({
      fold: fold.fold,
      trainRows: fold.train.length,
      testRows: fold.test.length,
      trainCutoff: fold.trainCutoff,
      testStart: fold.testStart,
      testEnd: fold.testEnd,
      selectedThreshold: selection.selectedThreshold,
      innerFoldCount: selection.innerFoldCount,
      innerCandidates: selection.candidates,
      ...scored,
    }));
  }
  const totalSignals = outerResults.reduce((s,r) => s + r.signalCount, 0);
  const weightedHits = outerResults.reduce((s,r) => s + (r.hitRate ?? 0) * r.signalCount, 0);
  const weightedNet = outerResults.reduce((s,r) => s + (r.netAverageReturn ?? 0) * r.signalCount, 0);
  return Object.freeze({
    phase: '57.p7',
    status: outerResults.length ? 'INTRADAY_NESTED_OOS_READY' : 'NO_NESTED_OOS_FOLDS',
    outerFoldCount: outerResults.length,
    outerResults: Object.freeze(outerResults),
    signalCount: totalSignals,
    hitRate: totalSignals ? weightedHits / totalSignals : null,
    netAverageReturn: totalSignals ? weightedNet / totalSignals : null,
    selectionIntegrity: Object.freeze({
      thresholdSelectedOnInnerOnly: true,
      outerTestNeverUsedForSelection: true,
      outerTestNeverUsedForFit: true,
      trainingRowsRequireResolvedOutcomeBeforeCutoff: true,
    }),
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
    safety: PHASE57_P7_SAFETY,
  });
}

export default { selectInnerThreshold, evaluateNestedIntradaySelection };
