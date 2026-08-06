const ALLOWED_KINDS = new Set(["OHLCV", "INDEX", "MACRO"]);

export const PHASE45_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

export const PHASE45_BENCHMARKS = Object.freeze([
  { symbol: "NIKKEI225", kind: "INDEX", currency: "JPY" },
  { symbol: "TOPIX", kind: "INDEX", currency: "JPY" },
  { symbol: "NASDAQ", kind: "INDEX", currency: "USD" },
  { symbol: "SOX", kind: "INDEX", currency: "USD" },
  { symbol: "VIX", kind: "INDEX", currency: "USD" },
  { symbol: "USDJPY", kind: "MACRO", currency: "JPY" },
]);

function text(value) {
  return String(value ?? "").trim();
}

function finiteNumber(value, field) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new TypeError(`${field} must be a finite number`);
  return number;
}

function isoDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new TypeError("sessionDate must be a valid date");
  return date.toISOString().slice(0, 10);
}

export function createPhase45Universe({ equities = [], version = "phase45-v1" } = {}) {
  if (!Array.isArray(equities)) throw new TypeError("equities must be an array");
  if (equities.length < 1 || equities.length > 50) {
    throw new RangeError("initial Phase45 universe must contain 1 to 50 equities");
  }

  const normalized = equities.map((item) => {
    const symbol = text(typeof item === "string" ? item : item?.symbol).toUpperCase();
    if (!/^\d{4,5}\.T$/.test(symbol)) throw new TypeError(`invalid TSE symbol: ${symbol}`);
    return Object.freeze({ symbol, kind: "OHLCV", currency: "JPY" });
  });

  const symbols = normalized.map((item) => item.symbol);
  if (new Set(symbols).size !== symbols.length) throw new TypeError("duplicate equity symbol");

  return Object.freeze({
    schemaVersion: 1,
    version: text(version) || "phase45-v1",
    equities: Object.freeze(normalized),
    benchmarks: PHASE45_BENCHMARKS,
    safety: PHASE45_SAFETY,
  });
}

export function normalizeHistoricalRecord(row, defaults = {}) {
  if (!row || typeof row !== "object") throw new TypeError("row must be an object");
  const kind = text(row.kind ?? defaults.kind ?? "OHLCV").toUpperCase();
  if (!ALLOWED_KINDS.has(kind)) throw new TypeError(`unsupported kind: ${kind}`);

  const symbol = text(row.symbol ?? row.ticker ?? defaults.symbol).toUpperCase();
  if (!symbol) throw new TypeError("symbol is required");

  const base = {
    kind,
    symbol,
    sessionDate: isoDate(row.sessionDate ?? row.date ?? row.Date),
    updatedAt: new Date(row.updatedAt ?? defaults.updatedAt ?? Date.now()).toISOString(),
    source: text(row.source ?? defaults.source ?? "PHASE45"),
    currency: text(row.currency ?? defaults.currency ?? (kind === "OHLCV" ? "JPY" : "USD")),
  };

  if (kind !== "OHLCV") {
    return Object.freeze({ ...base, value: finiteNumber(row.value ?? row.close ?? row.Close, "value") });
  }

  return Object.freeze({
    ...base,
    open: finiteNumber(row.open ?? row.Open, "open"),
    high: finiteNumber(row.high ?? row.High, "high"),
    low: finiteNumber(row.low ?? row.Low, "low"),
    close: finiteNumber(row.close ?? row.Close, "close"),
    adjustedClose: finiteNumber(row.adjustedClose ?? row.adjClose ?? row["Adj Close"] ?? row.close ?? row.Close, "adjustedClose"),
    volume: finiteNumber(row.volume ?? row.Volume, "volume"),
  });
}

export function inspectHistoricalRecords(records = [], { maxGapDays = 10 } = {}) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");

  const normalized = [];
  const blockers = [];
  const warnings = [];
  const seen = new Set();
  const lastDateBySymbol = new Map();

  records.forEach((row, index) => {
    try {
      const record = normalizeHistoricalRecord(row);
      const key = `${record.kind}:${record.symbol}:${record.sessionDate}`;
      if (seen.has(key)) {
        blockers.push({ code: "DUPLICATE_RECORD", index, key });
        return;
      }
      seen.add(key);

      if (record.kind === "OHLCV") {
        if (record.low > record.high) blockers.push({ code: "LOW_ABOVE_HIGH", index, key });
        if (record.open < record.low || record.open > record.high) blockers.push({ code: "OPEN_OUTSIDE_RANGE", index, key });
        if (record.close < record.low || record.close > record.high) blockers.push({ code: "CLOSE_OUTSIDE_RANGE", index, key });
        if (record.volume < 0) blockers.push({ code: "NEGATIVE_VOLUME", index, key });
        if (record.adjustedClose <= 0 || record.close <= 0) blockers.push({ code: "NON_POSITIVE_PRICE", index, key });
      }

      const previous = lastDateBySymbol.get(record.symbol);
      const current = Date.parse(record.sessionDate);
      if (previous && current > previous) {
        const gapDays = Math.round((current - previous) / 86400000);
        if (gapDays > maxGapDays) warnings.push({ code: "LARGE_DATE_GAP", symbol: record.symbol, gapDays });
      }
      lastDateBySymbol.set(record.symbol, Math.max(previous ?? 0, current));
      normalized.push(record);
    } catch (error) {
      blockers.push({ code: "NORMALIZATION_FAILED", index, message: String(error?.message || error) });
    }
  });

  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "VALID",
    normalizedRecords: Object.freeze(normalized),
    blockers: Object.freeze(blockers),
    warnings: Object.freeze(warnings),
    recordCount: normalized.length,
    safety: PHASE45_SAFETY,
  });
}

export function buildHistoricalIngestionBatch({ records = [], provider = "GENERIC" } = {}) {
  const inspection = inspectHistoricalRecords(records);
  if (inspection.status !== "VALID") {
    return Object.freeze({ status: "BLOCKED", provider: text(provider).toUpperCase(), inspection, records: Object.freeze([]), safety: PHASE45_SAFETY });
  }
  return Object.freeze({
    status: "READY_FOR_PHASE41",
    provider: text(provider).toUpperCase(),
    inspection,
    records: inspection.normalizedRecords,
    safety: PHASE45_SAFETY,
  });
}
