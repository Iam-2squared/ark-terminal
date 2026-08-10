export const PHASE57_P23_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_HISTORICAL_ANALOG_READ_ONLY_RESEARCH',
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

export const P23_DEFAULT_FEATURE_KEYS = Object.freeze([
  'ma5Distance',
  'ma10Distance',
  'ma20Distance',
  'ma5Slope',
  'rsi14',
  'macdSignalGap',
  'atrPct',
  'vwapDistance',
  'bollingerPosition',
  'relativeVolume20',
  'rangePosition20',
  'minutesFromOpen',
  'minutesToClose',
  'spreadBps',
  'topBookImbalance',
  'depthImbalance',
  'weightedDepthImbalance',
  'micropriceEdgeBps',
  'signedVolumeImbalance',
  'tradeIntensityPerSecond',
  'quoteUpdateRatePerSecond',
  'spreadChangeBps',
  'classifiedTickFraction',
]);

export const P23_MOVE_THRESHOLDS_PCT = Object.freeze([0.5, 1, 2, 3]);

const FORBIDDEN_FEATURE_PATTERN = /(future|outcome|label|target|actualreturn|netreturn|grossreturn|mfe|mae|profit|pnl|direction)/i;
const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function quantile(values, q) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  if (sorted.length === 1) return sorted[0];
  const position = clamp(Number(q), 0, 1) * (sorted.length - 1);
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  const weight = position - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function stddev(values) {
  if (values.length < 2) return 0;
  const m = mean(values);
  const variance = mean(values.map(value => (value - m) ** 2));
  return Math.sqrt(Math.max(0, variance));
}

function parseTime(value, field) {
  const parsed = Date.parse(value ?? '');
  if (!Number.isFinite(parsed)) throw new TypeError(`${field} must be a valid absolute timestamp`);
  return parsed;
}

function sessionDate(value, field = 'sessionDate') {
  const text = String(value ?? '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) throw new TypeError(`${field} must be YYYY-MM-DD`);
  return text;
}

function normalizeFeatureKeys(featureKeys) {
  const keys = [...new Set((Array.isArray(featureKeys) ? featureKeys : P23_DEFAULT_FEATURE_KEYS)
    .map(key => String(key ?? '').trim())
    .filter(Boolean))];
  if (!keys.length) throw new TypeError('featureKeys must contain at least one feature');
  for (const key of keys) {
    if (FORBIDDEN_FEATURE_PATTERN.test(key)) throw new Error(`outcome-derived feature is forbidden in P23 similarity: ${key}`);
  }
  return Object.freeze(keys);
}

function normalizeFeatures(features, featureKeys) {
  const source = features && typeof features === 'object' && !Array.isArray(features) ? features : {};
  return Object.freeze(Object.fromEntries(featureKeys.map(key => [key, finite(source[key]) ? Number(source[key]) : null])));
}

function normalizeContext(context = {}) {
  return Object.freeze({
    timeBucket: context?.timeBucket == null ? null : String(context.timeBucket),
    regime: context?.regime == null ? null : String(context.regime),
  });
}

function normalizeQuery(query, featureKeys) {
  if (!query || typeof query !== 'object') throw new TypeError('query is required');
  const asOfMs = parseTime(query.asOf ?? query.featureCutoff, 'query.asOf');
  const cutoffMs = parseTime(query.featureCutoff ?? query.asOf, 'query.featureCutoff');
  if (cutoffMs > asOfMs) throw new Error('query.featureCutoff cannot be after query.asOf');
  const currentSession = sessionDate(query.sessionDate, 'query.sessionDate');
  const horizonBars = Number(query.horizonBars);
  if (!Number.isInteger(horizonBars) || horizonBars <= 0) throw new TypeError('query.horizonBars must be a positive integer');
  return Object.freeze({
    symbol: String(query.symbol ?? '').trim() || null,
    sessionDate: currentSession,
    asOf: new Date(asOfMs).toISOString(),
    asOfMs,
    featureCutoff: new Date(cutoffMs).toISOString(),
    featureCutoffMs: cutoffMs,
    horizonBars,
    features: normalizeFeatures(query.features, featureKeys),
    context: normalizeContext(query.context),
  });
}

function normalizeCandidate(row, featureKeys) {
  if (!row || typeof row !== 'object') return null;
  try {
    const featureCutoffMs = parseTime(row.featureCutoff, 'candidate.featureCutoff');
    const outcomeAtMs = parseTime(row.outcomeAt, 'candidate.outcomeAt');
    const candidateSession = sessionDate(row.sessionDate, 'candidate.sessionDate');
    const outcomeSession = sessionDate(row.outcomeSessionDate ?? row.sessionDate, 'candidate.outcomeSessionDate');
    const horizonBars = Number(row.horizonBars);
    if (!Number.isInteger(horizonBars) || horizonBars <= 0) return null;
    if (featureCutoffMs >= outcomeAtMs) return null;
    if (candidateSession !== outcomeSession) return null;
    if (!finite(row.actualReturnPct)) return null;
    const actualReturnPct = Number(row.actualReturnPct);
    return Object.freeze({
      id: String(row.id ?? `${row.symbol ?? 'UNKNOWN'}|${candidateSession}|${new Date(featureCutoffMs).toISOString()}|${horizonBars}`),
      symbol: String(row.symbol ?? '').trim() || null,
      sessionDate: candidateSession,
      outcomeSessionDate: outcomeSession,
      featureCutoff: new Date(featureCutoffMs).toISOString(),
      featureCutoffMs,
      outcomeAt: new Date(outcomeAtMs).toISOString(),
      outcomeAtMs,
      horizonBars,
      features: normalizeFeatures(row.features, featureKeys),
      context: normalizeContext(row.context),
      actualReturnPct,
      absMovePct: finite(row.absMovePct) ? Math.abs(Number(row.absMovePct)) : Math.abs(actualReturnPct),
      mfePct: finite(row.mfePct) ? Number(row.mfePct) : null,
      maePct: finite(row.maePct) ? Number(row.maePct) : null,
      pointInTimeValid: row.pointInTimeValid !== false,
      intradayOnly: row.intradayOnly !== false,
    });
  } catch {
    return null;
  }
}

export function selectCausalAnalogPool({
  query,
  candidates = [],
  featureKeys = P23_DEFAULT_FEATURE_KEYS,
  excludeCurrentSession = true,
  sameSymbolOnly = false,
} = {}) {
  const keys = normalizeFeatureKeys(featureKeys);
  const current = normalizeQuery(query, keys);
  const accepted = [];
  const rejected = {
    invalid: 0,
    futureOutcome: 0,
    currentSession: 0,
    horizonMismatch: 0,
    symbolMismatch: 0,
    nonIntraday: 0,
    nonPointInTime: 0,
  };

  for (const raw of Array.isArray(candidates) ? candidates : []) {
    const candidate = normalizeCandidate(raw, keys);
    if (!candidate) {
      rejected.invalid += 1;
      continue;
    }
    if (!candidate.pointInTimeValid) {
      rejected.nonPointInTime += 1;
      continue;
    }
    if (!candidate.intradayOnly || candidate.sessionDate !== candidate.outcomeSessionDate) {
      rejected.nonIntraday += 1;
      continue;
    }
    if (candidate.horizonBars !== current.horizonBars) {
      rejected.horizonMismatch += 1;
      continue;
    }
    if (candidate.outcomeAtMs > current.featureCutoffMs) {
      rejected.futureOutcome += 1;
      continue;
    }
    if (excludeCurrentSession && candidate.sessionDate === current.sessionDate) {
      rejected.currentSession += 1;
      continue;
    }
    if (sameSymbolOnly && current.symbol && candidate.symbol !== current.symbol) {
      rejected.symbolMismatch += 1;
      continue;
    }
    accepted.push(candidate);
  }

  accepted.sort((a, b) => a.featureCutoffMs - b.featureCutoffMs || a.id.localeCompare(b.id));
  return Object.freeze({
    phase: '57.p23',
    query: current,
    featureKeys: keys,
    causalCandidates: Object.freeze(accepted),
    causalCandidateCount: accepted.length,
    rejected: Object.freeze(rejected),
    candidateOutcomesFullyRealizedBeforeQuery: accepted.every(row => row.outcomeAtMs <= current.featureCutoffMs),
    currentSessionExcluded: Boolean(excludeCurrentSession),
    sameSymbolOnly: Boolean(sameSymbolOnly),
    pointInTime: true,
    intradayOnly: true,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_SAFETY,
  });
}

export function fitCausalRobustScaler(candidates = [], featureKeys = P23_DEFAULT_FEATURE_KEYS) {
  const keys = normalizeFeatureKeys(featureKeys);
  const scaler = {};
  for (const key of keys) {
    const values = candidates.map(row => row?.features?.[key]).filter(finite).map(Number);
    const med = median(values);
    const q1 = quantile(values, 0.25);
    const q3 = quantile(values, 0.75);
    const iqr = finite(q1) && finite(q3) ? Number(q3) - Number(q1) : 0;
    const fallback = stddev(values);
    const scale = iqr > 1e-12 ? iqr : fallback > 1e-12 ? fallback : 1;
    scaler[key] = Object.freeze({ median: med ?? 0, scale, sampleCount: values.length });
  }
  return Object.freeze(scaler);
}

function analogDistance(query, candidate, scaler, featureKeys, featureWeights, minFeatureFraction, contextPenalties) {
  let weightedSquared = 0;
  let totalWeight = 0;
  let usedFeatures = 0;
  for (const key of featureKeys) {
    const q = query.features[key];
    const c = candidate.features[key];
    if (!finite(q) || !finite(c)) continue;
    const scale = Math.max(1e-12, Number(scaler[key]?.scale ?? 1));
    const weight = finite(featureWeights?.[key]) ? Math.max(0, Number(featureWeights[key])) : 1;
    if (weight === 0) continue;
    const delta = (Number(q) - Number(c)) / scale;
    weightedSquared += weight * delta * delta;
    totalWeight += weight;
    usedFeatures += 1;
  }
  const coverage = featureKeys.length ? usedFeatures / featureKeys.length : 0;
  if (coverage < minFeatureFraction || totalWeight <= 0) return null;
  let distance = Math.sqrt(weightedSquared / totalWeight);
  for (const [key, penalty] of Object.entries(contextPenalties)) {
    const q = query.context?.[key];
    const c = candidate.context?.[key];
    if (q != null && c != null && q !== c) distance += Math.max(0, Number(penalty) || 0);
  }
  return Object.freeze({ distance, coverage, usedFeatures });
}

function weightedMean(rows, selector) {
  let numerator = 0;
  let denominator = 0;
  for (const row of rows) {
    const value = selector(row);
    if (!finite(value) || !finite(row.similarityWeight) || row.similarityWeight <= 0) continue;
    numerator += Number(value) * row.similarityWeight;
    denominator += row.similarityWeight;
  }
  return denominator > 0 ? numerator / denominator : null;
}

function weightedRate(rows, predicate) {
  let numerator = 0;
  let denominator = 0;
  for (const row of rows) {
    const weight = Number(row.similarityWeight);
    if (!Number.isFinite(weight) || weight <= 0) continue;
    denominator += weight;
    if (predicate(row)) numerator += weight;
  }
  return denominator > 0 ? numerator / denominator : null;
}

function effectiveSampleSize(rows) {
  const weights = rows.map(row => Number(row.similarityWeight)).filter(weight => Number.isFinite(weight) && weight > 0);
  const sum = weights.reduce((total, weight) => total + weight, 0);
  const sumSquares = weights.reduce((total, weight) => total + weight * weight, 0);
  return sumSquares > 0 ? sum * sum / sumSquares : 0;
}

export function summarizeIntradayAnalogs(analogs = [], { roundTripCostPct = 0.05 } = {}) {
  const rows = Array.isArray(analogs) ? analogs : [];
  const cost = Math.max(0, Number(roundTripCostPct) || 0);
  const weightedReturn = weightedMean(rows, row => row.actualReturnPct);
  const weightedAbsMove = weightedMean(rows, row => row.absMovePct);
  const weightedMfe = weightedMean(rows, row => row.mfePct);
  const weightedMae = weightedMean(rows, row => row.maePct);
  const moveProbabilityByThresholdPct = Object.fromEntries(P23_MOVE_THRESHOLDS_PCT.map(threshold => [
    String(threshold),
    weightedRate(rows, row => Number(row.absMovePct) >= threshold),
  ]));
  const similarities = rows.map(row => Number(row.similarityWeight)).filter(Number.isFinite);
  const netLong = weightedReturn === null ? null : weightedReturn - cost;
  const netShort = weightedReturn === null ? null : -weightedReturn - cost;
  return Object.freeze({
    sampleCount: rows.length,
    effectiveSampleSize: effectiveSampleSize(rows),
    averageSimilarity: mean(similarities),
    weightedUpRate: weightedRate(rows, row => Number(row.actualReturnPct) > 0),
    weightedDownRate: weightedRate(rows, row => Number(row.actualReturnPct) < 0),
    weightedMeanReturnPct: weightedReturn,
    medianReturnPct: median(rows.map(row => Number(row.actualReturnPct)).filter(Number.isFinite)),
    weightedMeanAbsMovePct: weightedAbsMove,
    weightedMeanMfePct: weightedMfe,
    weightedMeanMaePct: weightedMae,
    expectedNetLongReturnPctAfterCost: netLong,
    expectedNetShortReturnPctAfterCost: netShort,
    roundTripCostPct: cost,
    moveProbabilityByThresholdPct: Object.freeze(moveProbabilityByThresholdPct),
  });
}

export function findIntradayHistoricalAnalogs({
  query,
  candidates = [],
  featureKeys = P23_DEFAULT_FEATURE_KEYS,
  featureWeights = {},
  topK = 20,
  minimumAnalogs = 10,
  minFeatureFraction = 0.5,
  excludeCurrentSession = true,
  sameSymbolOnly = false,
  contextPenalties = { timeBucket: 0.35, regime: 0.25 },
  roundTripCostPct = 0.05,
} = {}) {
  const pool = selectCausalAnalogPool({ query, candidates, featureKeys, excludeCurrentSession, sameSymbolOnly });
  const scaler = fitCausalRobustScaler(pool.causalCandidates, pool.featureKeys);
  const scored = [];
  for (const candidate of pool.causalCandidates) {
    const match = analogDistance(
      pool.query,
      candidate,
      scaler,
      pool.featureKeys,
      featureWeights,
      clamp(Number(minFeatureFraction) || 0, 0, 1),
      contextPenalties && typeof contextPenalties === 'object' ? contextPenalties : {},
    );
    if (!match) continue;
    const similarityWeight = 1 / (1 + match.distance);
    scored.push(Object.freeze({
      id: candidate.id,
      symbol: candidate.symbol,
      sessionDate: candidate.sessionDate,
      featureCutoff: candidate.featureCutoff,
      outcomeAt: candidate.outcomeAt,
      horizonBars: candidate.horizonBars,
      distance: match.distance,
      similarityWeight,
      featureCoverage: match.coverage,
      usedFeatureCount: match.usedFeatures,
      context: candidate.context,
      actualReturnPct: candidate.actualReturnPct,
      absMovePct: candidate.absMovePct,
      mfePct: candidate.mfePct,
      maePct: candidate.maePct,
    }));
  }
  scored.sort((a, b) => a.distance - b.distance || b.featureCoverage - a.featureCoverage || a.id.localeCompare(b.id));
  const limit = Math.max(1, Math.floor(Number(topK) || 20));
  const analogs = Object.freeze(scored.slice(0, limit));
  const summary = summarizeIntradayAnalogs(analogs, { roundTripCostPct });
  const minimum = Math.max(1, Math.floor(Number(minimumAnalogs) || 10));
  const qualityScore = summary.sampleCount
    ? clamp((summary.averageSimilarity ?? 0) * Math.min(1, summary.effectiveSampleSize / minimum), 0, 1)
    : 0;
  const status = !pool.causalCandidateCount
    ? 'NO_CAUSAL_INTRADAY_ANALOG_CANDIDATES'
    : summary.sampleCount < minimum
      ? 'INSUFFICIENT_INTRADAY_ANALOGS'
      : 'INTRADAY_ANALOGS_READY';

  return Object.freeze({
    phase: '57.p23',
    status,
    query: pool.query,
    featureKeys: pool.featureKeys,
    featureScaler: scaler,
    featureScalerFitOnCausalCandidatePoolOnly: true,
    analogs,
    summary,
    analogQualityScore: qualityScore,
    minimumAnalogs: minimum,
    candidateAudit: Object.freeze({
      inputCount: Array.isArray(candidates) ? candidates.length : 0,
      causalCandidateCount: pool.causalCandidateCount,
      scoredCandidateCount: scored.length,
      selectedAnalogCount: analogs.length,
      rejected: pool.rejected,
      maxOutcomeAtUsed: analogs.length ? analogs.reduce((latest, row) => row.outcomeAt > latest ? row.outcomeAt : latest, analogs[0].outcomeAt) : null,
      candidateOutcomesFullyRealizedBeforeQuery: pool.candidateOutcomesFullyRealizedBeforeQuery,
      currentSessionExcluded: pool.currentSessionExcluded,
      sameSymbolOnly: pool.sameSymbolOnly,
    }),
    distanceUsesOutcomeLabels: false,
    outcomeDerivedFeaturesAllowed: false,
    pointInTime: true,
    intradayOnly: true,
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    researchOnly: true,
    reviewOnly: true,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_P23_SAFETY,
  });
}

export default {
  selectCausalAnalogPool,
  fitCausalRobustScaler,
  summarizeIntradayAnalogs,
  findIntradayHistoricalAnalogs,
};
