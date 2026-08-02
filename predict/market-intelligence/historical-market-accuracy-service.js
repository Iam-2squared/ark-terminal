import {
  createHistoricalMarketSnapshotReference,
  restoreHistoricalMarketSnapshot,
} from "./historical-market-snapshot-model.js";
import {
  evaluateHistoricalMarketSnapshot,
} from "./historical-market-accuracy-engine.js";
import {
  composeHistoricalMarketAccuracy,
} from "./historical-market-accuracy-composer.js";
import { normalizeHistoricalOutcomeTimestamp } from "./historical-market-outcome-normalizer.js";

export const HISTORICAL_MARKET_ACCURACY_SERVICE_VERSION =
  "historical-market-accuracy-service-v1";

function validateFunction(value, label) {
  if (typeof value !== "function") {
    throw new TypeError(`Historical accuracy ${label} must be a function.`);
  }
  return value;
}

function objectValue(collection, snapshot) {
  if (!collection || typeof collection !== "object") return undefined;
  return (
    collection[snapshot.id] ??
    collection[snapshot.symbol] ??
    collection[snapshot.symbol.toLowerCase()] ??
    collection.default
  );
}

function resolveHistory(histories, snapshot) {
  if (typeof histories === "function") return histories(snapshot);
  if (histories instanceof Map) {
    return histories.get(snapshot.id) ?? histories.get(snapshot.symbol) ?? [];
  }
  if (Array.isArray(histories)) return histories;
  return objectValue(histories, snapshot) ?? [];
}

function resolvePrice(prices, snapshot) {
  if (typeof prices === "function") return prices(snapshot);
  if (prices instanceof Map) {
    return prices.get(snapshot.id) ?? prices.get(snapshot.symbol) ?? null;
  }
  if (typeof prices === "number" || typeof prices === "string") return prices;
  return objectValue(prices, snapshot) ?? null;
}

function errorDetails(error, snapshot = null) {
  return {
    name: error?.name ?? "Error",
    message: error?.message ?? String(error),
    snapshot: snapshot
      ? createHistoricalMarketSnapshotReference(snapshot)
      : null,
  };
}

export class HistoricalMarketAccuracyService {
  constructor({
    evaluator = evaluateHistoricalMarketSnapshot,
    composer = composeHistoricalMarketAccuracy,
    now = Date.now,
  } = {}) {
    this.evaluator = validateFunction(evaluator, "evaluator");
    this.composer = validateFunction(composer, "composer");
    this.now = validateFunction(now, "clock");
  }

  evaluateSnapshot(input = {}) {
    return this.evaluator({
      ...input,
      evaluatedAt: input.evaluatedAt ?? this.now(),
    });
  }

  evaluateSnapshotSafely(input = {}) {
    try {
      return {
        report: this.evaluateSnapshot(input),
        error: null,
      };
    } catch (error) {
      return {
        report: null,
        error: errorDetails(error),
      };
    }
  }

  evaluateBatch({
    snapshots = [],
    histories = {},
    prices = {},
    existingRecords = [],
    evaluatedAt = this.now(),
  } = {}) {
    if (!Array.isArray(snapshots)) {
      throw new TypeError("Historical accuracy snapshots must be an array.");
    }

    const normalizedEvaluatedAt = normalizeHistoricalOutcomeTimestamp(
      evaluatedAt,
      "Historical accuracy batch timestamp",
    );
    const reports = [];
    const errors = [];
    const identities = new Map();

    for (const supplied of snapshots) {
      let snapshot = null;

      try {
        snapshot = restoreHistoricalMarketSnapshot(supplied);
        const fingerprint = identities.get(snapshot.id);

        if (fingerprint && fingerprint !== snapshot.contentFingerprint) {
          throw new RangeError(
            "Historical accuracy batch contains conflicting snapshots.",
          );
        }
        if (fingerprint) continue;
        identities.set(snapshot.id, snapshot.contentFingerprint);

        reports.push(
          this.evaluator({
            snapshot,
            history: resolveHistory(histories, snapshot),
            predictionPrice: resolvePrice(prices, snapshot),
            evaluatedAt: normalizedEvaluatedAt,
          }),
        );
      } catch (error) {
        errors.push(errorDetails(error, snapshot));
      }
    }

    const composed = this.composer({
      evaluationReports: reports,
      existingRecords,
      generatedAt: normalizedEvaluatedAt,
    });

    return {
      ...composed,
      version: HISTORICAL_MARKET_ACCURACY_SERVICE_VERSION,
      status:
        errors.length > 0
          ? reports.length > 0
            ? "partial"
            : "error"
          : composed.status,
      evaluatedAt: normalizedEvaluatedAt,
      reports,
      errors,
      executionAllowed: false,
    };
  }
}

export const historicalMarketAccuracyService =
  new HistoricalMarketAccuracyService();

export const HistoricalMarketAccuracyServiceInternals = Object.freeze({
  validateFunction,
  objectValue,
  resolveHistory,
  resolvePrice,
  errorDetails,
});

export default HistoricalMarketAccuracyService;
