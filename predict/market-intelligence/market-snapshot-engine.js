import { isMarketDataPoint } from "./market-data-model.js";
import { analyzeGlobalIndexes } from "./global-index-engine.js";
import { analyzeMacroEnvironment } from "./macro-engine.js";
import { calculateCompositeMarketScore } from "./market-score.js";
import { detectSnapshotMarketRegime } from "./market-regime.js";

function normalizeCollection(value) {
  if (Array.isArray(value)) {
    return value.filter(isMarketDataPoint);
  }

  if (value instanceof Map) {
    return [...value.values()].filter(isMarketDataPoint);
  }

  if (value && Array.isArray(value.data)) {
    return value.data.filter(isMarketDataPoint);
  }

  if (value === null || value === undefined) {
    return [];
  }

  throw new TypeError("Market snapshot data must be an array, Map, or data array.");
}

function isoTimestamp(now) {
  const value = typeof now === "function" ? now() : now;
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError("Market snapshot clock returned an invalid timestamp.");
  }

  return date.toISOString();
}

export function buildMarketSnapshot(
  marketData = [],
  { now = Date.now } = {},
) {
  const points = normalizeCollection(marketData);
  const indexes = analyzeGlobalIndexes(points);
  const macro = analyzeMacroEnvironment(points);
  const composite = calculateCompositeMarketScore({ indexes, macro });
  const regime = detectSnapshotMarketRegime({
    score: composite.score,
    indexes,
    macro,
  });

  return {
    indexes,
    macro,
    regime,
    score: composite.score,
    timestamp: isoTimestamp(now),
  };
}

export class MarketSnapshotEngine {
  constructor({ marketDataService = null, now = Date.now } = {}) {
    if (marketDataService && typeof marketDataService.getAll !== "function") {
      throw new TypeError("Market snapshot service must expose getAll().");
    }

    if (typeof now !== "function") {
      throw new TypeError("Market snapshot clock must be a function.");
    }

    this.marketDataService = marketDataService;
    this.now = now;
  }

  analyze(marketData = []) {
    return buildMarketSnapshot(marketData, { now: this.now });
  }

  async run({ marketData, forceRefresh = false, signal } = {}) {
    if (marketData !== undefined) {
      return this.analyze(marketData);
    }

    if (!this.marketDataService) {
      throw new TypeError("Market snapshot service is required to load data.");
    }

    const loaded = await this.marketDataService.getAll({
      forceRefresh,
      signal,
    });

    return this.analyze(loaded);
  }
}

export async function createMarketSnapshot({
  marketData,
  marketDataService,
  now = Date.now,
  forceRefresh = false,
  signal,
} = {}) {
  const engine = new MarketSnapshotEngine({
    marketDataService,
    now,
  });

  return engine.run({
    marketData,
    forceRefresh,
    signal,
  });
}

export default MarketSnapshotEngine;
