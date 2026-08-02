import { calculateWeightedScore } from "./market-score.js";

export const FEAR_GREED_WEIGHTS = Object.freeze({
  volatility: 35,
  breadth: 20,
  momentum: 20,
  news: 15,
  market: 10,
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

function normalizeReport(value, { invert = false } = {}) {
  const source = value && typeof value === "object" ? value : { score: value };
  const rawScore = finiteOrNull(source.score);
  const score = rawScore === null ? null : clamp(rawScore);

  return {
    score: score === null ? null : invert ? 100 - score : score,
    confidence:
      score === null ? 0 : clamp(finiteOrNull(source.confidence) ?? 100),
    coverage:
      score === null ? 0 : clamp(finiteOrNull(source.coverage) ?? 100),
  };
}

export function classifyFearGreed(score) {
  const value = finiteOrNull(score);

  if (value === null) return "UNKNOWN";
  if (value >= 75) return "EXTREME_GREED";
  if (value >= 60) return "GREED";
  if (value <= 25) return "EXTREME_FEAR";
  if (value <= 40) return "FEAR";
  return "NEUTRAL";
}

export function calculateFearGreed({
  volatility,
  breadth,
  momentum,
  news,
  market,
  weights = FEAR_GREED_WEIGHTS,
} = {}) {
  const aggregate = calculateWeightedScore([
    {
      key: "volatility",
      report: normalizeReport(volatility, { invert: true }),
      weight: Math.max(0, finiteOrNull(weights?.volatility) ?? 35),
    },
    {
      key: "breadth",
      report: normalizeReport(breadth),
      weight: Math.max(0, finiteOrNull(weights?.breadth) ?? 20),
    },
    {
      key: "momentum",
      report: normalizeReport(momentum),
      weight: Math.max(0, finiteOrNull(weights?.momentum) ?? 20),
    },
    {
      key: "news",
      report: normalizeReport(news),
      weight: Math.max(0, finiteOrNull(weights?.news) ?? 15),
    },
    {
      key: "market",
      report: normalizeReport(market),
      weight: Math.max(0, finiteOrNull(weights?.market) ?? 10),
    },
  ]);

  return {
    score: aggregate.score,
    confidence: aggregate.confidence,
    coverage: aggregate.coverage,
    label: classifyFearGreed(aggregate.score),
    components: aggregate.components,
    isProbability: false,
  };
}

export class FearGreedEngine {
  constructor({ weights = FEAR_GREED_WEIGHTS } = {}) {
    this.weights = Object.freeze({ ...FEAR_GREED_WEIGHTS, ...(weights || {}) });
  }

  calculate(input = {}) {
    return calculateFearGreed({ ...input, weights: this.weights });
  }
}

export const fearGreedEngine = new FearGreedEngine();

export default calculateFearGreed;
