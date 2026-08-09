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

const clamp01 = v => Math.max(0, Math.min(1, Number(v)));
const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));

function scoreRows(rows, predictor, threshold) {
  const out = [];
  for (const row of rows) {
    const p = clamp01(predictor(row));
    const confidence = Math.max(p, 1 - p);
    if (confidence < threshold) continue;
    const prediction = p >= 0.5 ? 1 : 0;
    const correct = prediction === Number(row.label);
    const grossReturn = correct ? Number(row.barrierBps ?? 20) / 100 : -Number(row.barrierBps ?? 20) / 100;
    out.push({ row, probability: p, confidence, prediction, correct, grossReturn });
  }
  return out;
}

function validationMetric(signals) {
  if (!signals.length) return -Infinity;
  const hitRate = signals.filter(s => s.correct).length / signals.length;
  const coveragePenalty = Math.min(1, signals.length / 20);
  return hitRate * 0.8 + coveragePenalty * 0.2;
}

export function selectInnerIntradayConfig(outerTrain = [], {
  validationFraction = 0.25,
  thresholds = [0.55, 0.60, 0.65],
  modelCandidates = [
    { learningRate: 0.02, epochs: 160, l2: 0.001 },
    { learningRate: 0.01, epochs: 220, l2: 0.005 },
  ],
  minInnerTrainRows = 20,
} = {}) {
  const ordered = outerTrain.slice().sort((a,b) => a.featureCutoff.localeCompare(b.featureCutoff));
  const split = Math.max(minInnerTrainRows, Math.floor(ordered.length * (1 - validationFraction)));
  const innerTrain = ordered.slice(0, split);
  const validationCutoff = innerTrain.at(-1)?.featureCutoff ?? null;
  const innerValidation = ordered.slice(split).filter(r => !validationCutoff || Date.parse(r.outcomeAt) > Date.parse(validationCutoff));
  if (innerTrain.length < minInnerTrainRows || !innerValidation.length) return null;

  let best = null;
  for (const model of modelCandidates) {
    const predictor = fitIntradayLogisticPredictor(innerTrain, model);
    for (const threshold of thresholds) {
      const signals = scoreRows(innerValidation, predictor, threshold);
      const metric = validationMetric(signals);
      const candidate = { model: { ...model }, threshold, validationSignals: signals.length, validationHitRate: signals.length ? signals.filter(s => s.correct).length / signals.length : null, metric };
      if (!best || candidate.metric > best.metric || (candidate.metric === best.metric && candidate.validationSignals > best.validationSignals)) best = candidate;
    }
  }
  return best ? Object.freeze({ ...best, selectionSource: 'INNER_VALIDATION_ONLY' }) : null;
}

export function evaluateNestedIntradaySelection(rows = [], options = {}) {
  const folds = buildIntradayWalkForwardFolds(rows, options);
  const outerSignals = [];
  const foldSummaries = [];
  for (const fold of folds) {
    const selected = selectInnerIntradayConfig(fold.train, options);
    if (!selected) continue;
    const predictor = fitIntradayLogisticPredictor(fold.train, selected.model);
    const foldSignals = scoreRows(fold.test, predictor, selected.threshold).map(s => ({
      fold: fold.fold,
      symbol: s.row.symbol,
      featureCutoff: s.row.featureCutoff,
      outcomeAt: s.row.outcomeAt,
      label: Number(s.row.label),
      probability: s.probability,
      confidence: s.confidence,
      prediction: s.prediction,
      correct: s.correct,
      grossReturn: s.grossReturn,
      feePercent: options.feePercent ?? 0,
      slippagePercent: options.slippagePercent ?? 0.05,
      delayCostPercent: options.delayCostPercent ?? 0,
    }));
    outerSignals.push(...foldSignals);
    foldSummaries.push(Object.freeze({ fold: fold.fold, selected, trainRows: fold.train.length, testRows: fold.test.length, outerSignals: foldSignals.length, outerUntouchedBySelection: true }));
  }
  const cost = evaluateCostAwareStrategy(outerSignals, options);
  return Object.freeze({
    phase: '57.p7',
    status: outerSignals.length ? 'NESTED_INTRADAY_OOS_READY' : 'NO_NESTED_INTRADAY_SIGNALS',
    foldSummaries: Object.freeze(foldSummaries),
    signalCount: outerSignals.length,
    hitRate: outerSignals.length ? outerSignals.filter(s => s.correct).length / outerSignals.length : null,
    costAware: Object.freeze({ sampleCount: cost.sampleCount, netAverageReturn: cost.netAverageReturn, grossAverageReturn: cost.grossAverageReturn, profitFactor: cost.profitFactor, winRate: cost.winRate }),
    pointInTime: Object.freeze({ innerSelectionOnly: true, outerTestUntouchedBySelection: true, thresholdNeverSelectedOnOuter: true, modelHyperparametersNeverSelectedOnOuter: true }),
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

export default { selectInnerIntradayConfig, evaluateNestedIntradaySelection };
