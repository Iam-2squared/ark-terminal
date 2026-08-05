export const CONFIDENCE_CALIBRATION_V1_VERSION = "confidence-calibration-v1";

function probability(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.max(0, Math.min(1, n > 1 ? n / 100 : n));
}

function isTrade(record = {}) {
  const action = String(
    record.action ?? record.decision ?? record.signal ?? "",
  ).trim().toUpperCase();
  return ["BUY", "SELL"].includes(action);
}

function outcome(record = {}) {
  const status = String(record.status ?? record.outcome ?? "").toUpperCase();
  if (status === "WIN") return 1;
  if (["LOSS", "FLAT"].includes(status)) return 0;
  return null;
}

export function buildConfidenceCalibration(records = [], { bins = 10 } = {}) {
  const valid = (Array.isArray(records) ? records : [])
    .filter(isTrade)
    .map((record) => ({
      confidence: probability(record.confidence ?? record.predictionConfidence),
      outcome: outcome(record),
    }))
    .filter((row) => row.confidence !== null && row.outcome !== null);

  const bucketCount = Math.max(2, Math.floor(Number(bins) || 10));
  const buckets = Array.from({ length: bucketCount }, (_, index) => ({
    index,
    min: index / bucketCount,
    max: (index + 1) / bucketCount,
    count: 0,
    confidenceSum: 0,
    outcomeSum: 0,
  }));

  for (const row of valid) {
    const index = Math.min(bucketCount - 1, Math.floor(row.confidence * bucketCount));
    const bucket = buckets[index];
    bucket.count += 1;
    bucket.confidenceSum += row.confidence;
    bucket.outcomeSum += row.outcome;
  }

  const curve = buckets.map((bucket) => ({
    index: bucket.index,
    min: bucket.min,
    max: bucket.max,
    count: bucket.count,
    predicted: bucket.count ? bucket.confidenceSum / bucket.count : null,
    observed: bucket.count ? bucket.outcomeSum / bucket.count : null,
  }));

  const ece = valid.length
    ? curve.reduce(
        (sum, bucket) =>
          sum +
          (bucket.count / valid.length) *
            Math.abs((bucket.predicted ?? 0) - (bucket.observed ?? 0)),
        0,
      )
    : null;
  const brier = valid.length
    ? valid.reduce(
        (sum, row) => sum + (row.confidence - row.outcome) ** 2,
        0,
      ) / valid.length
    : null;

  return {
    version: CONFIDENCE_CALIBRATION_V1_VERSION,
    sampleSize: valid.length,
    bins: curve,
    expectedCalibrationError: ece,
    brierScore: brier,
    calibrate(value) {
      const p = probability(value);
      if (p === null) return null;
      const index = Math.min(bucketCount - 1, Math.floor(p * bucketCount));
      return curve[index].observed ?? p;
    },
    warnings: valid.length < 50 ? ["INSUFFICIENT_CALIBRATION_SAMPLE"] : [],
  };
}

export default buildConfidenceCalibration;
