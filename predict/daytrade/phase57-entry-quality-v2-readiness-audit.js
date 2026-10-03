import { createHash } from 'node:crypto';
import { PHASE57_ENTRY_QUALITY_V2_SAFETY } from './phase57-entry-quality-v2-research.js';

export const ENTRY_V2_READINESS_PHASE0_POLICY = Object.freeze({
  phase: '57.entry-quality-v2.dataset-readiness-phase0',
  modelFittingAllowed: false,
  performanceSelectionAllowed: false,
  sessionRegimeThresholds: Object.freeze({
    upReturnPct: 0.25,
    downReturnPct: -0.25,
    highCrossSectionalVolatilityPct: 3,
    lowCrossSectionalVolatilityPct: 1.5,
  }),
  dailyPriceBasis: Object.freeze({
    providerQuoteOhlcBasis: true,
    splitNormalization: 'PROVIDER_QUOTE_OHLC_EMPIRICALLY_SPLIT_NORMALIZED_DO_NOT_REAPPLY',
    splitEventRole: 'AUDIT_ONLY',
    volumeSemantics: 'NOT_INFERRED_FROM_SINGLE_SESSION_RATIOS;BLOCK_IF_SPLIT_WITHIN_VOLUME_FEATURE_WINDOW',
    dividendAdjustmentApplied: false,
    adjustedCloseUsedAsFeature: false,
    futureCorporateActionsMayAdjustPastFeatures: false,
  }),
  splitPolicy: Object.freeze({
    currentPoolRole: 'DEVELOPMENT_VALIDATION_DIAGNOSTIC_ONLY',
    groupedBySession: true,
    sameSessionMayCrossFold: false,
    minimumTrainingSessions: 6,
    validationBlockSessions: 2,
    embargoSessions: 1,
    untouchedOosPolicy: 'FIRST_THREE_ELIGIBLE_SESSIONS_AFTER_MODEL_AND_THRESHOLD_FREEZE',
    currentSessionsClaimedUntouchedOos: false,
    leaveOneSessionOutRole: 'SENSITIVITY_DIAGNOSTIC_ONLY',
  }),
});

export const ENTRY_V2_READINESS_PHASE0_SAFETY = Object.freeze({
  ...PHASE57_ENTRY_QUALITY_V2_SAFETY,
  phase: ENTRY_V2_READINESS_PHASE0_POLICY.phase,
  mode: 'READ_ONLY_OFFLINE_DATASET_AUDIT',
  researchOnly: true,
  prospective: false,
  formalOos: false,
  freshHoldoutConsumed: false,
});

const FALSE_KEYS = Object.freeze([
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed',
  'productionUpdateAllowed', 'transmitted',
]);

function assertSafe() {
  for (const key of FALSE_KEYS) {
    if (ENTRY_V2_READINESS_PHASE0_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_READINESS_PHASE0_UNSAFE_${key}`);
    }
  }
}

export const sha256 = value => createHash('sha256')
  .update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value))
  .digest('hex');

export function quantile(values = [], probability = 0.5) {
  const sorted = values.map(Number).filter(Number.isFinite).sort((left, right) => left - right);
  if (!sorted.length) return null;
  const position = Math.max(0, Math.min(1, Number(probability))) * (sorted.length - 1);
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

export function summarize(values = []) {
  const finite = values.map(Number).filter(Number.isFinite);
  if (!finite.length) return Object.freeze({ count: 0, mean: null, variance: null, median: null, p95: null, min: null, max: null });
  const mean = finite.reduce((sum, value) => sum + value, 0) / finite.length;
  const variance = finite.length > 1
    ? finite.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / (finite.length - 1)
    : 0;
  return Object.freeze({
    count: finite.length,
    mean,
    variance,
    median: quantile(finite, 0.5),
    p95: quantile(finite, 0.95),
    min: Math.min(...finite),
    max: Math.max(...finite),
  });
}

export function oneWayClusterAudit(rows = [], { clusterKey, valueKey } = {}) {
  assertSafe();
  const groups = new Map();
  for (const row of rows) {
    const cluster = String(row?.[clusterKey] ?? '');
    const value = Number(row?.[valueKey]);
    if (!cluster || !Number.isFinite(value)) continue;
    if (!groups.has(cluster)) groups.set(cluster, []);
    groups.get(cluster).push(value);
  }
  const clusters = [...groups.entries()].map(([cluster, values]) => ({ cluster, values, n: values.length, mean: summarize(values).mean }));
  const all = clusters.flatMap(group => group.values);
  const n = all.length;
  const k = clusters.length;
  const grandMean = summarize(all).mean;
  if (n <= k || k < 2) {
    return Object.freeze({ nominalN: n, clusterCount: k, averageClusterSize: k ? n / k : null, icc: null, designEffect: null, approximateEffectiveN: null });
  }
  const betweenSumSquares = clusters.reduce((sum, group) => sum + group.n * ((group.mean - grandMean) ** 2), 0);
  const withinSumSquares = clusters.reduce((sum, group) => sum
    + group.values.reduce((inner, value) => inner + ((value - group.mean) ** 2), 0), 0);
  const betweenMeanSquare = betweenSumSquares / (k - 1);
  const withinMeanSquare = withinSumSquares / (n - k);
  const effectiveClusterSize = (n - (clusters.reduce((sum, group) => sum + (group.n ** 2), 0) / n)) / (k - 1);
  const denominator = betweenMeanSquare + ((effectiveClusterSize - 1) * withinMeanSquare);
  const icc = denominator === 0 ? 0 : (betweenMeanSquare - withinMeanSquare) / denominator;
  const nonNegativeIccForDesign = Math.max(0, icc);
  const averageClusterSize = n / k;
  const designEffect = 1 + ((averageClusterSize - 1) * nonNegativeIccForDesign);
  return Object.freeze({
    methodology: 'ONE_WAY_RANDOM_EFFECTS_ICC1_UNBALANCED;NEGATIVE_ICC_REPORTED_BUT_CLAMPED_TO_ZERO_FOR_DESIGN_EFFECT',
    nominalN: n,
    clusterCount: k,
    averageClusterSize,
    minimumClusterSize: Math.min(...clusters.map(group => group.n)),
    maximumClusterSize: Math.max(...clusters.map(group => group.n)),
    grandMean,
    betweenClusterVarianceComponent: Math.max(0, (betweenMeanSquare - withinMeanSquare) / effectiveClusterSize),
    withinClusterVariance: withinMeanSquare,
    betweenMeanSquare,
    withinMeanSquare,
    effectiveClusterSize,
    icc,
    designEffect,
    approximateEffectiveN: n / designEffect,
  });
}

export function candidateDirectionalLabel(candidate, horizonBars, metric) {
  const label = (candidate?.qualityLabels ?? []).find(row => Number(row.horizonBars) === Number(horizonBars));
  if (!label?.complete) return null;
  const direction = String(candidate?.direction ?? '').toLowerCase();
  const value = Number(label?.[direction]?.[metric]);
  return Number.isFinite(value) ? value : null;
}

export function jstTimeBucket(timestamp) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  const minuteOfDay = Number(parts.hour) * 60 + Number(parts.minute);
  if (minuteOfDay < 600) return '09:00-09:59';
  if (minuteOfDay < 690) return '10:00-11:29';
  if (minuteOfDay < 810) return '12:30-13:29';
  if (minuteOfDay < 870) return '13:30-14:29';
  return '14:30-15:30';
}

export function buildLabelMissingnessAudit(candidates = [], horizons = [1, 3, 6, 12]) {
  const buckets = {};
  for (const candidate of candidates) {
    const bucket = jstTimeBucket(candidate.entryTimestamp);
    buckets[bucket] ??= { candidateCount: 0, horizons: {} };
    buckets[bucket].candidateCount += 1;
    for (const horizon of horizons) {
      buckets[bucket].horizons[horizon] ??= { complete: 0, incomplete: 0, coverage: null };
      buckets[bucket].horizons[horizon][candidate.labelCompleteness?.[horizon] === true ? 'complete' : 'incomplete'] += 1;
    }
  }
  for (const bucket of Object.values(buckets)) {
    for (const stats of Object.values(bucket.horizons)) stats.coverage = stats.complete / bucket.candidateCount;
  }
  return Object.freeze({
    mechanism: 'STRUCTURAL_SAME_SESSION_RIGHT_CENSORING;LIKELY_MNAR_BY_TIME_OF_DAY',
    labelsImputed: false,
    byTimeOfDay: Object.freeze(Object.fromEntries(Object.entries(buckets).sort())),
  });
}

export function applyDailyPriceBasisPolicy(records = [], splitEvents = [], decisionSessionDate) {
  assertSafe();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(decisionSessionDate))) {
    throw new Error('ENTRY_V2_DAILY_PRICE_BASIS_DECISION_SESSION_REQUIRED');
  }
  const futureSplitCount = splitEvents.filter(event => event.sessionDate > decisionSessionDate).length;
  return Object.freeze({
    records: Object.freeze(records.map(record => Object.freeze({
      ...record,
      open: Number(record.open), high: Number(record.high), low: Number(record.low), close: Number(record.close), volume: Number(record.volume),
    }))),
    policy: ENTRY_V2_READINESS_PHASE0_POLICY.dailyPriceBasis,
    lineage: Object.freeze({
      decisionSessionDate,
      splitEventsKnownByDecision: splitEvents.filter(event => event.sessionDate <= decisionSessionDate).length,
      futureSplitEventsExcludedFromFeatureTransformation: futureSplitCount,
      providerQuoteOhlcReAdjusted: false,
      adjustedCloseUsedAsFeature: false,
    }),
  });
}

export function buildGroupedWalkForwardPrecommit(sessionDates = []) {
  const sessions = [...new Set(sessionDates)].sort();
  const { minimumTrainingSessions, validationBlockSessions, embargoSessions } = ENTRY_V2_READINESS_PHASE0_POLICY.splitPolicy;
  const folds = [];
  for (let validationStart = minimumTrainingSessions + embargoSessions;
    validationStart + validationBlockSessions <= sessions.length;
    validationStart += validationBlockSessions) {
    folds.push(Object.freeze({
      trainingSessions: Object.freeze(sessions.slice(0, validationStart - embargoSessions)),
      embargoSessions: Object.freeze(sessions.slice(validationStart - embargoSessions, validationStart)),
      validationSessions: Object.freeze(sessions.slice(validationStart, validationStart + validationBlockSessions)),
    }));
  }
  return Object.freeze({ ...ENTRY_V2_READINESS_PHASE0_POLICY.splitPolicy, availableSessionCount: sessions.length, folds: Object.freeze(folds) });
}

export default {
  ENTRY_V2_READINESS_PHASE0_POLICY,
  ENTRY_V2_READINESS_PHASE0_SAFETY,
  quantile,
  summarize,
  oneWayClusterAudit,
  candidateDirectionalLabel,
  jstTimeBucket,
  buildLabelMissingnessAudit,
  applyDailyPriceBasisPolicy,
  buildGroupedWalkForwardPrecommit,
};
