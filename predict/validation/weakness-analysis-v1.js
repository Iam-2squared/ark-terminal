export const WEAKNESS_ANALYSIS_V1 = "weakness-analysis-v1";

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function summarize(rows = []) {
  const valid = rows.filter((row) => row?.correct !== undefined);
  const correct = valid.filter((row) => row.correct === true).length;
  const accuracy = valid.length ? correct / valid.length : 0;
  const avgConfidence = valid.length
    ? valid.reduce((sum, row) => sum + finite(row.confidence), 0) / valid.length
    : 0;
  return {
    sampleSize: valid.length,
    accuracy,
    averageConfidence: avgConfidence,
    calibrationGap: valid.length ? Math.abs(avgConfidence / 100 - accuracy) : 0,
  };
}

function breakdown(records, key) {
  const groups = new Map();
  for (const row of records) {
    const value = row?.[key] ?? "UNKNOWN";
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(row);
  }
  return [...groups.entries()]
    .map(([name, rows]) => ({ name, ...summarize(rows) }))
    .sort((a, b) => a.accuracy - b.accuracy);
}

export function analyzeWeaknessV1({ records = [], minimumSampleSize = 5 } = {}) {
  const bySymbol = breakdown(records, "symbol");
  const bySector = breakdown(records, "sector");
  const byRegime = breakdown(records, "regime");
  const byConfidenceBand = breakdown(records.map((row) => ({
    ...row,
    confidenceBand: `${Math.floor(finite(row.confidence) / 10) * 10}-${Math.floor(finite(row.confidence) / 10) * 10 + 9}`,
  })), "confidenceBand");
  const weak = [...bySymbol, ...bySector, ...byRegime]
    .filter((row) => row.sampleSize >= minimumSampleSize && row.accuracy < 0.5);
  const overconfident = byConfidenceBand
    .filter((row) => row.sampleSize >= minimumSampleSize && row.calibrationGap >= 0.15);
  const noTradeRate = records.length
    ? records.filter((row) => String(row.action).toUpperCase() === "NO_TRADE").length / records.length
    : 0;

  return {
    version: WEAKNESS_ANALYSIS_V1,
    generatedAt: new Date().toISOString(),
    status: records.length ? "READY" : "BLOCKED",
    overall: summarize(records),
    bySymbol,
    bySector,
    byRegime,
    byConfidenceBand,
    weakSegments: weak,
    overconfidentBands: overconfident,
    noTradeRate,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  };
}

export default analyzeWeaknessV1;
