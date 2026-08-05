export const CONTINUOUS_ACCURACY_V1 = "continuous-accuracy-v1";

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function group(records, key) {
  const map = new Map();
  for (const row of records) {
    const value = row?.[key] ?? "UNKNOWN";
    if (!map.has(value)) map.set(value, []);
    map.get(value).push(row);
  }
  return map;
}

function summarize(records = []) {
  const valid = records.filter((row) => finite(row?.outcome) !== null);
  const correct = valid.filter((row) => Boolean(row.correct) === true).length;
  const avgConfidence = valid.length
    ? valid.reduce((sum, row) => sum + (finite(row.confidence, 0) ?? 0), 0) / valid.length
    : 0;
  return {
    sampleSize: valid.length,
    accuracy: valid.length ? correct / valid.length : 0,
    averageConfidence: avgConfidence,
    calibrationGap: valid.length ? Math.abs(avgConfidence / 100 - correct / valid.length) : 0,
  };
}

export function analyzeContinuousAccuracyV1({ records = [], previous = null } = {}) {
  const overall = summarize(records);
  const breakdown = (key) => [...group(records, key).entries()]
    .map(([name, rows]) => ({ name, ...summarize(rows) }))
    .sort((a, b) => a.accuracy - b.accuracy);

  const byAction = breakdown("action");
  const bySymbol = breakdown("symbol");
  const bySector = breakdown("sector");
  const byRegime = breakdown("regime");
  const lowAccuracySegments = [...byAction, ...bySector, ...byRegime]
    .filter((row) => row.sampleSize >= 5 && row.accuracy < 0.5)
    .sort((a, b) => a.accuracy - b.accuracy);

  const previousAccuracy = finite(previous?.accuracy, null);
  const drift = previousAccuracy === null ? null : overall.accuracy - previousAccuracy;
  const suggestions = [
    ...(overall.calibrationGap > 0.15 ? ["RECALIBRATE_CONFIDENCE"] : []),
    ...(lowAccuracySegments.length ? ["REVIEW_WEAK_SEGMENTS"] : []),
    ...(drift !== null && drift < -0.05 ? ["INVESTIGATE_ACCURACY_DRIFT"] : []),
  ];

  return {
    version: CONTINUOUS_ACCURACY_V1,
    generatedAt: new Date().toISOString(),
    status: records.length ? "READY" : "BLOCKED",
    overall,
    byAction,
    bySymbol,
    bySector,
    byRegime,
    lowAccuracySegments,
    drift,
    suggestions,
    improvementCandidateGenerated: suggestions.length > 0,
    productionUpdateAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default analyzeContinuousAccuracyV1;
