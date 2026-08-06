export const MODEL_SEGMENTATION_VERSION = "phase24-model-segmentation-v1";

const normalize = (value, fallback = "UNKNOWN") => String(value ?? fallback).trim().toUpperCase() || fallback;
const finite = (value) => Number.isFinite(Number(value));

export function buildModelSegment(row = {}) {
  const action = normalize(row.signal ?? row.action ?? row.decision?.action, "NON_DIRECTIONAL");
  const horizon = Number(row.evaluationHorizon ?? row.horizon ?? row.period);
  const regime = normalize(row.marketRegime ?? row.regime);
  const industry = normalize(row.industry ?? row.sector);

  let horizonBucket = "UNKNOWN";
  if (Number.isInteger(horizon) && horizon > 0) {
    if (horizon <= 3) horizonBucket = "SHORT";
    else if (horizon <= 10) horizonBucket = "MEDIUM";
    else horizonBucket = "LONG";
  }

  return {
    version: MODEL_SEGMENTATION_VERSION,
    action: ["BUY", "SELL"].includes(action) ? action : "NON_DIRECTIONAL",
    horizon: finite(horizon) ? Number(horizon) : null,
    horizonBucket,
    regime,
    industry,
    key: [action, horizonBucket, regime, industry].join("::"),
  };
}

export function segmentRows(rows = []) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  const groups = new Map();
  for (const row of rows) {
    const segment = buildModelSegment(row);
    if (!groups.has(segment.key)) groups.set(segment.key, { segment, rows: [] });
    groups.get(segment.key).rows.push(row);
  }
  return [...groups.values()].sort((a, b) => a.segment.key.localeCompare(b.segment.key));
}

export default segmentRows;
