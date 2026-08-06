export const SURVIVORSHIP_UNIVERSE_VERSION = "survivorship-universe-v1";

function cleanSymbol(value) {
  return String(value ?? "").trim().toUpperCase();
}

function toTimestamp(value) {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function normalizeRecord(record = {}) {
  const listedAt = toTimestamp(record.listedAt ?? record.validFrom);
  const delistedAt = toTimestamp(record.delistedAt ?? record.validTo);
  return {
    symbol: cleanSymbol(record.symbol ?? record.ticker ?? record.code),
    listedAt,
    delistedAt,
    market: String(record.market ?? "UNKNOWN").trim().toUpperCase() || "UNKNOWN",
    status: String(record.status ?? "LISTED").trim().toUpperCase() || "LISTED",
    delistingReason: String(record.delistingReason ?? "").trim(),
    sourceVersion: String(record.sourceVersion ?? "UNKNOWN").trim(),
  };
}

export function buildPointInTimeUniverse({ records = [], asOf } = {}) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  const asOfTimestamp = toTimestamp(asOf);
  if (asOfTimestamp === null) throw new TypeError("asOf must be a valid timestamp");

  const normalized = records.map(normalizeRecord).filter((record) => record.symbol && record.listedAt !== null);
  const active = normalized.filter((record) => {
    const listed = record.listedAt <= asOfTimestamp;
    const notYetDelisted = record.delistedAt === null || record.delistedAt > asOfTimestamp;
    return listed && notYetDelisted;
  });

  const duplicateSymbols = [];
  const seen = new Set();
  for (const record of active) {
    if (seen.has(record.symbol)) duplicateSymbols.push(record.symbol);
    seen.add(record.symbol);
  }

  return {
    version: SURVIVORSHIP_UNIVERSE_VERSION,
    asOf: new Date(asOfTimestamp).toISOString(),
    symbols: [...new Set(active.map((record) => record.symbol))].sort(),
    records: active,
    diagnostics: {
      sourceCount: records.length,
      normalizedCount: normalized.length,
      activeCount: active.length,
      duplicateSymbols: [...new Set(duplicateSymbols)].sort(),
      excludedFutureListings: normalized.filter((record) => record.listedAt > asOfTimestamp).length,
      excludedDelisted: normalized.filter((record) => record.delistedAt !== null && record.delistedAt <= asOfTimestamp).length,
    },
    safety: {
      survivorshipBiasChecked: true,
      executionAllowed: false,
      brokerWriteAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export function assertSymbolInUniverse(symbol, universe) {
  const normalized = cleanSymbol(symbol);
  if (!universe?.symbols?.includes(normalized)) {
    throw new Error(`SYMBOL_NOT_IN_POINT_IN_TIME_UNIVERSE:${normalized || "UNKNOWN"}`);
  }
  return true;
}

export default buildPointInTimeUniverse;
