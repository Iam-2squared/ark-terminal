export const HISTORICAL_DATA_PIPELINE_V1 = "historical-data-pipeline-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function iso(value) {
  const time = Date.parse(value);
  return Number.isFinite(time) ? new Date(time).toISOString() : null;
}

function dedupe(rows = []) {
  const map = new Map();
  for (const row of rows) {
    const key = `${row?.symbol ?? "UNKNOWN"}|${iso(row?.timestamp) ?? "INVALID"}`;
    map.set(key, row);
  }
  return [...map.values()];
}

export function buildHistoricalDatasetV1({ rows = [], corporateActions = [], asOf = null } = {}) {
  const actionMap = new Map();
  for (const action of corporateActions) {
    const symbol = action?.symbol ?? "UNKNOWN";
    if (!actionMap.has(symbol)) actionMap.set(symbol, []);
    actionMap.get(symbol).push(action);
  }

  const unique = dedupe(rows);
  const normalized = unique.map((row) => {
    const symbol = row?.symbol ?? "UNKNOWN";
    const timestamp = iso(row?.timestamp);
    let splitFactor = 1;
    for (const action of actionMap.get(symbol) ?? []) {
      const effectiveAt = iso(action?.effectiveAt);
      const ratio = finite(action?.splitRatio, 1) ?? 1;
      if (timestamp && effectiveAt && timestamp < effectiveAt && ratio > 0) splitFactor *= ratio;
    }
    const close = finite(row?.close);
    const volume = finite(row?.volume);
    return {
      ...row,
      symbol,
      timestamp,
      adjustedClose: close === null ? null : close / splitFactor,
      adjustedVolume: volume === null ? null : volume * splitFactor,
      splitFactor,
    };
  }).sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)) || String(a.symbol).localeCompare(String(b.symbol)));

  const invalidRows = normalized.filter((row) => !row.timestamp || row.adjustedClose === null || row.adjustedVolume === null).length;
  const futureLeakDetected = Boolean(asOf) && normalized.some((row) => row.timestamp && Date.parse(row.timestamp) > Date.parse(asOf));
  const duplicateRowsRemoved = rows.length - unique.length;
  const symbols = [...new Set(normalized.map((row) => row.symbol))];

  return {
    version: HISTORICAL_DATA_PIPELINE_V1,
    generatedAt: new Date().toISOString(),
    status: futureLeakDetected ? "BLOCKED" : invalidRows ? "DEGRADED" : "READY",
    rows: normalized,
    metadata: {
      rowCount: normalized.length,
      symbolCount: symbols.length,
      symbols,
      duplicateRowsRemoved,
      invalidRows,
      futureLeakDetected,
    },
    productionUpdateAllowed: false,
  };
}

export default buildHistoricalDatasetV1;
