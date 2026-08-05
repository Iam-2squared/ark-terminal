export const DAILY_DATA_UPDATE_V1 = "daily-data-update-v1";

function iso(value) {
  const time = Date.parse(value);
  return Number.isFinite(time) ? new Date(time).toISOString() : null;
}

function summarizeSource(source = {}) {
  const rows = Array.isArray(source.rows) ? source.rows : [];
  const validRows = rows.filter((row) => iso(row?.timestamp));
  const futureRows = validRows.filter((row) => source.asOf && Date.parse(row.timestamp) > Date.parse(source.asOf));
  return {
    name: source.name ?? "UNKNOWN",
    status: source.error ? "FAILED" : futureRows.length ? "BLOCKED" : validRows.length ? "READY" : "EMPTY",
    rowCount: rows.length,
    validRowCount: validRows.length,
    futureRowCount: futureRows.length,
    error: source.error ?? null,
    updatedAt: source.updatedAt ?? null,
  };
}

export function runDailyDataUpdateV1({ sources = [], asOf = new Date().toISOString() } = {}) {
  const normalized = sources.map((source) => summarizeSource({ ...source, asOf }));
  const failed = normalized.filter((source) => source.status === "FAILED");
  const blocked = normalized.filter((source) => source.status === "BLOCKED");
  const empty = normalized.filter((source) => source.status === "EMPTY");
  const rollbackRequired = failed.length > 0 || blocked.length > 0;

  return {
    version: DAILY_DATA_UPDATE_V1,
    generatedAt: new Date().toISOString(),
    asOf,
    status: rollbackRequired ? "BLOCKED" : empty.length ? "DEGRADED" : "READY",
    sources: normalized,
    summary: {
      sourceCount: normalized.length,
      ready: normalized.filter((source) => source.status === "READY").length,
      failed: failed.length,
      blocked: blocked.length,
      empty: empty.length,
    },
    rollbackRequired,
    commitAllowed: !rollbackRequired,
    productionUpdateAllowed: !rollbackRequired,
    brokerExecutionAllowed: false,
  };
}

export default runDailyDataUpdateV1;
