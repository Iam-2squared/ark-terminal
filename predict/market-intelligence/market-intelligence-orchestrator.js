import { MarketSnapshotEngine } from "./market-snapshot-engine.js";
import { marketBreadthEngine } from "./market-breadth.js";
import { liquidityEngine } from "./liquidity-engine.js";
import { sectorStrengthEngine } from "./sector-strength-engine.js";
import { sectorRotationEngine } from "./sector-rotation-engine.js";
import { compositeMarketScoreEngine } from "./composite-market-score.js";
import { newsIntelligenceEngine } from "./news-intelligence-engine.js";
import { marketPredictionEngine } from "./market-prediction-engine.js";

export const MARKET_INTELLIGENCE_ORCHESTRATOR_VERSION =
  "market-intelligence-orchestrator-v1";

function hasOwn(value, key) {
  return Boolean(
    value && Object.prototype.hasOwnProperty.call(value, key),
  );
}

function requireMethod(value, method, label) {
  if (!value || typeof value[method] !== "function") {
    throw new TypeError(`Market Intelligence ${label} is invalid.`);
  }
}

function isoTimestamp(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError("Market Intelligence timestamp is invalid.");
  }

  return date.toISOString();
}

function resolveTimestamp(input, options, now) {
  return isoTimestamp(
    options.timestamp ?? input.timestamp ?? now(),
  );
}

function collectionRecords(value) {
  if (Array.isArray(value)) return value;
  if (value instanceof Map) return [...value.values()];
  if (value && Array.isArray(value.data)) return value.data;

  if (value && typeof value === "object") {
    if (
      [
        "timestamp",
        "publishedAt",
        "published_at",
        "title",
        "headline",
        "symbol",
      ].some((key) => hasOwn(value, key))
    ) {
      return [value];
    }

    return Object.values(value)
      .filter(Array.isArray)
      .flat();
  }

  return [];
}

function timestampMilliseconds(value) {
  const numeric =
    typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))
      ? Number(value)
      : null;
  const normalized =
    numeric !== null && numeric < 1_000_000_000_000
      ? numeric * 1000
      : value;

  return new Date(normalized).getTime();
}

function validateCollectionPointInTime(
  value,
  timestamp,
  fields,
  label,
) {
  const asOf = timestampMilliseconds(timestamp);

  for (const record of collectionRecords(value)) {
    for (const field of fields) {
      const sourceValue = record?.[field];

      if (
        sourceValue === null ||
        sourceValue === undefined ||
        sourceValue === ""
      ) {
        continue;
      }

      const sourceTime = timestampMilliseconds(sourceValue);

      if (Number.isFinite(sourceTime) && sourceTime > asOf) {
        throw new RangeError(
          `${label} contains data later than the analysis timestamp.`,
        );
      }

      break;
    }
  }
}

function resolveObservations(input) {
  if (hasOwn(input, "observations")) return input.observations;
  if (hasOwn(input, "marketObservations")) {
    return input.marketObservations;
  }
  return null;
}

function isNewsReport(value) {
  return Boolean(
    value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      hasOwn(value, "score") &&
      (hasOwn(value, "coverage") ||
        Array.isArray(value.items)),
  );
}

function resolveNewsItems(input) {
  if (hasOwn(input, "newsItems")) return input.newsItems;
  if (input.news && !isNewsReport(input.news)) return input.news;
  return null;
}

function suppliedNewsReport(input) {
  if (input.newsIntelligence) return input.newsIntelligence;
  return isNewsReport(input.news) ? input.news : null;
}

function hasBundleThreeReport(input) {
  return [
    input.breadth,
    input.liquidity,
    input.sectorStrength,
    input.sectorRotation,
  ].some(Boolean);
}

async function loadMarketData(input, options) {
  if (hasOwn(input, "marketData")) {
    return input.marketData;
  }

  if (!input.marketDataService) {
    return null;
  }

  requireMethod(input.marketDataService, "getAll", "data service");

  return input.marketDataService.getAll({
    forceRefresh: options.forceRefresh === true,
    signal: options.signal,
  });
}

export class MarketIntelligenceOrchestrator {
  constructor({
    snapshotEngine = null,
    breadthEngine = marketBreadthEngine,
    liquidity = liquidityEngine,
    sectorStrength = sectorStrengthEngine,
    sectorRotation = sectorRotationEngine,
    compositeMarket = compositeMarketScoreEngine,
    newsEngine = newsIntelligenceEngine,
    predictionEngine = marketPredictionEngine,
    now = Date.now,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("Market Intelligence clock must be a function.");
    }

    const resolvedSnapshotEngine =
      snapshotEngine || new MarketSnapshotEngine({ now });

    requireMethod(resolvedSnapshotEngine, "analyze", "snapshot engine");
    requireMethod(breadthEngine, "analyze", "breadth engine");
    requireMethod(liquidity, "analyze", "liquidity engine");
    requireMethod(sectorStrength, "analyze", "sector strength engine");
    requireMethod(sectorRotation, "analyze", "sector rotation engine");
    requireMethod(compositeMarket, "calculate", "composite market engine");
    requireMethod(newsEngine, "analyze", "news engine");
    requireMethod(predictionEngine, "analyze", "prediction engine");

    this.snapshotEngine = resolvedSnapshotEngine;
    this.breadthEngine = breadthEngine;
    this.liquidityEngine = liquidity;
    this.sectorStrengthEngine = sectorStrength;
    this.sectorRotationEngine = sectorRotation;
    this.compositeMarketEngine = compositeMarket;
    this.newsEngine = newsEngine;
    this.predictionEngine = predictionEngine;
    this.now = now;
  }

  async analyze(input = {}, options = {}) {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("Market Intelligence input must be an object.");
    }

    const timestamp = resolveTimestamp(input, options, this.now);
    const marketData = await loadMarketData(input, options);

    validateCollectionPointInTime(
      marketData,
      timestamp,
      ["timestamp"],
      "Market data",
    );

    const marketSnapshot =
      input.marketSnapshot ??
      input.snapshot ??
      (marketData === null
        ? null
        : this.snapshotEngine.analyze(marketData, { timestamp }));
    const observations = resolveObservations(input);

    validateCollectionPointInTime(
      observations,
      timestamp,
      ["timestamp"],
      "Market observations",
    );

    const breadth =
      input.breadth ??
      (observations === null
        ? null
        : this.breadthEngine.analyze(observations, {
            expectedCount: input.expectedObservationCount,
          }));
    const liquidity =
      input.liquidity ??
      (observations === null
        ? null
        : this.liquidityEngine.analyze(observations, {
            expectedCount: input.expectedObservationCount,
          }));
    const sectorStrength =
      input.sectorStrength ??
      (observations === null
        ? null
        : this.sectorStrengthEngine.analyze(observations, {
            expectedCount: input.expectedObservationCount,
          }));
    const sectorRotation =
      input.sectorRotation ??
      (sectorStrength && input.previousSectorStrength
        ? this.sectorRotationEngine.analyze({
            current: sectorStrength,
            previous: input.previousSectorStrength,
          })
        : null);
    const bundleThree = {
      breadth,
      liquidity,
      sectorStrength,
      sectorRotation,
    };
    const compositeMarket =
      input.compositeMarket ??
      (hasBundleThreeReport(bundleThree)
        ? this.compositeMarketEngine.calculate({
            ...bundleThree,
            timestamp,
          })
        : null);
    const newsItems = resolveNewsItems(input);

    validateCollectionPointInTime(
      newsItems,
      timestamp,
      ["publishedAt", "published_at", "timestamp", "date"],
      "News data",
    );

    const newsIntelligence =
      suppliedNewsReport(input) ??
      (newsItems === null
        ? null
        : await this.newsEngine.analyze(newsItems, { timestamp }));
    const prediction = this.predictionEngine.analyze(
      {
        marketSnapshot,
        compositeMarket,
        breadth,
        liquidity,
        sectorStrength,
        newsIntelligence,
        volatility: input.volatility,
        macro: input.macro,
        momentum: input.momentum,
        technical: input.technical,
        quote: input.quote,
      },
      {
        timestamp,
        atrPercent: options.atrPercent ?? input.atrPercent,
        calibration: options.calibration ?? input.calibration,
      },
    );

    return {
      version: MARKET_INTELLIGENCE_ORCHESTRATOR_VERSION,
      status: prediction.status,
      timestamp: prediction.timestamp,
      marketSnapshot,
      breadth,
      liquidity,
      sectorStrength,
      sectorRotation,
      compositeMarket,
      newsIntelligence,
      features: prediction.features,
      predictions: prediction.predictions,
      horizons: prediction.horizons,
      prediction,
      executionAllowed: false,
    };
  }
}

export const marketIntelligenceOrchestrator =
  new MarketIntelligenceOrchestrator();

export const MarketIntelligenceOrchestratorInternals = Object.freeze({
  hasOwn,
  isoTimestamp,
  resolveTimestamp,
  collectionRecords,
  timestampMilliseconds,
  validateCollectionPointInTime,
  resolveObservations,
  isNewsReport,
  resolveNewsItems,
  suppliedNewsReport,
  hasBundleThreeReport,
  loadMarketData,
});

export default MarketIntelligenceOrchestrator;
