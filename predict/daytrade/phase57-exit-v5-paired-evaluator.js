import crypto from 'node:crypto';
import { simulateP25ExitV3DualGate } from './phase57-p25-exit-v3-dual-gate.js';
import { simulateP25ExitV4 } from './phase57-p25-exit-v4-structural-risk.js';
import {
  PHASE57_EXIT_V5_RESEARCH_SAFETY,
  assertExitV5ResearchSafety,
  buildExitV5Features,
} from './phase57-exit-v5-continuation-dataset.js';
import { scoreExitV5Continuation } from './phase57-exit-v5-continuation-model.js';
import { fitExitV5DevelopmentBaseline } from './phase57-exit-v5-training-harness.js';
import {
  fitExitV5ConditionalModel,
  predictExitV5Conditional,
} from './phase57-exit-v5-conditional-model.js';
import { predictExitV5Gbm } from './phase57-exit-v5-gbm-model.js';

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

export const PHASE57_EXIT_V5_PAIRED_MODEL_IDS = Object.freeze([
  'V3',
  'V4',
  'V5_UNCONDITIONAL',
  'V5_CONDITIONAL',
]);

export const PHASE57_EXIT_V5_PAIRED_POLICY = Object.freeze({
  phase: '57.exit-v5.four-way-paired.v1',
  comparisonModels: PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  fitSplit: 'development',
  evaluationSplits: Object.freeze(['validation', 'oos', 'prospective']),
  primaryHorizonBars: 3,
  boundaryPurgingRequired: true,
  sessionPurgingRequired: true,
  sameSelectorRequired: true,
  sameFrozenEntryRequired: true,
  sameDirectionRequired: true,
  sameEntryPriceRequired: true,
  sameMarketDataRequired: true,
  sameTransactionCostRequired: true,
  sameCapitalAllocationRequired: true,
  evaluationLabelsUsedByDecision: false,
  validationRefitAllowed: false,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  automaticPromotionAllowed: false,
  noObservationPolicy: 'NO_FINALIZED_BAR_DOES_NOT_ADVANCE_STATE',
});

export const PHASE57_EXIT_V5_PAIRED_SAFETY = Object.freeze({
  ...PHASE57_EXIT_V5_RESEARCH_SAFETY,
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

const REQUIRED_CONTRACT_KEYS = Object.freeze([
  'selectorPolicyId',
  'entryPolicyId',
  'marketDataPolicyId',
  'transactionCostPolicyId',
  'capitalAllocationPolicyId',
]);

function finite(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new Error(`${name} must be finite`);
  return number;
}

function finiteOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function isoMillis(value, name) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) throw new Error(`${name} must be an ISO timestamp`);
  return parsed;
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function median(values) {
  if (!values.length) return null;
  const ordered = [...values].sort((a, b) => a - b);
  const midpoint = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[midpoint] : (ordered[midpoint - 1] + ordered[midpoint]) / 2;
}

function sampleStandardDeviation(values) {
  if (values.length < 2) return null;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - average) ** 2), 0) / (values.length - 1));
}

function directionOf(row) {
  const value = row?.signalDirection ?? row?.direction;
  if (value === 'LONG' || value === 'UP' || value === 1 || value === '+1') return 'LONG';
  if (value === 'SHORT' || value === 'DOWN' || value === -1 || value === '-1') return 'SHORT';
  throw new Error(`unsupported paired EXIT direction: ${value}`);
}

function directionSign(direction) {
  return direction === 'LONG' ? 1 : -1;
}

function directionalReturnPct(fromPrice, toPrice, direction) {
  return ((Number(toPrice) / Number(fromPrice)) - 1) * 100 * directionSign(direction);
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    const entries = Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
}

function normalizeBarsStrict(rows, label) {
  if (!Array.isArray(rows) || rows.length === 0) throw new Error(`${label} must contain finalized bars`);
  const bars = rows.map((row, index) => {
    const timestampMs = isoMillis(row?.timestamp ?? row?.time, `${label}[${index}].timestamp`);
    const close = finite(row?.close, `${label}[${index}].close`);
    const open = finite(row?.open, `${label}[${index}].open`);
    const high = finite(row?.high, `${label}[${index}].high`);
    const low = finite(row?.low, `${label}[${index}].low`);
    const volume = finite(row?.volume ?? 0, `${label}[${index}].volume`);
    if (close <= 0 || open <= 0 || high <= 0 || low <= 0 || volume < 0) throw new Error(`${label}[${index}] contains an invalid finalized bar`);
    if (high < Math.max(open, close, low) || low > Math.min(open, close, high)) throw new Error(`${label}[${index}] has inconsistent OHLC values`);
    return Object.freeze({
      timestamp: new Date(timestampMs).toISOString(),
      open,
      high,
      low,
      close,
      volume,
    });
  });
  for (let index = 1; index < bars.length; index += 1) {
    if (bars[index].timestamp <= bars[index - 1].timestamp) throw new Error(`${label} timestamps must be strictly increasing`);
  }
  return Object.freeze(bars);
}

function assertFrozenResearchRow(row) {
  if (row?.entryAccepted !== true || row?.frozenBeforeOutcome !== true || row?.currentOutcomeUsed !== false) {
    throw new Error('paired EXIT evaluation requires outcome-free frozen Entry');
  }
  const entryPrice = finite(row?.entryPrice, 'row.entryPrice');
  if (entryPrice <= 0) throw new Error('row.entryPrice must be positive');
  const entryTimestampMs = isoMillis(row?.entryTimestamp, 'row.entryTimestamp');
  if (!String(row?.symbol ?? '').trim()) throw new Error('row.symbol is required');
  if (!String(row?.sessionDate ?? '').trim()) throw new Error('row.sessionDate is required');
  const direction = directionOf(row);
  const futureBars = normalizeBarsStrict(row?.futureBars, 'row.futureBars');
  if (isoMillis(futureBars[0].timestamp, 'first future bar') <= entryTimestampMs) {
    throw new Error('futureBars must begin strictly after entryTimestamp');
  }
  return Object.freeze({ entryPrice, entryTimestampMs, direction, futureBars });
}

function assertContract(contract) {
  if (!contract || typeof contract !== 'object') throw new Error('explicit pairedContract is required');
  const normalized = {};
  for (const key of REQUIRED_CONTRACT_KEYS) {
    const value = String(contract[key] ?? '').trim();
    if (!value) throw new Error(`pairedContract.${key} is required`);
    normalized[key] = value;
  }
  return Object.freeze(normalized);
}

function assertOptionalRowContract(row, contract) {
  for (const key of REQUIRED_CONTRACT_KEYS) {
    if (row?.[key] !== undefined && String(row[key]) !== contract[key]) {
      throw new Error(`paired invariant mismatch for ${key}`);
    }
  }
}

function pairKeyOf(row, direction) {
  return `${String(row.sessionDate)}|${String(row.entryTimestamp)}|${String(row.symbol).trim().toUpperCase()}|${direction}`;
}

export function buildExitV5PairedInvariant({ row, pairedContract, roundTripCostPct = 0.05, incrementalCostPct = 0 } = {}) {
  const validated = assertFrozenResearchRow(row);
  const contract = assertContract(pairedContract);
  assertOptionalRowContract(row, contract);
  const roundTripCost = finite(roundTripCostPct, 'roundTripCostPct');
  const differentialCost = finite(incrementalCostPct, 'incrementalCostPct');
  if (roundTripCost < 0 || differentialCost < 0) throw new Error('paired EXIT costs must be non-negative');

  const contextBars = Array.isArray(row.contextBars) && row.contextBars.length
    ? normalizeBarsStrict(row.contextBars, 'row.contextBars')
    : Object.freeze([]);
  const marketDataFingerprint = sha256({ contextBars, futureBars: validated.futureBars });
  const invariantValues = Object.freeze({
    pairKey: pairKeyOf(row, validated.direction),
    symbol: String(row.symbol).trim().toUpperCase(),
    sessionDate: String(row.sessionDate),
    entryTimestamp: new Date(validated.entryTimestampMs).toISOString(),
    entryPrice: validated.entryPrice,
    direction: validated.direction,
    selectorPolicyId: contract.selectorPolicyId,
    entryPolicyId: contract.entryPolicyId,
    marketDataPolicyId: contract.marketDataPolicyId,
    marketDataFingerprint,
    transactionCostPolicyId: contract.transactionCostPolicyId,
    roundTripCostPct: roundTripCost,
    incrementalCostPct: differentialCost,
    capitalAllocationPolicyId: contract.capitalAllocationPolicyId,
    singleFrozenInputAppliedToAllModels: true,
  });
  return Object.freeze({ ...invariantValues, invariantSha256: sha256(invariantValues) });
}

function assertDevelopmentSamples(developmentSamples, developmentEnd) {
  if (!Array.isArray(developmentSamples) || developmentSamples.length < 2) throw new Error('developmentSamples must contain at least 2 samples');
  const developmentEndMs = isoMillis(developmentEnd, 'developmentEnd');
  let previous = -Infinity;
  let labelThroughMs = -Infinity;
  for (const [index, sample] of developmentSamples.entries()) {
    const featureAt = isoMillis(sample?.features?.featureAt, `developmentSamples[${index}].features.featureAt`);
    const labelThrough = isoMillis(sample?.labels?.labelThrough, `developmentSamples[${index}].labels.labelThrough`);
    finite(sample?.labels?.incrementalLiquidationReturnPctByHorizon?.[3], `developmentSamples[${index}] 3-bar label`);
    if (featureAt < previous) throw new Error('developmentSamples must be chronological');
    if (labelThrough < featureAt) throw new Error('development labelThrough cannot precede featureAt');
    if (labelThrough > developmentEndMs) throw new Error('development label crosses the purged development boundary');
    previous = featureAt;
    labelThroughMs = Math.max(labelThroughMs, labelThrough);
  }
  return Object.freeze({
    developmentEnd: new Date(developmentEndMs).toISOString(),
    labelThrough: new Date(labelThroughMs).toISOString(),
  });
}

/**
 * Fits both v5 baselines from the exact same already-purged development samples.
 * Evaluation rows are deliberately not accepted by this API.
 */
export function fitExitV5PairedDevelopmentModels(developmentSamples, {
  developmentEnd,
  boundaryPurgingConfirmed = false,
  sessionPurgingConfirmed = false,
  lambda = 1,
  lowerQuantile = 0.10,
  k = 40,
  minNeighbors = 20,
} = {}) {
  assertExitV5ResearchSafety();
  if (boundaryPurgingConfirmed !== true) throw new Error('boundaryPurgingConfirmed must be true');
  if (sessionPurgingConfirmed !== true) throw new Error('sessionPurgingConfirmed must be true');
  const boundary = assertDevelopmentSamples(developmentSamples, developmentEnd);
  const unconditional = fitExitV5DevelopmentBaseline(developmentSamples, { lambda, lowerQuantile });
  const conditional = fitExitV5ConditionalModel(developmentSamples, { k, minNeighbors, lambda, lowerQuantile });
  if (unconditional.sampleCount !== conditional.sampleCount) throw new Error('v5 paired models were not fit on identical development samples');

  return Object.freeze({
    trainedOn: 'development',
    sampleCount: developmentSamples.length,
    developmentEnd: boundary.developmentEnd,
    developmentLabelThrough: boundary.labelThrough,
    developmentFingerprint: sha256(developmentSamples),
    boundaryPurgingConfirmed: true,
    sessionPurgingConfirmed: true,
    unconditional,
    conditional,
    refitAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
  });
}

/** Preferred fit entrypoint: accepts only the audited output of the v5 split builder. */
export function fitExitV5PairedModelsFromPurgedSplit(purgedSplit, options = {}) {
  if (purgedSplit?.splitPolicy?.labelBoundaryPurged !== true || purgedSplit?.splitPolicy?.sessionAware !== true) {
    throw new Error('audited label- and session-purged split is required');
  }
  if (purgedSplit.splitPolicy.boundarySessionTreatment !== 'PURGE_ENTIRE_SESSION') {
    throw new Error('boundary sessions must be purged in full');
  }
  if (!purgedSplit?.boundaries?.developmentEnd) throw new Error('purged split development boundary is required');
  return fitExitV5PairedDevelopmentModels(purgedSplit.development, {
    ...options,
    developmentEnd: purgedSplit.boundaries.developmentEnd,
    boundaryPurgingConfirmed: true,
    sessionPurgingConfirmed: true,
  });
}

function assertFittedModels(fittedModels) {
  if (!fittedModels || fittedModels.trainedOn !== 'development' || fittedModels.boundaryPurgingConfirmed !== true || fittedModels.sessionPurgingConfirmed !== true) {
    throw new Error('paired evaluator requires purged development-fitted v5 models');
  }
  if (fittedModels.unconditional?.trainedOn !== 'development' || fittedModels.conditional?.trainedOn !== 'development') {
    throw new Error('both v5 models must remain development-fitted');
  }
  if (fittedModels.unconditional.sampleCount !== fittedModels.conditional.sampleCount || fittedModels.sampleCount !== fittedModels.unconditional.sampleCount) {
    throw new Error('v5 development sample lineage mismatch');
  }
}

function buildV5Outcome({ row, futureBars, direction, decisions, exitIndex, exitReason, roundTripCostPct, modelId }) {
  const entryPrice = Number(row.entryPrice);
  const exitBar = futureBars[exitIndex];
  const used = futureBars.slice(0, exitIndex + 1);
  const grossReturnPct = directionalReturnPct(entryPrice, exitBar.close, direction);
  const mfePct = Math.max(0, ...used.map((bar) => directionalReturnPct(entryPrice, direction === 'LONG' ? bar.high : bar.low, direction)));
  const maePct = Math.min(0, ...used.map((bar) => directionalReturnPct(entryPrice, direction === 'LONG' ? bar.low : bar.high, direction)));
  return Object.freeze({
    model: modelId,
    exitTimestamp: exitBar.timestamp,
    exitPrice: exitBar.close,
    exitReason,
    barsHeld: used.length,
    holdingMinutes: (Date.parse(exitBar.timestamp) - Date.parse(row.entryTimestamp)) / 60_000,
    grossReturnPct,
    netReturnPct: grossReturnPct - roundTripCostPct,
    mfePct,
    maePct,
    givebackPct: Math.max(0, mfePct - grossReturnPct),
    captureRatio: mfePct > 0 ? grossReturnPct / mfePct : null,
    managementDecisions: Object.freeze(decisions),
    evaluationLabelsUsedByDecision: false,
    safety: PHASE57_EXIT_V5_PAIRED_SAFETY,
  });
}

/** Runs a frozen v5 policy over one trade using only prefixes observed through each bar. */
export function simulateExitV5FrozenPolicy({
  row,
  fittedModel,
  modelId,
  roundTripCostPct = 0.05,
  incrementalCostPct = 0,
} = {}) {
  const validated = assertFrozenResearchRow(row);
  if (!['V5_UNCONDITIONAL', 'V5_CONDITIONAL', 'V5_GBM'].includes(modelId)) throw new Error('modelId must be a supported v5 paired model');
  const roundTripCost = finite(roundTripCostPct, 'roundTripCostPct');
  const differentialCost = finite(incrementalCostPct, 'incrementalCostPct');
  if (roundTripCost < 0 || differentialCost < 0) throw new Error('EXIT v5 costs must be non-negative');
  if (fittedModel?.trainedOn !== 'development') throw new Error('development-fitted frozen v5 model required');

  const observed = [];
  const decisions = [];
  let exitIndex = validated.futureBars.length - 1;
  let exitReason = 'SESSION_END';
  for (let index = 0; index < validated.futureBars.length; index += 1) {
    const bar = validated.futureBars[index];
    observed.push(bar);
    if (observed.length < 2) {
      decisions.push(Object.freeze({
        timestamp: bar.timestamp,
        observedBarCount: observed.length,
        ready: false,
        decision: 'HOLD',
        reason: 'V5_CAUSAL_FEATURE_WARMUP',
      }));
      continue;
    }

    const features = buildExitV5Features({ entryPrice: validated.entryPrice, direction: validated.direction, observedBars: observed });
    let prediction;
    if (modelId === 'V5_UNCONDITIONAL') {
      prediction = Object.freeze({
        ready: true,
        ...scoreExitV5Continuation({
          meanIncrementalReturnPct: fittedModel.meanIncrementalReturnPct,
          q10IncrementalReturnPct: fittedModel.q10IncrementalReturnPct,
          incrementalCostPct: differentialCost,
        }, fittedModel.spec),
      });
    } else if (modelId === 'V5_CONDITIONAL') {
      prediction = predictExitV5Conditional(features, fittedModel, { incrementalCostPct: differentialCost });
    } else {
      prediction = predictExitV5Gbm(features, fittedModel, { incrementalCostPct: differentialCost });
    }
    const decision = prediction.ready === true ? prediction.decision : 'HOLD';
    const reason = prediction.ready !== true
      ? String(prediction.reason ?? 'V5_MODEL_NOT_READY')
      : decision === 'EXIT' ? 'V5_NONPOSITIVE_CONTINUATION_SCORE' : 'V5_POSITIVE_CONTINUATION_SCORE';
    decisions.push(Object.freeze({
      timestamp: bar.timestamp,
      observedBarCount: observed.length,
      features,
      ...prediction,
      decision,
      reason,
    }));
    if (prediction.ready === true && decision === 'EXIT') {
      exitIndex = index;
      exitReason = reason;
      break;
    }
  }

  return buildV5Outcome({
    row,
    futureBars: validated.futureBars,
    direction: validated.direction,
    decisions,
    exitIndex,
    exitReason,
    roundTripCostPct: roundTripCost,
    modelId,
  });
}

export function assertExitV5OutcomeUsesInvariant(outcome, futureBars, invariant, modelId) {
  const exitIndex = futureBars.findIndex((bar) => bar.timestamp === outcome?.exitTimestamp);
  if (exitIndex < 0) throw new Error(`${modelId} exited outside the frozen market-data path`);
  if (Math.abs(Number(outcome.exitPrice) - futureBars[exitIndex].close) > 1e-12) throw new Error(`${modelId} exit price is not the frozen finalized close`);
  if (Number(outcome.barsHeld) !== exitIndex + 1) throw new Error(`${modelId} barsHeld does not match the frozen path`);
  const expectedNet = Number(outcome.grossReturnPct) - invariant.roundTripCostPct;
  if (Math.abs(Number(outcome.netReturnPct) - expectedNet) > 1e-10) throw new Error(`${modelId} transaction-cost invariant mismatch`);
  return Object.freeze({ ...outcome, invariantSha256: invariant.invariantSha256 });
}

export function evaluateExitV5OutcomeWindows({ row, outcome, futureBars, direction, horizons, roundTripCostPct }) {
  const exitIndex = futureBars.findIndex((bar) => bar.timestamp === outcome.exitTimestamp);
  const windows = [];
  for (const horizonBars of horizons) {
    const target = futureBars[exitIndex + horizonBars];
    if (!target) continue;
    const forwardDirectionalReturnPct = directionalReturnPct(outcome.exitPrice, target.close, direction);
    windows.push(Object.freeze({
      horizonBars,
      targetTimestamp: target.timestamp,
      forwardDirectionalReturnPct,
      postExitRegretPct: Math.max(0, forwardDirectionalReturnPct - roundTripCostPct),
      additionalLossAvoidedPct: Math.max(0, -forwardDirectionalReturnPct),
    }));
  }
  const earlyExit = windows.some((window) => window.postExitRegretPct > 0);
  const lateExit = Number(outcome.givebackPct) > roundTripCostPct;
  return Object.freeze({
    diagnosticOnly: true,
    outcomeWindowsNeverUsedByDecisionPolicy: true,
    windows: Object.freeze(windows),
    earlyExit,
    lateExit,
    maxPostExitRegretPct: windows.length ? Math.max(...windows.map((window) => window.postExitRegretPct)) : null,
    maxAdditionalLossAvoidedPct: windows.length ? Math.max(...windows.map((window) => window.additionalLossAvoidedPct)) : null,
  });
}

export function buildExitV5CalibrationRows(outcome, futureBars, direction) {
  const rows = [];
  for (const decision of outcome.managementDecisions ?? []) {
    if (decision?.ready !== true || !Number.isFinite(Number(decision.meanIncrementalReturnPct))) continue;
    const currentIndex = futureBars.findIndex((bar) => bar.timestamp === decision.timestamp);
    const target = futureBars[currentIndex + PHASE57_EXIT_V5_PAIRED_POLICY.primaryHorizonBars];
    if (currentIndex < 0 || !target) continue;
    const current = futureBars[currentIndex];
    rows.push(Object.freeze({
      featureAt: decision.timestamp,
      labelThrough: target.timestamp,
      predictedMeanPct: Number(decision.meanIncrementalReturnPct),
      predictedQ10Pct: Number(decision.q10IncrementalReturnPct),
      continuationScorePct: Number(decision.continuationScorePct),
      decision: decision.decision,
      realizedIncrementalReturnPct: directionalReturnPct(current.close, target.close, direction),
      evaluationOnly: true,
    }));
  }
  return Object.freeze(rows);
}

function tradeMetadata(row, direction) {
  return Object.freeze({
    direction,
    setup: String(row.setup ?? row.setupId ?? 'UNKNOWN'),
    volatilityRegime: String(row.volatilityRegime ?? row.volRegime ?? 'UNKNOWN'),
    timeOfDay: String(row.timeOfDayBucket ?? row.timeOfDay ?? 'UNKNOWN'),
    symbol: String(row.symbol).trim().toUpperCase(),
    sector: String(row.sector ?? 'UNKNOWN'),
  });
}

function summarizeCalibration(rows) {
  if (!rows.length) return Object.freeze({ sampleCount: 0 });
  const errors = rows.map((row) => row.predictedMeanPct - row.realizedIncrementalReturnPct);
  const predicted = rows.map((row) => row.predictedMeanPct);
  const realized = rows.map((row) => row.realizedIncrementalReturnPct);
  const signCorrect = rows.filter((row) => Math.sign(row.predictedMeanPct) === Math.sign(row.realizedIncrementalReturnPct)).length;
  const buckets = [
    ['LE_NEGATIVE_HALF', (value) => value <= -0.5],
    ['NEGATIVE_TO_ZERO', (value) => value > -0.5 && value <= 0],
    ['ZERO_TO_POSITIVE_HALF', (value) => value > 0 && value <= 0.5],
    ['GT_POSITIVE_HALF', (value) => value > 0.5],
  ];
  return Object.freeze({
    sampleCount: rows.length,
    meanPredictedPct: mean(predicted),
    meanRealizedPct: mean(realized),
    meanPredictionErrorPct: mean(errors),
    maePct: mean(errors.map(Math.abs)),
    rmsePct: Math.sqrt(mean(errors.map((error) => error ** 2))),
    signAccuracy: signCorrect / rows.length,
    buckets: Object.freeze(Object.fromEntries(buckets.map(([name, include]) => {
      const selected = rows.filter((row) => include(row.predictedMeanPct));
      return [name, Object.freeze({
        count: selected.length,
        meanPredictedPct: mean(selected.map((row) => row.predictedMeanPct)),
        meanRealizedPct: mean(selected.map((row) => row.realizedIncrementalReturnPct)),
      })];
    }))),
  });
}

function profitFactor(returns) {
  const grossProfit = returns.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const grossLoss = -returns.filter((value) => value < 0).reduce((sum, value) => sum + value, 0);
  if (grossLoss > 0) return grossProfit / grossLoss;
  return grossProfit > 0 ? Infinity : null;
}

function compoundedReturnPct(returns) {
  let equity = 1;
  for (const value of returns) equity *= 1 + value / 100;
  return (equity - 1) * 100;
}

function maxDrawdownPct(returns) {
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value / 100;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, ((peak - equity) / peak) * 100);
  }
  return maxDrawdown;
}

function coreModelSummary(rows, calibration = []) {
  const returns = rows.map((row) => Number(row.outcome.netReturnPct));
  const winners = rows.filter((row) => Number(row.outcome.netReturnPct) > 0);
  const losers = rows.filter((row) => Number(row.outcome.netReturnPct) < 0);
  const returnStd = sampleStandardDeviation(returns);
  const maximumRegret = rows.map((row) => row.evaluation.maxPostExitRegretPct).filter((value) => value !== null);
  const avoidedLoss = rows.map((row) => row.evaluation.maxAdditionalLossAvoidedPct).filter((value) => value !== null);
  return Object.freeze({
    tradeCount: rows.length,
    netReturnPct: compoundedReturnPct(returns),
    averageTradePct: mean(returns),
    medianTradePct: median(returns),
    profitFactor: profitFactor(returns),
    winRate: rows.length ? winners.length / rows.length : null,
    maxDrawdownPct: maxDrawdownPct(returns),
    tradeSharpe: returnStd && returnStd > 0 ? mean(returns) / returnStd : null,
    meanMfePct: mean(rows.map((row) => finiteOrNull(row.outcome.mfePct)).filter((value) => value !== null)),
    meanMaePct: mean(rows.map((row) => finiteOrNull(row.outcome.maePct)).filter((value) => value !== null)),
    meanCaptureRatio: mean(rows.map((row) => finiteOrNull(row.outcome.captureRatio)).filter((value) => value !== null)),
    meanProfitGivebackPct: mean(rows.map((row) => finiteOrNull(row.outcome.givebackPct)).filter((value) => value !== null)),
    meanHoldingBars: mean(rows.map((row) => Number(row.outcome.barsHeld))),
    meanHoldingMinutes: mean(rows.map((row) => {
      const provided = finiteOrNull(row.outcome.holdingMinutes);
      return provided ?? ((Date.parse(row.outcome.exitTimestamp) - Date.parse(row.entryTimestamp)) / 60_000);
    })),
    winnerMeanHoldingBars: mean(winners.map((row) => Number(row.outcome.barsHeld))),
    loserMeanHoldingBars: mean(losers.map((row) => Number(row.outcome.barsHeld))),
    earlyExitRate: rows.length ? rows.filter((row) => row.evaluation.earlyExit).length / rows.length : null,
    lateExitRate: rows.length ? rows.filter((row) => row.evaluation.lateExit).length / rows.length : null,
    meanPostExitRegretPct: mean(maximumRegret),
    meanAdditionalLossAvoidedPct: mean(avoidedLoss),
    calibration: summarizeCalibration(calibration),
  });
}

function groupedSummary(rows, field) {
  const groups = new Map();
  for (const row of rows) {
    const key = String(row.metadata[field] ?? 'UNKNOWN');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return Object.freeze(Object.fromEntries([...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, values]) => [
    key,
    coreModelSummary(values, values.flatMap((row) => row.calibration ?? [])),
  ])));
}

function summarizeModel(pairs, modelId) {
  const rows = pairs.map((pair) => Object.freeze({
    entryTimestamp: pair.invariant.entryTimestamp,
    metadata: pair.metadata,
    outcome: pair.outcomes[modelId],
    evaluation: pair.evaluation[modelId],
    calibration: pair.calibration[modelId] ?? [],
  }));
  const calibration = rows.flatMap((row) => row.calibration);
  return Object.freeze({
    ...coreModelSummary(rows, calibration),
    segments: Object.freeze({
      direction: groupedSummary(rows, 'direction'),
      setup: groupedSummary(rows, 'setup'),
      volatilityRegime: groupedSummary(rows, 'volatilityRegime'),
      timeOfDay: groupedSummary(rows, 'timeOfDay'),
      symbol: groupedSummary(rows, 'symbol'),
      sector: groupedSummary(rows, 'sector'),
    }),
  });
}

function summarizeDelta(pairs, leftModel, rightModel) {
  const netDeltas = pairs.map((pair) => Number(pair.outcomes[leftModel].netReturnPct) - Number(pair.outcomes[rightModel].netReturnPct));
  const barsDeltas = pairs.map((pair) => Number(pair.outcomes[leftModel].barsHeld) - Number(pair.outcomes[rightModel].barsHeld));
  return Object.freeze({
    pairedCount: pairs.length,
    leftModel,
    rightModel,
    meanNetReturnDeltaPct: mean(netDeltas),
    medianNetReturnDeltaPct: median(netDeltas),
    meanBarsHeldDelta: mean(barsDeltas),
    leftBetterCount: netDeltas.filter((value) => value > 0).length,
    leftWorseCount: netDeltas.filter((value) => value < 0).length,
    equalCount: netDeltas.filter((value) => value === 0).length,
  });
}

/**
 * Rebuilds the complete four-way summary from already-audited pair rows. This is
 * intentionally exported so independently computed validation-session shards can
 * be reduced without rerunning any EXIT decision.
 */
export function summarizeExitV5Pairs(pairs, { modelIds, deltaPairs = [] } = {}) {
  if (!Array.isArray(pairs) || pairs.length === 0) throw new Error('paired summary requires non-empty pairs');
  if (!Array.isArray(modelIds) || modelIds.length === 0 || new Set(modelIds).size !== modelIds.length) {
    throw new Error('paired summary requires unique modelIds');
  }
  if (!Array.isArray(deltaPairs)) throw new Error('deltaPairs must be an array');
  const seen = new Set();
  for (const [index, pair] of pairs.entries()) {
    if (!String(pair?.pairKey ?? '').trim()) throw new Error(`pairs[${index}].pairKey is required`);
    if (seen.has(pair.pairKey)) throw new Error(`duplicate paired summary key: ${pair.pairKey}`);
    seen.add(pair.pairKey);
    if (!pair?.invariant?.invariantSha256) throw new Error(`pairs[${index}] invariant hash is required`);
    for (const modelId of modelIds) {
      if (!pair?.outcomes?.[modelId] || !pair?.evaluation?.[modelId] || !Array.isArray(pair?.calibration?.[modelId])) {
        throw new Error(`pairs[${index}] is missing ${modelId} paired evidence`);
      }
      if (pair.outcomes[modelId].invariantSha256 !== pair.invariant.invariantSha256) {
        throw new Error(`pairs[${index}] ${modelId} invariant hash mismatch`);
      }
    }
  }

  const frozenPairs = Object.freeze([...pairs]);
  const models = Object.freeze(Object.fromEntries(modelIds.map((modelId) => [modelId, summarizeModel(frozenPairs, modelId)])));
  const pairedDeltas = Object.freeze(Object.fromEntries(deltaPairs.map(([name, leftModel, rightModel]) => {
    if (!modelIds.includes(leftModel) || !modelIds.includes(rightModel)) throw new Error(`paired delta ${name} references an unknown model`);
    return [name, summarizeDelta(frozenPairs, leftModel, rightModel)];
  })));
  return Object.freeze({ models, pairedDeltas });
}

/** Preserves the original four-model evidence contract and delta names. */
export function summarizeExitV5FourWayPairs(pairs) {
  return summarizeExitV5Pairs(pairs, {
    modelIds: PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
    deltaPairs: Object.freeze([
      Object.freeze(['V4_MINUS_V3', 'V4', 'V3']),
      Object.freeze(['V5_UNCONDITIONAL_MINUS_V3', 'V5_UNCONDITIONAL', 'V3']),
      Object.freeze(['V5_UNCONDITIONAL_MINUS_V4', 'V5_UNCONDITIONAL', 'V4']),
      Object.freeze(['V5_CONDITIONAL_MINUS_V3', 'V5_CONDITIONAL', 'V3']),
      Object.freeze(['V5_CONDITIONAL_MINUS_V4', 'V5_CONDITIONAL', 'V4']),
      Object.freeze(['V5_CONDITIONAL_MINUS_V5_UNCONDITIONAL', 'V5_CONDITIONAL', 'V5_UNCONDITIONAL']),
    ]),
  });
}

function assertChronologicalEvaluationRows(rows) {
  let previous = -Infinity;
  for (const [index, row] of rows.entries()) {
    const at = isoMillis(row?.entryTimestamp, `evaluationRows[${index}].entryTimestamp`);
    if (at < previous) throw new Error('evaluationRows must be chronological');
    previous = at;
  }
}

export function runExitV5FourWayPairedEvaluation({
  evaluationRows,
  analogPool,
  fittedModels,
  splitName,
  pairedContract,
  roundTripCostPct = 0.05,
  incrementalCostPct = 0,
  evaluationHorizons = [1, 3, 6],
} = {}) {
  assertExitV5PairedSafety();
  assertFittedModels(fittedModels);
  if (!PHASE57_EXIT_V5_PAIRED_POLICY.evaluationSplits.includes(splitName)) throw new Error('splitName must be validation, oos, or prospective');
  if (!Array.isArray(evaluationRows) || evaluationRows.length === 0) throw new Error('evaluationRows must be non-empty');
  const contract = assertContract(pairedContract);
  const horizons = [...new Set(evaluationHorizons.filter((value) => Number.isInteger(value) && value > 0))].sort((a, b) => a - b);
  if (!horizons.length) throw new Error('evaluationHorizons must contain a positive integer');
  assertChronologicalEvaluationRows(evaluationRows);

  const pairs = [];
  const seenPairKeys = new Set();
  const developmentEndMs = isoMillis(fittedModels.developmentEnd, 'fittedModels.developmentEnd');
  for (const row of evaluationRows) {
    const validated = assertFrozenResearchRow(row);
    if (validated.entryTimestampMs <= developmentEndMs) throw new Error('evaluation Entry must be strictly after the frozen development boundary');
    const invariant = buildExitV5PairedInvariant({ row, pairedContract: contract, roundTripCostPct, incrementalCostPct });
    if (seenPairKeys.has(invariant.pairKey)) throw new Error(`duplicate paired evaluation key: ${invariant.pairKey}`);
    seenPairKeys.add(invariant.pairKey);

    const rawOutcomes = Object.freeze({
      V3: simulateP25ExitV3DualGate({ row, analogPool, roundTripCostPct: invariant.roundTripCostPct }),
      V4: simulateP25ExitV4({ row, analogPool, roundTripCostPct: invariant.roundTripCostPct }),
      V5_UNCONDITIONAL: simulateExitV5FrozenPolicy({
        row,
        fittedModel: fittedModels.unconditional,
        modelId: 'V5_UNCONDITIONAL',
        roundTripCostPct: invariant.roundTripCostPct,
        incrementalCostPct: invariant.incrementalCostPct,
      }),
      V5_CONDITIONAL: simulateExitV5FrozenPolicy({
        row,
        fittedModel: fittedModels.conditional,
        modelId: 'V5_CONDITIONAL',
        roundTripCostPct: invariant.roundTripCostPct,
        incrementalCostPct: invariant.incrementalCostPct,
      }),
    });
    const outcomes = Object.freeze(Object.fromEntries(PHASE57_EXIT_V5_PAIRED_MODEL_IDS.map((modelId) => [
      modelId,
      assertExitV5OutcomeUsesInvariant(rawOutcomes[modelId], validated.futureBars, invariant, modelId),
    ])));
    const evaluation = Object.freeze(Object.fromEntries(PHASE57_EXIT_V5_PAIRED_MODEL_IDS.map((modelId) => [
      modelId,
      evaluateExitV5OutcomeWindows({
        row,
        outcome: outcomes[modelId],
        futureBars: validated.futureBars,
        direction: validated.direction,
        horizons,
        roundTripCostPct: invariant.roundTripCostPct,
      }),
    ])));
    const calibration = Object.freeze({
      V3: Object.freeze([]),
      V4: Object.freeze([]),
      V5_UNCONDITIONAL: buildExitV5CalibrationRows(outcomes.V5_UNCONDITIONAL, validated.futureBars, validated.direction),
      V5_CONDITIONAL: buildExitV5CalibrationRows(outcomes.V5_CONDITIONAL, validated.futureBars, validated.direction),
    });
    pairs.push(Object.freeze({
      pairKey: invariant.pairKey,
      invariant,
      metadata: tradeMetadata(row, validated.direction),
      outcomes,
      evaluation,
      calibration,
    }));
  }

  const frozenPairs = Object.freeze(pairs);
  const summary = summarizeExitV5FourWayPairs(frozenPairs);

  return Object.freeze({
    phase: PHASE57_EXIT_V5_PAIRED_POLICY.phase,
    status: 'EXIT_V5_FOUR_WAY_PAIRED_EVALUATED',
    splitName,
    pairedCount: frozenPairs.length,
    comparisonModels: PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
    developmentFingerprint: fittedModels.developmentFingerprint,
    developmentRefitPerformed: false,
    pairedContract: contract,
    evaluationHorizons: Object.freeze(horizons),
    pairs: frozenPairs,
    summary,
    methodology: Object.freeze({
      exactSameFrozenInputForAllModels: true,
      marketDataFingerprintAsserted: true,
      transactionCostParityAsserted: true,
      capitalAllocationPolicyParityAsserted: true,
      evaluationLabelsUsedByDecision: false,
      developmentOnlyFit: true,
      boundaryPurgingConfirmed: true,
      sessionPurgingConfirmed: true,
      outerOosRetuning: false,
      prospectiveRetuning: false,
      resultBasedPromotion: false,
    }),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_EXIT_V5_PAIRED_SAFETY,
  });
}

export function assertExitV5PairedSafety() {
  assertExitV5ResearchSafety();
  for (const key of FALSE_SAFETY_KEYS) {
    if (PHASE57_EXIT_V5_PAIRED_SAFETY[key] !== false) throw new Error(`unsafe EXIT v5 paired flag: ${key}`);
  }
  if (PHASE57_EXIT_V5_PAIRED_SAFETY.researchOnly !== true) throw new Error('EXIT v5 paired evaluator must remain research-only');
  if (PHASE57_EXIT_V5_PAIRED_POLICY.evaluationLabelsUsedByDecision !== false) throw new Error('evaluation labels cannot be decision inputs');
  return true;
}

export default {
  PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  PHASE57_EXIT_V5_PAIRED_POLICY,
  PHASE57_EXIT_V5_PAIRED_SAFETY,
  assertExitV5PairedSafety,
  buildExitV5PairedInvariant,
  fitExitV5PairedDevelopmentModels,
  fitExitV5PairedModelsFromPurgedSplit,
  simulateExitV5FrozenPolicy,
  assertExitV5OutcomeUsesInvariant,
  evaluateExitV5OutcomeWindows,
  buildExitV5CalibrationRows,
  summarizeExitV5Pairs,
  summarizeExitV5FourWayPairs,
  runExitV5FourWayPairedEvaluation,
};
