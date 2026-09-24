import {
  PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  PHASE57_EXIT_V5_PAIRED_SAFETY,
  assertExitV5OutcomeUsesInvariant,
  buildExitV5CalibrationRows,
  evaluateExitV5OutcomeWindows,
  fitExitV5PairedModelsFromPurgedSplit,
  simulateExitV5FrozenPolicy,
  summarizeExitV5Pairs,
} from './phase57-exit-v5-paired-evaluator.js';
import { runExitV5AuditedSplitPairedEvaluation } from './phase57-exit-v5-audited-split-evaluator.js';
import { fitExitV5GbmModel, PHASE57_EXIT_V5_GBM_POLICY } from './phase57-exit-v5-gbm-model.js';

const FALSE_SAFETY_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
]);

export const PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS = Object.freeze([
  ...PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  'V5_GBM',
]);

const DELTA_PAIRS = Object.freeze([
  Object.freeze(['V4_MINUS_V3', 'V4', 'V3']),
  Object.freeze(['V5_UNCONDITIONAL_MINUS_V3', 'V5_UNCONDITIONAL', 'V3']),
  Object.freeze(['V5_UNCONDITIONAL_MINUS_V4', 'V5_UNCONDITIONAL', 'V4']),
  Object.freeze(['V5_CONDITIONAL_MINUS_V3', 'V5_CONDITIONAL', 'V3']),
  Object.freeze(['V5_CONDITIONAL_MINUS_V4', 'V5_CONDITIONAL', 'V4']),
  Object.freeze(['V5_CONDITIONAL_MINUS_V5_UNCONDITIONAL', 'V5_CONDITIONAL', 'V5_UNCONDITIONAL']),
  Object.freeze(['V5_GBM_MINUS_V3', 'V5_GBM', 'V3']),
  Object.freeze(['V5_GBM_MINUS_V4', 'V5_GBM', 'V4']),
  Object.freeze(['V5_GBM_MINUS_V5_UNCONDITIONAL', 'V5_GBM', 'V5_UNCONDITIONAL']),
  Object.freeze(['V5_GBM_MINUS_V5_CONDITIONAL', 'V5_GBM', 'V5_CONDITIONAL']),
]);

export const PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY = Object.freeze({
  phase: '57.exit-v5.gbm-five-way-challenger.v1',
  comparisonModels: PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
  baseEvidenceContractPreserved: true,
  primaryHorizonBars: 3,
  fitSplit: 'development',
  gbmModelType: PHASE57_EXIT_V5_GBM_POLICY.modelType,
  gbmSpecSelectedOn: 'development',
  evaluationLabelsUsedByDecision: false,
  validationRefitAllowed: false,
  validationRetuningAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  automaticPromotionAllowed: false,
});

export const PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY = Object.freeze({
  ...PHASE57_EXIT_V5_PAIRED_SAFETY,
  researchOnly: true,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

export function fitExitV5GbmChallengerModelsFromPurgedSplit(purgedSplit, {
  baseModelOptions = {},
  gbmModelOptions = {},
} = {}) {
  assertExitV5GbmChallengerSafety();
  if (purgedSplit?.splitPolicy?.labelBoundaryPurged !== true
    || purgedSplit?.splitPolicy?.sessionAware !== true
    || purgedSplit?.splitPolicy?.boundarySessionTreatment !== 'PURGE_ENTIRE_SESSION') {
    throw new Error('GBM challenger requires an audited label- and session-purged split');
  }
  const base = fitExitV5PairedModelsFromPurgedSplit(purgedSplit, baseModelOptions);
  const gbm = fitExitV5GbmModel(purgedSplit.development, gbmModelOptions);
  if (base.sampleCount !== gbm.sampleCount || base.sampleCount !== purgedSplit.development.length) {
    throw new Error('GBM challenger Development sample lineage mismatch');
  }
  return Object.freeze({
    ...base,
    gbm,
    gbmModelFingerprint: gbm.modelFingerprint,
    sameDevelopmentSamplesForAllV5Models: true,
    comparisonModels: PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
    refitAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

export function summarizeExitV5GbmChallengerPairs(pairs) {
  return summarizeExitV5Pairs(pairs, {
    modelIds: PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
    deltaPairs: DELTA_PAIRS,
  });
}

/**
 * Adds one fixed GBM challenger to the untouched four-way evaluator. The existing
 * four model outcomes are computed by their original entrypoint and then extended
 * with a fifth outcome bound to the same invariant hash and finalized-bar path.
 */
export function runExitV5GbmChallengerPairedEvaluation({
  evaluationRows,
  purgedSplit,
  analogPool,
  fittedModels,
  splitName,
  pairedContract,
  roundTripCostPct = 0.05,
  incrementalCostPct = 0,
  evaluationHorizons = [1, 3, 6],
} = {}) {
  assertExitV5GbmChallengerSafety();
  if (fittedModels?.sameDevelopmentSamplesForAllV5Models !== true || fittedModels?.gbm?.trainedOn !== 'development') {
    throw new Error('frozen Development-fitted GBM challenger models required');
  }
  if (fittedModels.sampleCount !== fittedModels.gbm.sampleCount) throw new Error('GBM challenger fitted sample count mismatch');

  const base = runExitV5AuditedSplitPairedEvaluation({
    evaluationRows,
    purgedSplit,
    analogPool,
    fittedModels,
    splitName,
    pairedContract,
    roundTripCostPct,
    incrementalCostPct,
    evaluationHorizons,
  });
  const horizons = base.evaluationHorizons;
  const pairs = base.pairs.map((pair, index) => {
    const row = evaluationRows[index];
    if (pair.invariant.pairKey !== pair.pairKey) throw new Error('base pair invariant identity drift');
    const rawOutcome = simulateExitV5FrozenPolicy({
      row,
      fittedModel: fittedModels.gbm,
      modelId: 'V5_GBM',
      roundTripCostPct: pair.invariant.roundTripCostPct,
      incrementalCostPct: pair.invariant.incrementalCostPct,
    });
    const outcome = assertExitV5OutcomeUsesInvariant(rawOutcome, row.futureBars, pair.invariant, 'V5_GBM');
    const evaluation = evaluateExitV5OutcomeWindows({
      row,
      outcome,
      futureBars: row.futureBars,
      direction: pair.invariant.direction,
      horizons,
      roundTripCostPct: pair.invariant.roundTripCostPct,
    });
    const calibration = buildExitV5CalibrationRows(outcome, row.futureBars, pair.invariant.direction);
    return Object.freeze({
      ...pair,
      outcomes: Object.freeze({ ...pair.outcomes, V5_GBM: outcome }),
      evaluation: Object.freeze({ ...pair.evaluation, V5_GBM: evaluation }),
      calibration: Object.freeze({ ...pair.calibration, V5_GBM: calibration }),
    });
  });
  const frozenPairs = Object.freeze(pairs);
  const summary = summarizeExitV5GbmChallengerPairs(frozenPairs);

  return Object.freeze({
    ...base,
    phase: PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.phase,
    status: 'EXIT_V5_GBM_FIVE_WAY_PAIRED_EVALUATED',
    comparisonModels: PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
    pairs: frozenPairs,
    summary,
    gbmModelFingerprint: fittedModels.gbm.modelFingerprint,
    developmentRefitPerformed: false,
    methodology: Object.freeze({
      ...base.methodology,
      originalFourWayPolicyUnchanged: true,
      exactSameFrozenInputForAllFiveModels: true,
      sameDevelopmentSamplesForAllV5Models: true,
      gbmMeanObjective: PHASE57_EXIT_V5_GBM_POLICY.meanObjective,
      gbmLowerQuantileObjective: PHASE57_EXIT_V5_GBM_POLICY.lowerQuantileObjective,
      validationRefit: false,
      validationRetuning: false,
      outerOosRetuning: false,
      prospectiveRetuning: false,
      resultBasedPromotion: false,
    }),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY,
  });
}

export function assertExitV5GbmChallengerSafety() {
  for (const key of FALSE_SAFETY_KEYS) {
    if (PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY[key] !== false) throw new Error(`unsafe EXIT v5 GBM challenger flag: ${key}`);
  }
  if (PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY.researchOnly !== true) throw new Error('EXIT v5 GBM challenger must remain research-only');
  if (PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.evaluationLabelsUsedByDecision !== false
    || PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY.automaticPromotionAllowed !== false) {
    throw new Error('EXIT v5 GBM challenger methodology boundary violation');
  }
  return true;
}

export default {
  PHASE57_EXIT_V5_GBM_CHALLENGER_MODEL_IDS,
  PHASE57_EXIT_V5_GBM_CHALLENGER_POLICY,
  PHASE57_EXIT_V5_GBM_CHALLENGER_SAFETY,
  assertExitV5GbmChallengerSafety,
  fitExitV5GbmChallengerModelsFromPurgedSplit,
  summarizeExitV5GbmChallengerPairs,
  runExitV5GbmChallengerPairedEvaluation,
};
