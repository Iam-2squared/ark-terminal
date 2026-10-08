import { PHASE57_EXIT_V5_DATASET_POLICY, assertExitV5ResearchSafety } from './phase57-exit-v5-continuation-dataset.js';

export const PHASE57_EXIT_V5_MODEL_POLICY = Object.freeze({
  candidateFamily: PHASE57_EXIT_V5_DATASET_POLICY.candidateFamily,
  modelForm: 'TWO_HEAD_MEAN_PLUS_LOWER_QUANTILE',
  primaryHorizonBars: 3,
  meanTarget: 'incrementalLiquidationReturnPct@3bar',
  lowerQuantile: 0.10,
  meanLoss: 'HUBER',
  quantileLoss: 'PINBALL',
  decisionRule: 'continuationScorePct <= 0 => EXIT; otherwise HOLD',
  lambdaSelectionSplit: 'development',
  validationRetuningAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  performancePromotionAllowed: false,
  transactionCostTreatment: 'INCREMENTAL_DIFFERENTIAL_ONLY',
});

function finite(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`${name} must be finite`);
  return n;
}

/**
 * Freeze all decision-time scalar choices after development.
 * This object is intended to be serialized with research evidence so validation,
 * untouched OOS and prospective evaluation cannot silently retune lambda/thresholds.
 */
export function freezeExitV5ModelSpec({ lambda, selectedOn = 'development', lowerQuantile = 0.10, primaryHorizonBars = 3 }) {
  assertExitV5ResearchSafety();
  const riskLambda = finite(lambda, 'lambda');
  if (riskLambda < 0) throw new Error('lambda must be non-negative');
  if (selectedOn !== 'development') throw new Error('EXIT v5 model spec may only be selected on development data');
  if (!(lowerQuantile > 0 && lowerQuantile < 0.5)) throw new Error('lowerQuantile must be in (0, 0.5)');
  if (primaryHorizonBars !== PHASE57_EXIT_V5_MODEL_POLICY.primaryHorizonBars) {
    throw new Error(`v5.0 primary horizon is frozen at ${PHASE57_EXIT_V5_MODEL_POLICY.primaryHorizonBars} bars`);
  }
  return Object.freeze({
    candidateFamily: PHASE57_EXIT_V5_MODEL_POLICY.candidateFamily,
    modelForm: PHASE57_EXIT_V5_MODEL_POLICY.modelForm,
    lambda: riskLambda,
    lowerQuantile,
    primaryHorizonBars,
    selectedOn,
    decisionThresholdPct: 0,
    frozen: true,
  });
}

/**
 * Score a fitted model's two causal forecasts. q10 is a RETURN quantile, therefore
 * downside risk is the positive loss magnitude max(0, -q10), avoiding the CVaR/
 * quantile sign error where a more-negative tail would increase continuation value.
 *
 * incrementalCostPct is only the DIFFERENCE between HOLD-then-liquidate and
 * liquidate-now costs. Common sunk/exit costs must not be subtracted twice.
 */
export function scoreExitV5Continuation({ meanIncrementalReturnPct, q10IncrementalReturnPct, incrementalCostPct = 0 }, frozenSpec) {
  if (!frozenSpec?.frozen || frozenSpec.selectedOn !== 'development') throw new Error('a frozen development-selected model spec is required');
  const mean = finite(meanIncrementalReturnPct, 'meanIncrementalReturnPct');
  const q10 = finite(q10IncrementalReturnPct, 'q10IncrementalReturnPct');
  const differentialCost = finite(incrementalCostPct, 'incrementalCostPct');
  if (differentialCost < 0) throw new Error('incrementalCostPct must be non-negative');

  const downsideRiskPct = Math.max(0, -q10);
  const continuationScorePct = mean - frozenSpec.lambda * downsideRiskPct - differentialCost;
  const decision = continuationScorePct <= frozenSpec.decisionThresholdPct ? 'EXIT' : 'HOLD';

  return Object.freeze({
    meanIncrementalReturnPct: mean,
    q10IncrementalReturnPct: q10,
    downsideRiskPct,
    incrementalCostPct: differentialCost,
    continuationScorePct,
    decision,
  });
}

/**
 * Evaluation-only diagnostics. realizedIncrementalReturnPct is a forward label and
 * must never be passed into scoreExitV5Continuation or any feature builder.
 */
export function evaluateExitV5Predictions(rows) {
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('rows must be a non-empty array');
  let squaredError = 0;
  let absoluteError = 0;
  let holdCount = 0;
  let exitCount = 0;
  let holdRealizedSum = 0;
  let exitLossAvoidedSum = 0;
  let correctSign = 0;

  for (const row of rows) {
    const predicted = finite(row.meanIncrementalReturnPct, 'row.meanIncrementalReturnPct');
    const realized = finite(row.realizedIncrementalReturnPct, 'row.realizedIncrementalReturnPct');
    const score = finite(row.continuationScorePct, 'row.continuationScorePct');
    const decision = row.decision;
    if (decision !== 'HOLD' && decision !== 'EXIT') throw new Error('row.decision must be HOLD or EXIT');
    const error = predicted - realized;
    squaredError += error * error;
    absoluteError += Math.abs(error);
    if (Math.sign(predicted) === Math.sign(realized) || (predicted === 0 && realized === 0)) correctSign += 1;
    if (decision === 'HOLD') {
      holdCount += 1;
      holdRealizedSum += realized;
    } else {
      exitCount += 1;
      exitLossAvoidedSum += Math.max(0, -realized);
    }
    if (!Number.isFinite(score)) throw new Error('continuationScorePct must be finite');
  }

  const n = rows.length;
  return Object.freeze({
    sampleCount: n,
    rmsePct: Math.sqrt(squaredError / n),
    maePct: absoluteError / n,
    signAccuracy: correctSign / n,
    holdCount,
    exitCount,
    meanRealizedContinuationWhenHeldPct: holdCount ? holdRealizedSum / holdCount : null,
    meanAdditionalLossAvoidedWhenExitPct: exitCount ? exitLossAvoidedSum / exitCount : null,
  });
}

/**
 * Promotion gate intentionally cannot promote. It only reports research evidence.
 * Any future promotion must be a separate human-reviewed process outside this module.
 */
export function buildExitV5ResearchEvidence({ splitName, pairedAgainst, metrics, spec }) {
  if (!['validation', 'oos', 'prospective'].includes(splitName)) throw new Error('splitName must be validation, oos, or prospective');
  if (!['v3', 'v4'].includes(pairedAgainst)) throw new Error('pairedAgainst must be v3 or v4');
  if (!spec?.frozen || spec.selectedOn !== 'development') throw new Error('frozen development-selected spec required');
  return Object.freeze({
    splitName,
    pairedAgainst,
    metrics: Object.freeze({ ...metrics }),
    spec,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    verdict: 'RESEARCH_EVIDENCE_ONLY',
  });
}
