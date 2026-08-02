export const HISTORICAL_MARKET_OUTCOME_TIMELINE_VERSION =
  "historical-market-outcome-timeline-v1";

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function normalizeHistoricalOutcomeTimestamp(
  value,
  label = "Historical outcome timestamp",
) {
  if (value === null || value === undefined || value === "") {
    throw new TypeError(`${label} is required.`);
  }

  const numeric =
    typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))
      ? Number(value)
      : null;
  const milliseconds =
    numeric === null
      ? new Date(value).getTime()
      : numeric >= 1_000_000_000_000
        ? numeric
        : numeric * 1000;

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(`${label} is invalid.`);
  }

  return new Date(milliseconds).toISOString();
}

function timestampSeconds(value, label) {
  return Date.parse(normalizeHistoricalOutcomeTimestamp(value, label)) / 1000;
}

function normalizeSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function historyRows(history) {
  if (Array.isArray(history)) return history;
  if (Array.isArray(history?.candles)) return history.candles;
  if (Array.isArray(history?.rows)) return history.rows;
  return [];
}

function normalizeCandle(row = {}) {
  const timestamp =
    row.time ?? row.timestamp ?? row.date ?? row.datetime ?? row.Date;
  const close = finiteOrNull(
    row.close ?? row.Close ?? row.adjustedClose ?? row.adjClose ?? row.price,
  );

  if (timestamp === null || timestamp === undefined || close === null || close <= 0) {
    return null;
  }

  try {
    return {
      time: timestampSeconds(timestamp, "Historical outcome candle timestamp"),
      close,
      symbol: normalizeSymbol(row.symbol ?? row.ticker) || null,
    };
  } catch {
    return null;
  }
}

export function normalizeHistoricalMarketOutcomeCandles(
  history = [],
  { symbol = null } = {},
) {
  const normalizedSymbol = normalizeSymbol(symbol);
  const unique = new Map();

  for (const row of historyRows(history)) {
    const candle = normalizeCandle(row);
    if (!candle) continue;
    if (
      normalizedSymbol &&
      candle.symbol &&
      candle.symbol !== normalizedSymbol
    ) {
      continue;
    }

    unique.set(candle.time, {
      ...candle,
      symbol: candle.symbol || normalizedSymbol || null,
    });
  }

  return [...unique.values()].sort((first, second) => first.time - second.time);
}

function positivePrice(value, label) {
  if (value === null || value === undefined || value === "") return null;
  const number = finiteOrNull(value);

  if (number === null || number <= 0) {
    throw new TypeError(`${label} must be positive.`);
  }

  return number;
}

export function resolveHistoricalPredictionPrice({
  snapshot = {},
  predictionPrice = null,
} = {}) {
  const explicit = positivePrice(
    predictionPrice,
    "Historical outcome prediction price",
  );
  if (explicit !== null) return { price: explicit, source: "explicit" };

  const metadataPrice = positivePrice(
    snapshot?.metadata?.predictionPrice ?? snapshot?.metadata?.price,
    "Historical snapshot prediction price",
  );

  return metadataPrice === null
    ? { price: null, source: "unavailable" }
    : { price: metadataPrice, source: "snapshot_metadata" };
}

export function buildHistoricalMarketOutcomeTimeline({
  snapshot = {},
  history = [],
  predictionPrice = null,
  availableAt = Date.now(),
} = {}) {
  const symbol = normalizeSymbol(snapshot.symbol);
  if (!symbol) throw new TypeError("Historical outcome symbol is required.");

  const asOf = normalizeHistoricalOutcomeTimestamp(
    snapshot.asOf,
    "Historical snapshot analysis timestamp",
  );
  const normalizedAvailableAt = normalizeHistoricalOutcomeTimestamp(
    availableAt,
    "Historical outcome availability timestamp",
  );
  const asOfSeconds = Date.parse(asOf) / 1000;
  const availableAtSeconds = Date.parse(normalizedAvailableAt) / 1000;

  if (availableAtSeconds < asOfSeconds) {
    throw new RangeError(
      "Historical outcome availability cannot precede the snapshot.",
    );
  }

  const normalized = normalizeHistoricalMarketOutcomeCandles(history, {
    symbol,
  });
  const future = normalized.filter(
    (candle) => candle.time > asOfSeconds && candle.time <= availableAtSeconds,
  );
  const price = resolveHistoricalPredictionPrice({
    snapshot,
    predictionPrice,
  });
  const anchor =
    price.price === null
      ? null
      : {
          time: asOfSeconds,
          close: price.price,
          symbol,
          source: price.source,
        };

  return {
    version: HISTORICAL_MARKET_OUTCOME_TIMELINE_VERSION,
    symbol,
    asOf,
    availableAt: normalizedAvailableAt,
    anchor,
    candles: anchor ? [anchor, ...future] : [],
    futureCandles: future,
    availableFutureSessions: future.length,
    excludedAtOrBeforeSnapshot: normalized.filter(
      (candle) => candle.time <= asOfSeconds,
    ).length,
    excludedAfterAvailability: normalized.filter(
      (candle) => candle.time > availableAtSeconds,
    ).length,
    futureInformationIncluded: false,
    executionAllowed: false,
  };
}

export const HistoricalMarketOutcomeNormalizerInternals = Object.freeze({
  finiteOrNull,
  timestampSeconds,
  normalizeSymbol,
  historyRows,
  normalizeCandle,
  positivePrice,
});

export default buildHistoricalMarketOutcomeTimeline;
