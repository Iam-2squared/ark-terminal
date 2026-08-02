import {
  MARKET_DATA_STATUS,
  createMarketDataPoint,
  getMarketDataDefinition,
} from "./market-data-model.js";

export const DEFAULT_MARKET_DATA_STALE_AFTER_MS = 4 * 24 * 60 * 60 * 1000;

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function positiveOrNull(value) {
  const number = finiteOrNull(value);
  return number !== null && number > 0 ? number : null;
}

function timestampToMs(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))) {
    const numeric = Number(value);
    const milliseconds = numeric < 1_000_000_000_000 ? numeric * 1000 : numeric;
    return Number.isFinite(milliseconds) ? milliseconds : null;
  }

  const milliseconds = Date.parse(value);
  return Number.isFinite(milliseconds) ? milliseconds : null;
}

function isoTimestamp(value) {
  const milliseconds = timestampToMs(value);
  return milliseconds === null ? null : new Date(milliseconds).toISOString();
}

function readHistory(raw) {
  const candles = Array.isArray(raw?.candles) ? raw.candles : [];
  const rows = candles
    .map((candle) => ({
      price: positiveOrNull(candle?.close ?? candle?.adjustedClose),
      timestamp: timestampToMs(
        candle?.time ?? candle?.timestamp ?? candle?.date,
      ),
    }))
    .filter((row) => row.price !== null && row.timestamp !== null)
    .sort((first, second) => first.timestamp - second.timestamp);

  if (!rows.length) {
    return null;
  }

  return {
    price: rows.at(-1).price,
    previousClose: rows.length > 1 ? rows.at(-2).price : null,
    timestamp: rows.at(-1).timestamp,
  };
}

function readQuote(raw) {
  const price = positiveOrNull(
    raw?.price ?? raw?.regularMarketPrice ?? raw?.current,
  );

  if (price === null) {
    return null;
  }

  return {
    price,
    previousClose: positiveOrNull(
      raw?.previousClose ?? raw?.chartPreviousClose,
    ),
    change: finiteOrNull(raw?.change),
    changePercent: finiteOrNull(raw?.changePercent),
    timestamp:
      timestampToMs(raw?.timestamp ?? raw?.updatedAt ?? raw?.regularMarketTime),
  };
}

function calculateConfidence({
  definition,
  raw,
  timestamp,
  change,
  changePercent,
  status,
}) {
  if (
    status === MARKET_DATA_STATUS.ERROR ||
    status === MARKET_DATA_STATUS.UNAVAILABLE
  ) {
    return 0;
  }

  let confidence =
    finiteOrNull(raw?.confidence) ?? finiteOrNull(definition.confidence) ?? 80;

  if (!timestamp) {
    confidence -= 20;
  }

  if (change === null || changePercent === null) {
    confidence -= 10;
  }

  const sourceRows = positiveOrNull(raw?.sourceQuality?.sourceRowCount);
  const droppedRows = finiteOrNull(raw?.sourceQuality?.droppedRowCount);

  if (sourceRows !== null && droppedRows !== null && droppedRows > 0) {
    const droppedRatio = Math.min(1, Math.max(0, droppedRows / sourceRows));
    confidence -= droppedRatio * 40;
  }

  if (status === MARKET_DATA_STATUS.STALE) {
    confidence *= 0.65;
  }

  return Math.round(Math.max(0, Math.min(100, confidence)));
}

function resolveDefinition(value) {
  const definition = getMarketDataDefinition(value);

  if (!definition) {
    throw new RangeError(`Unknown market data symbol: ${String(value || "")}`);
  }

  return definition;
}

export function normalizeMarketData(
  raw,
  definitionOrSymbol,
  {
    now = Date.now(),
    staleAfterMs = DEFAULT_MARKET_DATA_STALE_AFTER_MS,
  } = {},
) {
  const definition = resolveDefinition(definitionOrSymbol);
  const extracted = readQuote(raw) ?? readHistory(raw);

  if (!extracted) {
    return createMarketDataPoint({
      symbol: definition.symbol,
      source: definition.source,
      status:
        raw?.status === MARKET_DATA_STATUS.ERROR
          ? MARKET_DATA_STATUS.ERROR
          : MARKET_DATA_STATUS.UNAVAILABLE,
      confidence: 0,
    });
  }

  const previousClose = extracted.previousClose;
  const change =
    previousClose !== null
      ? extracted.price - previousClose
      : finiteOrNull(extracted.change);
  const changePercent =
    previousClose !== null
      ? (change / previousClose) * 100
      : finiteOrNull(extracted.changePercent);
  const timestamp = isoTimestamp(extracted.timestamp);
  const timestampMs = timestampToMs(timestamp);
  const currentTime = typeof now === "function" ? Number(now()) : Number(now);
  const stale =
    timestampMs !== null &&
    Number.isFinite(currentTime) &&
    currentTime - timestampMs > Math.max(0, Number(staleAfterMs) || 0);
  const rawStatus = Object.values(MARKET_DATA_STATUS).includes(raw?.status)
    ? raw.status
    : null;
  const status =
    rawStatus === MARKET_DATA_STATUS.ERROR ||
    rawStatus === MARKET_DATA_STATUS.UNAVAILABLE
      ? rawStatus
      : stale || rawStatus === MARKET_DATA_STATUS.STALE
        ? MARKET_DATA_STATUS.STALE
        : MARKET_DATA_STATUS.AVAILABLE;
  const providerSource = raw?.source || raw?.provider;
  const source = definition.isProxy
    ? definition.source
    : String(providerSource || definition.source);

  return createMarketDataPoint({
    symbol: definition.symbol,
    price: extracted.price,
    change,
    changePercent,
    timestamp,
    source,
    status,
    confidence: calculateConfidence({
      definition,
      raw,
      timestamp,
      change,
      changePercent,
      status,
    }),
  });
}

export function normalizeMarketDataError(
  definitionOrSymbol,
  error,
  { now = Date.now() } = {},
) {
  const definition = resolveDefinition(definitionOrSymbol);
  const currentTime = typeof now === "function" ? now() : now;

  return createMarketDataPoint({
    symbol: definition.symbol,
    timestamp: isoTimestamp(currentTime),
    source: definition.source,
    status: error ? MARKET_DATA_STATUS.ERROR : MARKET_DATA_STATUS.UNAVAILABLE,
    confidence: 0,
  });
}

export const MarketDataNormalizerInternals = Object.freeze({
  finiteOrNull,
  timestampToMs,
  readHistory,
  readQuote,
});

export default normalizeMarketData;
