import {
  normalizeMarketObservations,
  resolveLatestObservationTimestamp,
  summarizeObservationCoverage,
} from "./market-observation-normalizer.js";
import { calculateWeightedScore } from "./market-score.js";

export const LIQUIDITY_WEIGHTS = Object.freeze({
  volumeActivity: 50,
  volumeFlow: 30,
  turnoverActivity: 20,
});

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function clampScore(value) {
  return Math.min(100, Math.max(0, value));
}

function median(values) {
  const sorted = values
    .filter(Number.isFinite)
    .sort((first, second) => first - second);

  if (!sorted.length) return null;

  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}

export function scoreLiquidityRatio(ratio) {
  if (!Number.isFinite(ratio) || ratio < 0) {
    return null;
  }

  return round(clampScore(50 + (ratio - 1) * 50));
}

function activityMetric(
  observations,
  { key, field, weight, expectedCount },
) {
  const summary = summarizeObservationCoverage(
    observations,
    (item) => item[field] !== null,
    { expectedCount },
  );
  const items = summary.items.map((item) => ({
    symbol: item.symbol,
    ratio: item[field],
    score: scoreLiquidityRatio(item[field]),
    confidence: item.confidence,
  }));
  const aggregate = calculateWeightedScore(
    items.map((item) => ({
      key: item.symbol,
      score: item.score,
      confidence: item.confidence,
      coverage: 100,
      weight: 1,
    })),
  );
  const medianRatio = median(items.map((item) => item.ratio));
  const activeCount = items.filter((item) => item.ratio >= 1).length;

  return {
    key,
    weight,
    score: aggregate.score,
    confidence: summary.confidence,
    coverage: summary.coverage,
    availableCount: summary.availableCount,
    requestedCount: summary.requestedCount,
    medianRatio: medianRatio === null ? null : round(medianRatio, 3),
    activeCount,
    activePercent: summary.availableCount
      ? round((activeCount / summary.availableCount) * 100)
      : null,
    items,
  };
}

function volumeFlowMetric(observations, expectedCount) {
  const summary = summarizeObservationCoverage(
    observations,
    (item) => item.changePercent !== null && item.volume !== null,
    { expectedCount },
  );
  const upVolume = summary.items
    .filter((item) => item.changePercent > 0)
    .reduce((total, item) => total + item.volume, 0);
  const downVolume = summary.items
    .filter((item) => item.changePercent < 0)
    .reduce((total, item) => total + item.volume, 0);
  const unchangedVolume = summary.items
    .filter((item) => item.changePercent === 0)
    .reduce((total, item) => total + item.volume, 0);
  const directionalVolume = upVolume + downVolume;
  const score = summary.availableCount
    ? directionalVolume > 0
      ? round((upVolume / directionalVolume) * 100)
      : 50
    : null;

  return {
    key: "volumeFlow",
    weight: LIQUIDITY_WEIGHTS.volumeFlow,
    score,
    confidence: summary.confidence,
    coverage: summary.coverage,
    availableCount: summary.availableCount,
    requestedCount: summary.requestedCount,
    upVolume: round(upVolume),
    downVolume: round(downVolume),
    unchangedVolume: round(unchangedVolume),
    upVolumePercent:
      directionalVolume > 0 ? round((upVolume / directionalVolume) * 100) : null,
  };
}

export function analyzeLiquidity(
  inputs = [],
  { expectedCount = null } = {},
) {
  const observations = normalizeMarketObservations(inputs);
  const volumeActivity = activityMetric(observations, {
    key: "volumeActivity",
    field: "volumeRatio",
    weight: LIQUIDITY_WEIGHTS.volumeActivity,
    expectedCount,
  });
  const volumeFlow = volumeFlowMetric(observations, expectedCount);
  const turnoverActivity = activityMetric(observations, {
    key: "turnoverActivity",
    field: "turnoverRatio",
    weight: LIQUIDITY_WEIGHTS.turnoverActivity,
    expectedCount,
  });
  const metrics = [volumeActivity, volumeFlow, turnoverActivity];
  const composite = calculateWeightedScore(
    metrics.map((metric) => ({
      key: metric.key,
      report: metric,
      weight: metric.weight,
    })),
  );

  return {
    score: composite.score,
    confidence: composite.confidence,
    coverage: composite.coverage,
    timestamp: resolveLatestObservationTimestamp(observations),
    availableCount: volumeActivity.availableCount,
    requestedCount: volumeActivity.requestedCount,
    medianVolumeRatio: volumeActivity.medianRatio,
    activeVolumePercent: volumeActivity.activePercent,
    upVolumePercent: volumeFlow.upVolumePercent,
    medianTurnoverRatio: turnoverActivity.medianRatio,
    volumeActivity,
    volumeFlow,
    turnoverActivity,
    components: metrics,
  };
}

export class LiquidityEngine {
  analyze(inputs = [], options = {}) {
    return analyzeLiquidity(inputs, options);
  }
}

export const liquidityEngine = new LiquidityEngine();

export default analyzeLiquidity;
