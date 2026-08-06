export const DATA_QUALITY_GATE_VERSION = "data-quality-gate-v1";

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function timestamp(value) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeSymbol(row = {}) {
  return String(row.symbol ?? row.ticker ?? row.code ?? "").trim().toUpperCase();
}

export function evaluateDataQuality({ rows = [], expectedSymbol = null, now = Date.now(), staleAfterMs = 15 * 60 * 1000 } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");

  const issues = [];
  const warnings = [];
  const seen = new Set();
  let previousTime = null;

  rows.forEach((row, index) => {
    const symbol = normalizeSymbol(row);
    const time = timestamp(row.time ?? row.timestamp ?? row.date);
    const close = Number(row.close ?? row.price);
    const volume = Number(row.volume ?? 0);
    const key = `${symbol}|${time}`;

    if (!symbol) issues.push({ code: "MISSING_SYMBOL", index });
    if (expectedSymbol && symbol && symbol !== String(expectedSymbol).trim().toUpperCase()) {
      issues.push({ code: "CROSS_SYMBOL_ROW", index, symbol });
    }
    if (time === null) issues.push({ code: "INVALID_TIMESTAMP", index });
    if (!finite(close) || close <= 0) issues.push({ code: "INVALID_PRICE", index, value: row.close ?? row.price });
    if (!finite(volume) || volume < 0) issues.push({ code: "INVALID_VOLUME", index, value: row.volume });
    if (seen.has(key)) issues.push({ code: "DUPLICATE_ROW", index, key });
    if (time !== null) {
      if (previousTime !== null && time < previousTime) issues.push({ code: "TIME_REVERSED", index });
      previousTime = time;
      if (now - time > staleAfterMs) warnings.push({ code: "STALE_DATA", index, ageMs: now - time });
    }
    seen.add(key);
  });

  const status = issues.length ? "BLOCKED" : warnings.length ? "WARNING" : "PASS";
  return {
    version: DATA_QUALITY_GATE_VERSION,
    status,
    blocked: status === "BLOCKED",
    issues,
    warnings,
    diagnostics: {
      sourceRows: rows.length,
      uniqueRows: seen.size,
      issueCount: issues.length,
      warningCount: warnings.length,
    },
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export function assertDataQuality(result) {
  if (!result || result.status === "BLOCKED") throw new Error("DATA_QUALITY_BLOCKED");
  return true;
}

export default evaluateDataQuality;
