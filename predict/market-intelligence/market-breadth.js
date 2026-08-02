import {
  normalizeMarketObservations,
  resolveLatestObservationTimestamp,
  summarizeObservationCoverage,
} from "./market-observation-normalizer.js";
import { calculateWeightedScore } from "./market-score.js";

export const MARKET_BREADTH_WEIGHTS = Object.freeze({
  advanceDecline: 60,
  aboveMa20: 15,
  aboveMa50: 15,
  newHighLow: 10,
});

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function clampScore(value) {
  return Math.min(100, Math.max(0, value));
}

export function calculateBreadthBalanceScore({
  advancers = 0,
  decliners = 0,
  total = 0,
} = {}) {
  if (!Number.isFinite(total) || total <= 0) {
    return null;
  }

  return round(
    clampScore(50 + ((advancers - decliners) / total) * 50),
  );
}

function buildMetric(key, weight, summary, score) {
  return {
    key,
    weight,
    score,
    confidence: summary.confidence,
    coverage: summary.coverage,
    availableCount: summary.availableCount,
    requestedCount: summary.requestedCount,
  };
}

function booleanMetric(
  observations,
  field,
  key,
  weight,
  expectedCount,
) {
  const summary = summarizeObservationCoverage(
    observations,
    (item) => item[field] !== null,
    { expectedCount },
  );
  const positiveCount = summary.items.filter((item) => item[field]).length;
  const score = summary.availableCount
    ? round((positiveCount / summary.availableCount) * 100)
    : null;

  return {
    ...buildMetric(key, weight, summary, score),
    positiveCount,
    percent: score,
  };
}

function highLowMetric(observations, expectedCount) {
  const summary = summarizeObservationCoverage(
    observations,
    (item) => item.newHigh !== null || item.newLow !== null,
    { expectedCount },
  );
  const newHighs = summary.items.filter((item) => item.newHigh).length;
  const newLows = summary.items.filter((item) => item.newLow).length;
  const score = calculateBreadthBalanceScore({
    advancers: newHighs,
    decliners: newLows,
    total: summary.availableCount,
  });

  return {
    ...buildMetric(
      "newHighLow",
      MARKET_BREADTH_WEIGHTS.newHighLow,
      summary,
      score,
    ),
    newHighs,
    newLows,
    ratio: newLows > 0 ? round(newHighs / newLows, 3) : null,
  };
}

export function analyzeMarketBreadth(
  inputs = [],
  { expectedCount = null } = {},
) {
  const observations = normalizeMarketObservations(inputs);
  const changeSummary = summarizeObservationCoverage(
    observations,
    (item) => item.changePercent !== null,
    { expectedCount },
  );
  const advancers = changeSummary.items.filter(
    (item) => item.changePercent > 0,
  ).length;
  const decliners = changeSummary.items.filter(
    (item) => item.changePercent < 0,
  ).length;
  const unchanged = changeSummary.availableCount - advancers - decliners;
  const advanceDecline = {
    ...buildMetric(
      "advanceDecline",
      MARKET_BREADTH_WEIGHTS.advanceDecline,
      changeSummary,
      calculateBreadthBalanceScore({
        advancers,
        decliners,
        total: changeSummary.availableCount,
      }),
    ),
    advancers,
    decliners,
    unchanged,
  };
  const aboveMa20 = booleanMetric(
    observations,
    "aboveMa20",
    "aboveMa20",
    MARKET_BREADTH_WEIGHTS.aboveMa20,
    expectedCount,
  );
  const aboveMa50 = booleanMetric(
    observations,
    "aboveMa50",
    "aboveMa50",
    MARKET_BREADTH_WEIGHTS.aboveMa50,
    expectedCount,
  );
  const newHighLow = highLowMetric(observations, expectedCount);
  const metrics = [advanceDecline, aboveMa20, aboveMa50, newHighLow];
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
    availableCount: changeSummary.availableCount,
    requestedCount: changeSummary.requestedCount,
    advancers,
    decliners,
    unchanged,
    advancePercent: changeSummary.availableCount
      ? round((advancers / changeSummary.availableCount) * 100)
      : null,
    declinePercent: changeSummary.availableCount
      ? round((decliners / changeSummary.availableCount) * 100)
      : null,
    netAdvances: advancers - decliners,
    advanceDeclineRatio:
      decliners > 0 ? round(advancers / decliners, 3) : null,
    aboveMa20,
    aboveMa50,
    newHighLow,
    components: metrics,
  };
}

export class MarketBreadthEngine {
  analyze(inputs = [], options = {}) {
    return analyzeMarketBreadth(inputs, options);
  }
}

export const marketBreadthEngine = new MarketBreadthEngine();

export default analyzeMarketBreadth;
