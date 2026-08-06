import crypto from "node:crypto";

export const PHASE46_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number)) throw new TypeError(`${name} must be finite`);
  return number;
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function std(values) {
  const avg = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - avg) ** 2)));
}

function round(value, digits = 8) {
  return Number(value.toFixed(digits));
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function checksum(value) {
  return crypto.createHash("sha256").update(canonical(value)).digest("hex");
}

export function buildPointInTimeRows(records = [], { horizon = 5, minHistory = 20 } = {}) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  if (!Number.isInteger(horizon) || horizon < 1) throw new RangeError("horizon must be >= 1");

  const grouped = new Map();
  for (const row of records) {
    if (row?.kind !== "OHLCV") continue;
    const symbol = String(row.symbol || "").trim().toUpperCase();
    if (!symbol) throw new TypeError("symbol is required");
    const normalized = {
      symbol,
      sessionDate: String(row.sessionDate),
      open: finite(row.open, "open"),
      high: finite(row.high, "high"),
      low: finite(row.low, "low"),
      close: finite(row.close, "close"),
      adjustedClose: finite(row.adjustedClose ?? row.close, "adjustedClose"),
      volume: finite(row.volume, "volume"),
    };
    if (!grouped.has(symbol)) grouped.set(symbol, []);
    grouped.get(symbol).push(normalized);
  }

  const rows = [];
  for (const [symbol, series] of grouped) {
    series.sort((a, b) => a.sessionDate.localeCompare(b.sessionDate));
    for (let index = minHistory - 1; index + horizon < series.length; index += 1) {
      const history = series.slice(0, index + 1);
      const current = series[index];
      const closes = history.map((row) => row.adjustedClose);
      const volumes = history.map((row) => row.volume);
      const future = series[index + horizon];
      const ma5 = mean(closes.slice(-5));
      const ma20 = mean(closes.slice(-20));
      const returns = closes.slice(-20).slice(1).map((value, i) => value / closes.slice(-20)[i] - 1);
      const volume20 = mean(volumes.slice(-20));
      const futureReturn = future.adjustedClose / current.adjustedClose - 1;

      rows.push(Object.freeze({
        symbol,
        asOfDate: current.sessionDate,
        horizon,
        features: Object.freeze({
          close: round(current.adjustedClose),
          ma5Ratio: round(current.adjustedClose / ma5 - 1),
          ma20Ratio: round(current.adjustedClose / ma20 - 1),
          momentum5: round(current.adjustedClose / closes.at(-6) - 1),
          volatility20: round(std(returns)),
          volumeRatio20: round(volume20 === 0 ? 0 : current.volume / volume20),
          intradayRange: round((current.high - current.low) / current.close),
        }),
        label: Object.freeze({
          futureDate: future.sessionDate,
          futureReturn: round(futureReturn),
          direction: futureReturn > 0 ? 1 : 0,
        }),
        pointInTime: Object.freeze({
          featureCutoff: current.sessionDate,
          labelAvailableAt: future.sessionDate,
          futureDataUsedInFeatures: false,
        }),
      }));
    }
  }
  return Object.freeze(rows);
}

export function buildTrainingDataset({ records = [], datasetVersion = "phase46-v1", horizon = 5, minHistory = 20 } = {}) {
  const rows = buildPointInTimeRows(records, { horizon, minHistory });
  const payload = {
    schemaVersion: 1,
    datasetVersion,
    horizon,
    minHistory,
    rowCount: rows.length,
    rows,
    safety: PHASE46_SAFETY,
  };
  return Object.freeze({ ...payload, checksum: checksum(payload) });
}

export function auditTrainingDataset(dataset) {
  const blockers = [];
  if (!dataset || typeof dataset !== "object") blockers.push("DATASET_REQUIRED");
  const rows = Array.isArray(dataset?.rows) ? dataset.rows : [];
  const seen = new Set();
  for (const row of rows) {
    const key = `${row.symbol}:${row.asOfDate}:${row.horizon}`;
    if (seen.has(key)) blockers.push(`DUPLICATE_ROW:${key}`);
    seen.add(key);
    if (row.pointInTime?.futureDataUsedInFeatures !== false) blockers.push(`FUTURE_LEAK:${key}`);
    if (!(row.pointInTime?.featureCutoff < row.pointInTime?.labelAvailableAt)) blockers.push(`INVALID_TEMPORAL_ORDER:${key}`);
  }
  const expected = dataset ? checksum({
    schemaVersion: dataset.schemaVersion,
    datasetVersion: dataset.datasetVersion,
    horizon: dataset.horizon,
    minHistory: dataset.minHistory,
    rowCount: dataset.rowCount,
    rows: dataset.rows,
    safety: dataset.safety,
  }) : null;
  if (dataset?.checksum !== expected) blockers.push("CHECKSUM_MISMATCH");
  return Object.freeze({
    status: blockers.length ? "BLOCKED" : "VALID",
    blockers: Object.freeze(blockers),
    rowCount: rows.length,
    checksum: expected,
    safety: PHASE46_SAFETY,
  });
}
