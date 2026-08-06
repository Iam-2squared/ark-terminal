import { inspectHistoricalRecords, PHASE45_SAFETY } from "./phase45-historical-data.js";

export const PHASE50_DOWNLOADER_SAFETY = Object.freeze({
  ...PHASE45_SAFETY,
  networkReadOnly: true,
  externalWriteAllowed: false,
});

export const DEFAULT_BENCHMARK_MAP = Object.freeze({
  NIKKEI225: "^N225",
  NASDAQ: "^IXIC",
  SOX: "^SOX",
  VIX: "^VIX",
  USDJPY: "JPY=X",
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
  const encoded = encodeURIComponent(symbol);
  return `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?period1=${period1}&period2=${period2}&interval=${encodeURIComponent(interval)}&events=div%2Csplits&includeAdjustedClose=true`;
}

function isoDateFromUnix(seconds) {
  return new Date(seconds * 1000).toISOString().slice(0, 10);
}

export function normalizeYahooChartPayload(payload, { symbol, kind = "OHLCV", currency = "JPY", source = "YAHOO_CHART" } = {}) {
  const result = payload?.chart?.result?.[0];
  const timestamps = result?.timestamp;
  const quote = result?.indicators?.quote?.[0];
  const adjusted = result?.indicators?.adjclose?.[0]?.adjclose;
  if (!Array.isArray(timestamps) || !quote) throw new TypeError("invalid chart payload");

  const records = [];
  for (let index = 0; index < timestamps.length; index += 1) {
    const open = quote.open?.[index];
    const high = quote.high?.[index];
    const low = quote.low?.[index];
    const close = quote.close?.[index];
    const volume = quote.volume?.[index];
    if ([open, high, low, close].some((value) => !Number.isFinite(value))) continue;
    records.push({
      kind,
      symbol,
      sessionDate: isoDateFromUnix(timestamps[index]),
      open,
      high,
      low,
      close,
      adjustedClose: Number.isFinite(adjusted?.[index]) ? adjusted[index] : close,
      volume: Number.isFinite(volume) ? volume : 0,
      source,
      currency,
    });
  }
  return records;
}

export async function downloadHistoricalSeries({ symbol, start, end, interval = "1d", fetchImpl = fetch, kind = "OHLCV", currency = "JPY" }) {
  const url = buildYahooChartUrl({ symbol, start, end, interval });
  const response = await fetchImpl(url, { method: "GET", headers: { accept: "application/json" } });
  if (!response?.ok) throw new Error(`historical download failed: ${response?.status ?? "unknown"}`);
  const payload = await response.json();
  const records = normalizeYahooChartPayload(payload, { symbol, kind, currency });
  const inspection = inspectHistoricalRecords(records);
  if (inspection.status !== "VALID") {
    const error = new Error("DOWNLOADED_DATA_BLOCKED");
    error.inspection = inspection;
    throw error;
  }
  return Object.freeze({ symbol, url, records: inspection.normalizedRecords, warnings: inspection.warnings, safety: PHASE50_DOWNLOADER_SAFETY });
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
        failures.push({ symbol: current.symbol, message: String(error?.message || error) });
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
    safety: PHASE50_DOWNLOADER_SAFETY,
  });
}
