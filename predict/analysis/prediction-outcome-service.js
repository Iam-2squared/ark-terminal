import { resolvePredictions } from "../backtest/engine.js";

export const PREDICTION_OUTCOME_REFRESH_VERSION =
  "prediction-outcome-refresh-v1";
export const DEFAULT_OUTCOME_REFRESH_CONCURRENCY = 3;

function normalizedConcurrency(value) {
  const number = Number(value);

  if (!Number.isFinite(number) || number <= 0) {
    return DEFAULT_OUTCOME_REFRESH_CONCURRENCY;
  }

  return Math.max(1, Math.floor(number));
}

function pendingSymbols(records) {
  return [
    ...new Set(
      records
        .filter(
          (record) =>
            record?.status === "pending" &&
            typeof record.symbol === "string" &&
            record.symbol.trim(),
        )
        .map((record) => record.symbol.trim().toUpperCase()),
    ),
  ].sort();
}

function errorDetails(error) {
  return {
    name: error?.name ?? "Error",
    message: error?.message ?? String(error),
  };
}

async function mapWithConcurrency(items, concurrency, worker) {
  const results = new Array(items.length);
  let cursor = 0;

  async function consume() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await worker(items[index], index);
    }
  }

  await Promise.all(
    Array.from(
      { length: Math.min(items.length, normalizedConcurrency(concurrency)) },
      () => consume(),
    ),
  );

  return results;
}

function transitionIds(previous, next) {
  const previousStatus = new Map(
    previous.map((record) => [record?.id, record?.status]),
  );

  return next
    .filter(
      (record) =>
        record?.id &&
        previousStatus.get(record.id) === "pending" &&
        record.status === "resolved",
    )
    .map((record) => record.id);
}

export async function refreshPredictionOutcomes({
  records = [],
  fetchHistory,
  resolver = resolvePredictions,
  range = "5y",
  interval = "1d",
  concurrency = DEFAULT_OUTCOME_REFRESH_CONCURRENCY,
  signal = undefined,
} = {}) {
  if (!Array.isArray(records)) {
    throw new TypeError("Prediction outcome records must be an array.");
  }

  if (typeof fetchHistory !== "function") {
    throw new TypeError("Prediction outcome history provider is required.");
  }

  if (typeof resolver !== "function") {
    throw new TypeError("Prediction outcome resolver must be a function.");
  }

  const symbols = pendingSymbols(records);
  const histories = await mapWithConcurrency(
    symbols,
    concurrency,
    async (symbol) => {
      try {
        const history = await fetchHistory(symbol, {
          range,
          interval,
          signal,
        });

        if (!Array.isArray(history?.candles)) {
          throw new TypeError("History provider returned no candle collection.");
        }

        return {
          symbol,
          candles: history.candles,
          provider: history.provider ?? "unknown",
          error: null,
        };
      } catch (error) {
        if (error?.name === "AbortError") throw error;

        return {
          symbol,
          candles: null,
          provider: null,
          error: errorDetails(error),
        };
      }
    },
  );

  let nextRecords = [...records];
  const resolvedIds = [];
  const errors = [];
  const providers = new Set();

  for (const history of histories) {
    if (history.error) {
      errors.push({ symbol: history.symbol, ...history.error });
      continue;
    }

    const previous = nextRecords;
    const result = resolver(previous, history.symbol, history.candles);

    if (!result || !Array.isArray(result.records)) {
      errors.push({
        symbol: history.symbol,
        name: "TypeError",
        message: "Prediction outcome resolver returned an invalid result.",
      });
      continue;
    }

    nextRecords = result.records;
    resolvedIds.push(...transitionIds(previous, nextRecords));
    if (history.provider) providers.add(history.provider);
  }

  return {
    version: PREDICTION_OUTCOME_REFRESH_VERSION,
    status:
      errors.length > 0
        ? resolvedIds.length > 0
          ? "partial"
          : "unavailable"
        : "ready",
    changed: resolvedIds.length > 0,
    records: nextRecords,
    pendingSymbolCount: symbols.length,
    checkedSymbolCount: histories.length - errors.length,
    resolvedCount: resolvedIds.length,
    resolvedIds: [...new Set(resolvedIds)],
    providers: [...providers].sort(),
    errors,
    executionAllowed: false,
  };
}

export const PredictionOutcomeServiceInternals = Object.freeze({
  normalizedConcurrency,
  pendingSymbols,
  errorDetails,
  mapWithConcurrency,
  transitionIds,
});

export default refreshPredictionOutcomes;
