import { DEFAULT_DYNAMIC_EXIT_CONFIG, simulateDynamicTradeManagement } from './phase57-dynamic-trade-management.js';
import { simulateIntradayExit } from './phase57-exit-optimization.js';

export const PHASE57_P23_3_SAFETY = Object.freeze({
  mode: 'PHASE57_REAL_DYNAMIC_EXIT_OOS_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  humanApprovalRequired: true,
});

// This is frozen before real OOS measurement. 1000 bars is intentionally non-binding;
// the same-session path, not elapsed time, ends a healthy trend at the session boundary.
export const P23_3_FROZEN_DYNAMIC_CONFIG = Object.freeze({
  ...DEFAULT_DYNAMIC_EXIT_CONFIG,
  maxHoldBars: 1000,
  roundTripCostPct: 0.05,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function jstDate(timestamp) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function normalizePath(rows = []) {
  return (Array.isArray(rows) ? rows : []).map(raw => ({
    timestamp: new Date(raw?.timestamp ?? raw?.time ?? raw?.datetime).toISOString(),
    open: Number(raw?.open), high: Number(raw?.high), low: Number(raw?.low), close: Number(raw?.close),
    volume: finite(raw?.volume) ? Number(raw.volume) : 0,
  })).filter(bar => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function directionSign(direction) {
  if (direction === 1 || direction === 'LONG') return 1;
  if (direction === 0 || direction === -1 || direction === 'SHORT') return -1;
  return null;
}

function directionalReturnPct(entry, price, sign) {
  return (Number(price) / Number(entry) - 1) * 100 * sign;
}

function fullPathOpportunity(row, dynamicOutcome) {
  const sign = directionSign(row.signalDirection);
  const entry = Number(row.entryPrice);
  const path = normalizePath(row.futureBars ?? row.path ?? []);
  if (!sign || !finite(entry) || entry <= 0 || !path.length) return Object.freeze({
    fullPathMfePct: null,
    fullPathMaePct: null,
    fullPathCaptureRatio: null,
  });
  const favorable = sign === 1 ? Math.max(...path.map(bar => bar.high)) : Math.min(...path.map(bar => bar.low));
  const adverse = sign === 1 ? Math.min(...path.map(bar => bar.low)) : Math.max(...path.map(bar => bar.high));
  const fullPathMfePct = Math.max(0, directionalReturnPct(entry, favorable, sign));
  const fullPathMaePct = Math.min(0, directionalReturnPct(entry, adverse, sign));
  const fullPathCaptureRatio = fullPathMfePct > 0 && finite(dynamicOutcome?.grossReturnPct)
    ? clamp(Number(dynamicOutcome.grossReturnPct) / fullPathMfePct, -5, 5)
    : null;
  return Object.freeze({ fullPathMfePct, fullPathMaePct, fullPathCaptureRatio });
}

function sequentialSignalDrawdownPct(outcomes = []) {
  let equity = 0;
  let peak = 0;
  let maxDrawdown = 0;
  for (const outcome of outcomes) {
    equity += Number(outcome?.netReturnPct || 0);
    peak = Math.max(peak, equity);
    maxDrawdown = Math.max(maxDrawdown, peak - equity);
  }
  return maxDrawdown;
}

function summarizeOutcomes(outcomes = [], { includeFullPathCapture = false } = {}) {
  const rows = Array.isArray(outcomes) ? outcomes : [];
  const n = rows.length;
  const positive = rows.filter(row => Number(row.netReturnPct) > 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const negative = -rows.filter(row => Number(row.netReturnPct) < 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const capture = rows.map(row => Number(row.captureRatio)).filter(Number.isFinite);
  const fullPathCapture = rows.map(row => Number(row.fullPathCaptureRatio)).filter(Number.isFinite);
  const exitReasonCounts = {};
  for (const row of rows) {
    if (row.exitReason) exitReasonCounts[row.exitReason] = (exitReasonCounts[row.exitReason] || 0) + 1;
  }
  return Object.freeze({
    signalCount: n,
    hitRate: n ? rows.filter(row => Number(row.netReturnPct) > 0).length / n : null,
    netAverageReturnPct: n ? mean(rows.map(row => Number(row.netReturnPct))) : null,
    grossAverageReturnPct: n ? mean(rows.map(row => Number(row.grossReturnPct))) : null,
    medianNetReturnPct: n ? median(rows.map(row => Number(row.netReturnPct))) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: n ? mean(rows.map(row => Number(row.barsHeld))) : null,
    averageHoldingMinutes: n ? mean(rows.map(row => Number(row.barsHeld) * 5)) : null,
    averageMfePct: n ? mean(rows.map(row => Number(row.mfePct)).filter(Number.isFinite)) : null,
    averageMaePct: n ? mean(rows.map(row => Number(row.maePct)).filter(Number.isFinite)) : null,
    averageCaptureRatio: capture.length ? mean(capture) : null,
    averageFullPathCaptureRatio: includeFullPathCapture && fullPathCapture.length ? mean(fullPathCapture) : null,
    maxSequentialSignalDrawdownPct: n ? sequentialSignalDrawdownPct(rows) : null,
    exitReasonCounts: Object.freeze(exitReasonCounts),
  });
}

function validResearchRow(row) {
  if (!row?.symbol || !row?.sessionDate || !row?.featureCutoff) return false;
  if (!finite(row?.entryPrice) || Number(row.entryPrice) <= 0) return false;
  if (directionSign(row?.signalDirection) === null) return false;
  if (!Number.isInteger(Number(row?.baseHorizonBars)) || Number(row.baseHorizonBars) <= 0) return false;
  if (row?.signalPointInTimeValid === false || row?.pointInTimeValid === false) return false;
  const context = normalizePath(row?.contextBars ?? []);
  const future = normalizePath(row?.futureBars ?? row?.path ?? []);
  if (!future.length) return false;
  if (context.length && Date.parse(context.at(-1).timestamp) >= Date.parse(future[0].timestamp)) return false;
  if (future.some(bar => jstDate(bar.timestamp) !== String(row.sessionDate))) return false;
  return true;
}

function pairRow(row, dynamicConfig, roundTripCostPct) {
  const dynamic = simulateDynamicTradeManagement({ ...row, sessionDate: String(row.sessionDate) }, { ...dynamicConfig, roundTripCostPct });
  const baselinePolicy = Object.freeze({
    id: `MATCHED_FIXED_${Number(row.baseHorizonBars) * 5}M`,
    type: 'FIXED',
    maxBars: Number(row.baseHorizonBars),
  });
  const baseline = simulateIntradayExit(row, baselinePolicy, { roundTripCostPct });
  if (!dynamic || !baseline) return null;
  const opportunity = fullPathOpportunity(row, dynamic);
  const pairId = String(row?.id ?? `${row.symbol}|${row.sessionDate}|${row.featureCutoff}|${row.baseHorizonBars}`);
  return Object.freeze({
    pairId,
    symbol: String(row.symbol),
    sessionDate: String(row.sessionDate),
    featureCutoff: new Date(row.featureCutoff).toISOString(),
    baseOuterFold: Number.isInteger(Number(row?.baseOuterFold)) ? Number(row.baseOuterFold) : null,
    baseHorizonBars: Number(row.baseHorizonBars),
    baseHorizonMinutes: Number(row.baseHorizonBars) * 5,
    dynamic: Object.freeze({
      netReturnPct: dynamic.netReturnPct,
      grossReturnPct: dynamic.grossReturnPct,
      barsHeld: dynamic.barsHeld,
      mfePct: dynamic.mfePct,
      maePct: dynamic.maePct,
      captureRatio: dynamic.captureRatio,
      exitReason: dynamic.exitReason,
      outcomeAt: dynamic.outcomeAt,
      ...opportunity,
    }),
    matchedFixedBaseline: Object.freeze({
      netReturnPct: baseline.netReturnPct,
      grossReturnPct: baseline.grossReturnPct,
      barsHeld: baseline.barsHeld,
      mfePct: baseline.mfePct,
      maePct: baseline.maePct,
      captureRatio: baseline.captureRatio,
      exitReason: baseline.exitReason,
      outcomeAt: baseline.outcomeAt,
    }),
    deltaNetReturnPct: Number(dynamic.netReturnPct) - Number(baseline.netReturnPct),
    deltaHoldingBars: Number(dynamic.barsHeld) - Number(baseline.barsHeld),
    dynamicDecisionUsesFutureBars: false,
  });
}

function foldSummaries(pairs = []) {
  const folds = new Map();
  for (const pair of pairs) {
    const key = pair.baseOuterFold === null ? 'UNKNOWN' : String(pair.baseOuterFold);
    if (!folds.has(key)) folds.set(key, []);
    folds.get(key).push(pair);
  }
  return Object.freeze([...folds.entries()].sort(([a], [b]) => Number(a) - Number(b)).map(([fold, rows]) => {
    const dynamic = summarizeOutcomes(rows.map(row => ({ ...row.dynamic })), { includeFullPathCapture: true });
    const baseline = summarizeOutcomes(rows.map(row => ({ ...row.matchedFixedBaseline })));
    return Object.freeze({
      fold: fold === 'UNKNOWN' ? null : Number(fold),
      signalCount: rows.length,
      dynamic,
      matchedFixedBaseline: baseline,
      deltaNetAverageReturnPct: finite(dynamic.netAverageReturnPct) && finite(baseline.netAverageReturnPct)
        ? Number(dynamic.netAverageReturnPct) - Number(baseline.netAverageReturnPct)
        : null,
      outerOutcomesUsedForConfigSelection: false,
    });
  }));
}

export function evaluateRealDynamicExitOos(rows = [], options = {}) {
  const roundTripCostPct = Math.max(0, Number(options?.roundTripCostPct ?? 0.05));
  const dynamicConfig = Object.freeze({
    ...P23_3_FROZEN_DYNAMIC_CONFIG,
    ...(options?.dynamicConfig ?? {}),
    roundTripCostPct,
  });
  if (options?.allowOuterOosConfigSelection === true) throw new Error('P23.3 forbids outer-OOS exit configuration selection');

  const input = Array.isArray(rows) ? rows : [];
  const valid = input.filter(validResearchRow).sort((a, b) => String(a.featureCutoff).localeCompare(String(b.featureCutoff)));
  const pairs = valid.map(row => pairRow(row, dynamicConfig, roundTripCostPct)).filter(Boolean);
  const dynamicOutcomes = pairs.map(pair => ({ ...pair.dynamic }));
  const baselineOutcomes = pairs.map(pair => ({ ...pair.matchedFixedBaseline }));
  const dynamic = summarizeOutcomes(dynamicOutcomes, { includeFullPathCapture: true });
  const matchedFixedBaseline = summarizeOutcomes(baselineOutcomes);
  const folds = foldSummaries(pairs);
  const signalBearingFolds = folds.filter(fold => fold.signalCount > 0);
  const dynamicPositiveFoldFraction = signalBearingFolds.length
    ? signalBearingFolds.filter(fold => Number(fold.dynamic.netAverageReturnPct) > 0).length / signalBearingFolds.length
    : null;
  const dynamicBetterFoldFraction = signalBearingFolds.length
    ? signalBearingFolds.filter(fold => Number(fold.deltaNetAverageReturnPct) > 0).length / signalBearingFolds.length
    : null;

  return Object.freeze({
    phase: '57.p23.3-real-dynamic-exit-oos',
    status: pairs.length ? 'REAL_DYNAMIC_EXIT_OOS_EVALUATED' : 'NO_REAL_DYNAMIC_EXIT_PAIRS',
    inputRowCount: input.length,
    validResearchRowCount: valid.length,
    rejectedRowCount: input.length - valid.length,
    pairedSignalCount: pairs.length,
    dynamic,
    matchedFixedBaseline,
    deltaMatchedNetAverageReturnPct: finite(dynamic.netAverageReturnPct) && finite(matchedFixedBaseline.netAverageReturnPct)
      ? Number(dynamic.netAverageReturnPct) - Number(matchedFixedBaseline.netAverageReturnPct)
      : null,
    deltaAverageHoldingBars: finite(dynamic.averageHoldingBars) && finite(matchedFixedBaseline.averageHoldingBars)
      ? Number(dynamic.averageHoldingBars) - Number(matchedFixedBaseline.averageHoldingBars)
      : null,
    foldResults: folds,
    dynamicPositiveFoldFraction,
    dynamicBetterThanBaselineFoldFraction: dynamicBetterFoldFraction,
    frozenDynamicConfig: dynamicConfig,
    selectionIntegrity: Object.freeze({
      entrySignalsArePriorOuterOos: true,
      dynamicExitConfigFrozenBeforeThisOuterEvaluation: true,
      outerOosUsedForDynamicExitConfigSelection: false,
      matchedBaselineUsesExactSameSignalRows: pairs.length === valid.length,
      fixedHorizonBaselineUsesPriorEntrySignalHorizon: true,
      sessionPathEndsHealthyTrendInsteadOfElapsedTime: true,
      fullPathMfeUsedForEvaluationOnly: true,
      postSelectionAcrossExitVariantsAllowed: false,
    }),
    interpretation: Object.freeze({
      primaryObjective: 'NET_EXPECTANCY_AFTER_EXPLICIT_COST',
      dynamicExitIsPrimaryResearchExit: true,
      fixedElapsedTimeIsBaselineOnly: true,
      maxHoldIsNonBindingSameSessionSafetyGuard: dynamicConfig.maxHoldBars >= 1000,
      singleRecentWindowEdgeClaimAllowed: false,
    }),
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_3_SAFETY,
  });
}

export default { P23_3_FROZEN_DYNAMIC_CONFIG, evaluateRealDynamicExitOos };
