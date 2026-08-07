import { inspectHistoricalRecords, PHASE45_SAFETY } from "./phase45-historical-data.js";

export const PHASE50_DOWNLOADER_SAFETY = Object.freeze({
  ...PHASE45_SAFETY,
  networkReadOnly: true,
  externalWriteAllowed: false,
});

export const YAHOO_MINOR_RANGE_TOLERANCE = 0.11;
export const YAHOO_QUARANTINE_RELATIVE_TOLERANCE = 0.001;

export const DEFAULT_BENCHMARK_MAP = Object.freeze({
  NIKKEI225: { providerSymbol: "^N225", kind: "INDEX", currency: "JPY" },
  TOPIX: { providerSymbol: "^TOPX", kind: "INDEX", currency: "JPY" },
  NASDAQ: { providerSymbol: "^IXIC", kind: "INDEX", currency: "USD" },
  SOX: { providerSymbol: "^SOX", kind: "INDEX", currency: "USD" },
  VIX: { providerSymbol: "^VIX", kind: "INDEX", currency: "USD" },
  USDJPY: { providerSymbol: "JPY=X", kind: "MACRO", currency: "JPY" },
});

function toUnixSeconds(value) {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) throw new TypeError(`invalid date: ${value}`);
  return Math.floor(time / 1000);
}

export function buildYahooChartUrl({ symbol, start, end, interval = "1d" }) {
  if (!symbol) throw new TypeError("symbol is required");
  const period1 = toUnixSeconds(start);
  const period2 = toUnixSeconds(end);
  if (period2 <= period1) throw new RangeError("end must be after start");
  return `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?period1=${period1}&period2=${period2}&interval=${encodeURIComponent(interval)}&events=div%2Csplits&includeAdjustedClose=true`;
}

function isoDateFromUnix(seconds) {
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}

function yahooRangeViolation(record) {
  if (record.kind !== "OHLCV" || record.source !== "YAHOO_CHART") return null;
  const violations = [];
  for (const [field, value] of [["open", record.open], ["close", record.close]]) {
    if (value < record.low) violations.push({ field, boundary: "low", delta: record.low - value });
    if (value > record.high) violations.push({ field, boundary: "high", delta: value - record.high });
  }
  if (!violations.length) return null;
  const scale = Math.max(Math.abs(record.open), Math.abs(record.high), Math.abs(record.low), Math.abs(record.close), 1);
  const maxDelta = Math.max(...violations.map((item) => item.delta));
  return { violations, maxDelta, relativeDelta: maxDelta / scale };
}

function normalizeMinorYahooRangeDrift(record, tolerance = YAHOO_MINOR_RANGE_TOLERANCE) {
  if (record.kind !== "OHLCV" || record.source !== "YAHOO_CHART") return { record, warnings: [] };

  const original = { open: record.open, high: record.high, low: record.low, close: record.close };
  let { open, high, low, close } = record;
  const warnings = [];

  const adjustLow = (field, value) => {
    const delta = low - value;
    if (delta > 0 && delta <= tolerance) {
      warnings.push({
        code: "MINOR_RANGE_ADJUSTMENT",
        symbol: record.symbol,
        sessionDate: record.sessionDate,
        field,
        boundary: "low",
        delta,
        originalValue: value,
        originalBoundary: low,
        adjustedBoundary: value,
      });
      low = value;
    }
  };

  const adjustHigh = (field, value) => {
    const delta = value - high;
    if (delta > 0 && delta <= tolerance) {
      warnings.push({
        code: "MINOR_RANGE_ADJUSTMENT",
        symbol: record.symbol,
        sessionDate: record.sessionDate,
        field,
        boundary: "high",
        delta,
        originalValue: value,
        originalBoundary: high,
        adjustedBoundary: value,
      });
      high = value;
    }
  };

  adjustLow("open", open);
  adjustHigh("open", open);
  adjustLow("close", close);
  adjustHigh("close", close);

  if (warnings.length === 0) return { record, warnings };
  return {
    record: {
      ...record,
      open,
      high,
      low,
      close,
      normalizationAudit: {
        rule: "YAHOO_MINOR_RANGE_TOLERANCE",
        tolerance,
        original,
      },
    },
    warnings,
  };
}

function quarantineSingleMinorYahooRangeRow(records, relativeTolerance = YAHOO_QUARANTINE_RELATIVE_TOLERANCE) {
  const violations = records
    .map((record, index) => ({ record, index, violation: yahooRangeViolation(record) }))
    .filter((item) => item.violation);

  // Quarantine is intentionally stricter than the legacy absolute adjustment:
  // exactly one Yahoo OHLCV row in the entire series may be inconsistent, and that
  // one row must remain within the relative drift tolerance. Any second violation,
  // even if individually tiny, is left untouched so Phase45 blocks fail-closed.
  if (violations.length !== 1) return { records, warnings: [], quarantined: [] };
  const candidate = violations[0];
  if (candidate.violation.relativeDelta > relativeTolerance) {
    return { records, warnings: [], quarantined: [] };
  }

  const remaining = records.filter((_, index) => index !== candidate.index);
  return {
    records: remaining,
    warnings: [{
      code: "QUARANTINED_RANGE_DRIFT",
      symbol: candidate.record.symbol,
      sessionDate: candidate.record.sessionDate,
      relativeTolerance,
      maxDelta: candidate.violation.maxDelta,
      relativeDelta: candidate.violation.relativeDelta,
      violations: candidate.violation.violations,
      originalRecord: candidate.record,
    }],
    quarantined: [candidate.record],
  };
}

export function normalizeYahooChartPayload(payload, { symbol, outputSymbol = symbol, kind = "OHLCV", currency = "JPY", source = "YAHOO_CHART" } = {}) {
  const result = payload?.chart?.result?.[0];
  const timestamps = result?.timestamp;
  const quote = result?.indicators?.quote?.[0];
  const adjusted = result?.indicators?.adjclose?.[0]?.adjclose;
  if (!Array.isArray(timestamps) || !quote) throw new TypeError("invalid chart payload");

  const records = [];
  for (let index = 0; index < timestamps.length; index += 1) {
    const close = quote.close?.[index];
    if (!Number.isFinite(close)) continue;
    const base = {
      kind,
      symbol: outputSymbol,
      sessionDate: isoDateFromUnix(timestamps[index]),
      source,
      currency,
    };
    if (kind !== "OHLCV") {
      records.push({ ...base, value: close });
      continue;
    }
    const open = quote.open?.[index];
    const high = quote.high?.[index];
    const low = quote.low?.[index];
    const volume = quote.volume?.[index];
    if ([open, high, low].some((value) => !Number.isFinite(value))) continue;
    records.push({
      ...base,
      open,
      high,
      low,
      close,
      adjustedClose: Number.isFinite(adjusted?.[index]) ? adjusted[index] : close,
      volume: Number.isFinite(volume) ? volume : 0,
    });
  }
  return records;
}

export async function downloadHistoricalSeries({ symbol, outputSymbol = symbol, start, end, interval = "1d", fetchImpl = fetch, kind = "OHLCV", currency = "JPY" }) {
  const url = buildYahooChartUrl({ symbol, start, end, interval });
  const response = await fetchImpl(url, { method: "GET", headers: { accept: "application/json" } });
  if (!response?.ok) throw new Error(`historical download failed: ${response?.status ?? "unknown"}`);
  const payload = await response.json();
  const rawRecords = normalizeYahooChartPayload(payload, { symbol, outputSymbol, kind, currency });
  if (!rawRecords.length) throw new Error("historical download returned no valid records");

  // First preserve strict fail-closed behavior for materially inconsistent rows while
  // quarantining a single small Yahoo-specific relative drift. Only after quarantine
  // do we apply the legacy absolute float adjustment for sub-0.11 price-unit noise.
  const quarantine = quarantineSingleMinorYahooRangeRow(rawRecords);
  if (!quarantine.records.length) throw new Error("historical download returned no valid records after quarantine");

  const adjustmentWarnings = [];
  const adjustedRecords = quarantine.records.map((record) => {
    const normalized = normalizeMinorYahooRangeDrift(record);
    adjustmentWarnings.push(...normalized.warnings);
    return normalized.record;
  });

  const inspection = inspectHistoricalRecords(adjustedRecords);
  const allWarnings = Object.freeze([...quarantine.warnings, ...adjustmentWarnings, ...inspection.warnings]);
  if (inspection.status !== "VALID") {
    const error = new Error("DOWNLOADED_DATA_BLOCKED");
    error.inspection = { ...inspection, warnings: allWarnings };
    throw error;
  }
  return Object.freeze({
    symbol: outputSymbol,
    providerSymbol: symbol,
    url,
    records: inspection.normalizedRecords,
    warnings: allWarnings,
    quarantined: Object.freeze(quarantine.quarantined),
    safety: PHASE50_DOWNLOADER_SAFETY,
  });
}

export async function downloadHistoricalUniverse({ instruments, start, end, interval = "1d", fetchImpl = fetch, concurrency = 3 }) {
  if (!Array.isArray(instruments) || instruments.length === 0) throw new TypeError("instruments are required");
  const results = [];
  const failures = [];
  let cursor = 0;

  async function worker() {
    while (cursor < instruments.length) {
      const current = instruments[cursor++];
      try {
        results.push(await downloadHistoricalSeries({ ...current, start, end, interval, fetchImpl }));
      } catch (error) {
        failures.push({
          symbol: current.outputSymbol ?? current.symbol,
          message: String(error?.message || error),
          blockers: error?.inspection?.blockers ?? [],
          warnings: error?.inspection?.warnings ?? [],
          recordCount: error?.inspection?.recordCount ?? null,
        });
      }
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, Math.min(concurrency, instruments.length)) }, worker));
  if (failures.length) {
    const error = new Error("HISTORICAL_UNIVERSE_DOWNLOAD_BLOCKED");
    error.failures = failures;
    throw error;
  }
  return Object.freeze({
    status: "READY_FOR_PHASE45",
    records: Object.freeze(results.flatMap((item) => item.records)),
    symbols: Object.freeze(results.map((item) => item.symbol)),
    warnings: Object.freeze(results.flatMap((item) => item.warnings)),
    quarantined: Object.freeze(results.flatMap((item) => item.quarantined)),
    safety: PHASE50_DOWNLOADER_SAFETY,
  });
}
