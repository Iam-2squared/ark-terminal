import {
  calculateWeightedScore,
  scoreToSentiment,
} from "./market-score.js";

export const COMPOSITE_MARKET_WEIGHTS = Object.freeze({
  breadth: 35,
  liquidity: 25,
  sectorStrength: 25,
  sectorRotation: 15,
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeWeights(weights = {}) {
  return Object.freeze(
    Object.fromEntries(
      Object.entries(COMPOSITE_MARKET_WEIGHTS).map(([key, fallback]) => [
        key,
        Math.max(0, finiteOrNull(weights?.[key]) ?? fallback),
      ]),
    ),
  );
}

function isoTimestamp(timestamp, now) {
  const value =
    timestamp ?? (typeof now === "function" ? now() : Number.NaN);
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError("Composite market score timestamp is invalid.");
  }

  return date.toISOString();
}

export function calculateCompositeMarketScore({
  breadth,
  liquidity,
  sectorStrength,
  sectorRotation,
  weights = COMPOSITE_MARKET_WEIGHTS,
  timestamp = null,
  now = Date.now,
} = {}) {
  if (typeof now !== "function") {
    throw new TypeError("Composite market score clock must be a function.");
  }

  const normalizedWeights = normalizeWeights(weights);
  const composite = calculateWeightedScore([
    {
      key: "breadth",
      report: breadth,
      weight: normalizedWeights.breadth,
    },
    {
      key: "liquidity",
      report: liquidity,
      weight: normalizedWeights.liquidity,
    },
    {
      key: "sectorStrength",
      report: sectorStrength,
      weight: normalizedWeights.sectorStrength,
    },
    {
      key: "sectorRotation",
      report: sectorRotation,
      weight: normalizedWeights.sectorRotation,
    },
  ]);

  return {
    score: composite.score,
    confidence: composite.confidence,
    coverage: composite.coverage,
    sentiment: scoreToSentiment(composite.score),
    timestamp: isoTimestamp(timestamp, now),
    components: composite.components,
  };
}

export class CompositeMarketScoreEngine {
  constructor({ weights = COMPOSITE_MARKET_WEIGHTS, now = Date.now } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("Composite market score clock must be a function.");
    }

    this.weights = normalizeWeights(weights);
    this.now = now;
  }

  calculate(input = {}) {
    return calculateCompositeMarketScore({
      ...input,
      weights: this.weights,
      now: this.now,
    });
  }
}

export const compositeMarketScoreEngine = new CompositeMarketScoreEngine();

export default calculateCompositeMarketScore;
