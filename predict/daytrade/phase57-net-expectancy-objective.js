export const PHASE57_P21_4_SAFETY = Object.freeze({
  mode: 'PHASE57_NET_EXPECTANCY_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  oosSelectionAllowed: false,
  humanApprovalRequired: true,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function quantile(values, q) {
  if (!values.length) return null;
  const ordered = values.slice().sort((a, b) => a - b);
  const position = (ordered.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return ordered[lower];
  return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower);
}

function sampleStd(values) {
  if (values.length < 2) return null;
  const m = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - m) ** 2, 0) / (values.length - 1));
}

function normalizeObservation(row, index) {
  const netReturnPct = finite(row?.netReturnPct) ? Number(row.netReturnPct)
    : finite(row?.netReturn) ? Number(row.netReturn)
      : finite(row?.netAverageReturnPct) ? Number(row.netAverageReturnPct) : null;
  if (!finite(netReturnPct)) return null;
  const probability = finite(row?.probability) ? Math.max(0, Math.min(1, Number(row.probability))) : null;
  const label = finite(row?.label) && [0, 1].includes(Number(row.label)) ? Number(row.label) : null;
  return Object.freeze({
    id: row?.id ?? `${row?.symbol ?? 'UNKNOWN'}|${row?.featureCutoff ?? index}|${index}`,
    symbol: row?.symbol ?? 'UNKNOWN',
    fold: row?.baseOuterFold ?? row?.outerFold ?? row?.fold ?? null,
    featureCutoff: row?.featureCutoff ?? row?.timestamp ?? null,
    netReturnPct,
    probability,
    label,
    mfePct: finite(row?.mfePct) ? Number(row.mfePct) : null,
    maePct: finite(row?.maePct) ? Number(row.maePct) : null,
    barsHeld: finite(row?.barsHeld) ? Number(row.barsHeld) : null,
  });
}

function profitFactor(returns) {
  const gains = returns.filter(value => value > 0).reduce((sum, value) => sum + value, 0);
  const losses = -returns.filter(value => value < 0).reduce((sum, value) => sum + value, 0);
  return losses > 0 ? gains / losses : gains > 0 ? Infinity : null;
}

function maxDrawdownPct(returns) {
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value / 100;
    peak = Math.max(peak, equity);
    if (peak > 0) maxDrawdown = Math.max(maxDrawdown, (peak - equity) / peak);
  }
  return maxDrawdown * 100;
}

function calibration(observations, bins = 10) {
  const scored = observations.filter(row => finite(row.probability) && [0, 1].includes(row.label));
  if (!scored.length) return Object.freeze({ sampleCount: 0, brierScore: null, ece: null, bins: Object.freeze([]) });
  const brierScore = mean(scored.map(row => (row.probability - row.label) ** 2));
  const bucketCount = Math.max(2, Math.floor(Number(bins) || 10));
  const bucketRows = Array.from({ length: bucketCount }, () => []);
  for (const row of scored) {
    const index = Math.min(bucketCount - 1, Math.floor(row.probability * bucketCount));
    bucketRows[index].push(row);
  }
  const summaries = bucketRows.map((rows, index) => {
    if (!rows.length) return Object.freeze({ index, count: 0, meanProbability: null, eventRate: null, absoluteGap: null });
    const meanProbability = mean(rows.map(row => row.probability));
    const eventRate = mean(rows.map(row => row.label));
    return Object.freeze({ index, count: rows.length, meanProbability, eventRate, absoluteGap: Math.abs(meanProbability - eventRate) });
  });
  const ece = summaries.reduce((sum, bin) => sum + (bin.count / scored.length) * Number(bin.absoluteGap ?? 0), 0);
  return Object.freeze({ sampleCount: scored.length, brierScore, ece, bins: Object.freeze(summaries) });
}

function xorshift32(seed) {
  let state = (Number(seed) >>> 0) || 0x6d2b79f5;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return (state >>> 0) / 4294967296;
  };
}

function bootstrapMeanConfidenceInterval(observations, { iterations = 2000, confidence = 0.95, seed = 570214 } = {}) {
  if (!observations.length) return Object.freeze({ method: 'NONE', iterations: 0, confidence, lowerPct: null, upperPct: null });
  const foldGroups = new Map();
  for (const row of observations) {
    if (row.fold === null || row.fold === undefined) continue;
    const key = String(row.fold);
    if (!foldGroups.has(key)) foldGroups.set(key, []);
    foldGroups.get(key).push(row.netReturnPct);
  }
  const useCluster = foldGroups.size >= 3;
  const groups = useCluster ? [...foldGroups.values()] : null;
  const returns = observations.map(row => row.netReturnPct);
  const rng = xorshift32(seed);
  const draws = [];
  const count = Math.max(200, Math.floor(Number(iterations) || 2000));
  for (let i = 0; i < count; i += 1) {
    const sampled = [];
    if (useCluster) {
      for (let g = 0; g < groups.length; g += 1) sampled.push(...groups[Math.floor(rng() * groups.length)]);
    } else {
      for (let j = 0; j < returns.length; j += 1) sampled.push(returns[Math.floor(rng() * returns.length)]);
    }
    draws.push(mean(sampled));
  }
  const alpha = Math.max(0.001, Math.min(0.5, 1 - Number(confidence || 0.95)));
  return Object.freeze({
    method: useCluster ? 'DETERMINISTIC_FOLD_CLUSTER_BOOTSTRAP' : 'DETERMINISTIC_IID_BOOTSTRAP',
    iterations: count,
    confidence: 1 - alpha,
    lowerPct: quantile(draws, alpha / 2),
    upperPct: quantile(draws, 1 - alpha / 2),
    clusterCount: useCluster ? groups.length : 0,
    seed: Number(seed),
  });
}

function groupStability(observations, key) {
  const groups = new Map();
  for (const row of observations) {
    const value = row[key];
    if (value === null || value === undefined) continue;
    const id = String(value);
    if (!groups.has(id)) groups.set(id, []);
    groups.get(id).push(row.netReturnPct);
  }
  const summaries = [...groups.entries()].map(([id, values]) => Object.freeze({
    id,
    sampleCount: values.length,
    netAverageReturnPct: mean(values),
    profitFactor: profitFactor(values),
    positive: mean(values) > 0,
  }));
  const positiveCount = summaries.filter(group => group.positive).length;
  return Object.freeze({
    groupCount: summaries.length,
    positiveGroupCount: positiveCount,
    positiveGroupFraction: summaries.length ? positiveCount / summaries.length : null,
    groups: Object.freeze(summaries),
  });
}

function concentration(observations) {
  const counts = new Map();
  for (const row of observations) counts.set(row.symbol, (counts.get(row.symbol) || 0) + 1);
  const total = observations.length;
  const shares = [...counts.entries()].map(([symbol, count]) => Object.freeze({ symbol, count, share: total ? count / total : 0 }))
    .sort((a, b) => b.share - a.share);
  return Object.freeze({ symbolCount: shares.length, maxSingleSymbolShare: shares[0]?.share ?? null, shares: Object.freeze(shares) });
}

export function summarizeNetExpectancy(observations = [], options = {}) {
  const normalized = (Array.isArray(observations) ? observations : []).map(normalizeObservation).filter(Boolean)
    .sort((a, b) => String(a.featureCutoff ?? '').localeCompare(String(b.featureCutoff ?? '')));
  const returns = normalized.map(row => row.netReturnPct);
  const n = returns.length;
  const std = sampleStd(returns);
  const mfe = normalized.filter(row => finite(row.mfePct)).map(row => row.mfePct);
  const mae = normalized.filter(row => finite(row.maePct)).map(row => row.maePct);
  const holds = normalized.filter(row => finite(row.barsHeld)).map(row => row.barsHeld);
  const researchRows = Math.max(0, Number(options.researchRowCount ?? options.opportunityCount ?? 0));
  return Object.freeze({
    sampleCount: n,
    netAverageReturnPct: mean(returns),
    medianNetReturnPct: n ? quantile(returns, 0.5) : null,
    hitRate: n ? returns.filter(value => value > 0).length / n : null,
    profitFactor: profitFactor(returns),
    maxDrawdownPct: maxDrawdownPct(returns),
    tradeSharpe: n > 1 && std > 0 ? mean(returns) / std : null,
    returnStdPct: std,
    coverage: researchRows > 0 ? n / researchRows : null,
    averageMfePct: mean(mfe),
    averageMaePct: mean(mae),
    averageHoldingBars: mean(holds),
    confidenceInterval: bootstrapMeanConfidenceInterval(normalized, options.bootstrap),
    calibration: calibration(normalized, options.calibrationBins ?? 10),
    symbolStability: groupStability(normalized, 'symbol'),
    foldStability: groupStability(normalized, 'fold'),
    concentration: concentration(normalized),
  });
}

export function evaluateNetExpectancyEvidence(observations = [], options = {}) {
  const metrics = summarizeNetExpectancy(observations, options);
  const thresholds = Object.freeze({
    minSignals: Number(options.minSignals ?? 100),
    minimumNetAverageReturnPct: Number(options.minimumNetAverageReturnPct ?? 0),
    minimumLowerConfidenceBoundPct: Number(options.minimumLowerConfidenceBoundPct ?? 0),
    minimumProfitFactor: Number(options.minimumProfitFactor ?? 1.2),
    maximumDrawdownPct: Number(options.maximumDrawdownPct ?? 10),
    minimumPositiveFoldFraction: Number(options.minimumPositiveFoldFraction ?? 0.6),
    minimumFoldGroups: Number(options.minimumFoldGroups ?? 3),
    requireCrossSymbolStability: options.requireCrossSymbolStability === true,
    minimumPositiveSymbolFraction: Number(options.minimumPositiveSymbolFraction ?? 0.6),
    minimumSymbolGroups: Number(options.minimumSymbolGroups ?? 3),
    maximumSingleSymbolShare: Number(options.maximumSingleSymbolShare ?? 0.6),
  });

  const failures = [];
  if (metrics.sampleCount < thresholds.minSignals) failures.push('INSUFFICIENT_SAMPLE');
  if (!finite(metrics.netAverageReturnPct) || metrics.netAverageReturnPct <= thresholds.minimumNetAverageReturnPct) failures.push('NET_EXPECTANCY_NOT_POSITIVE_ENOUGH');
  if (!finite(metrics.confidenceInterval.lowerPct) || metrics.confidenceInterval.lowerPct <= thresholds.minimumLowerConfidenceBoundPct) failures.push('NET_EXPECTANCY_LOWER_BOUND_NOT_POSITIVE');
  if (!finite(metrics.profitFactor) || metrics.profitFactor < thresholds.minimumProfitFactor) failures.push('PROFIT_FACTOR_TOO_LOW');
  if (!finite(metrics.maxDrawdownPct) || metrics.maxDrawdownPct > thresholds.maximumDrawdownPct) failures.push('MAX_DRAWDOWN_TOO_HIGH');
  if (metrics.foldStability.groupCount < thresholds.minimumFoldGroups) failures.push('INSUFFICIENT_FOLD_STABILITY_SAMPLE');
  else if (!finite(metrics.foldStability.positiveGroupFraction) || metrics.foldStability.positiveGroupFraction < thresholds.minimumPositiveFoldFraction) failures.push('FOLD_STABILITY_TOO_WEAK');
  if (thresholds.requireCrossSymbolStability) {
    if (metrics.symbolStability.groupCount < thresholds.minimumSymbolGroups) failures.push('INSUFFICIENT_SYMBOL_STABILITY_SAMPLE');
    else if (!finite(metrics.symbolStability.positiveGroupFraction) || metrics.symbolStability.positiveGroupFraction < thresholds.minimumPositiveSymbolFraction) failures.push('SYMBOL_STABILITY_TOO_WEAK');
    if (!finite(metrics.concentration.maxSingleSymbolShare) || metrics.concentration.maxSingleSymbolShare > thresholds.maximumSingleSymbolShare) failures.push('SINGLE_SYMBOL_CONCENTRATION_TOO_HIGH');
  }

  return Object.freeze({
    phase: '57.p21.4',
    objective: 'OOS_NET_EXPECTANCY_PRIMARY',
    status: failures.length ? 'ABSTAIN_INSUFFICIENT_NET_EXPECTANCY_EVIDENCE' : 'RESEARCH_EVIDENCE_GATE_PASSED',
    metrics,
    thresholds,
    failureReasons: Object.freeze(failures),
    evidenceGatePassed: failures.length === 0,
    researchOnly: true,
    recommendationAllowed: false,
    oosSelectionAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_P21_4_SAFETY,
  });
}

export default { summarizeNetExpectancy, evaluateNetExpectancyEvidence };
