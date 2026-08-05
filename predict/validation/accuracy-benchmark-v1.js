export const ACCURACY_BENCHMARK_V1 = "accuracy-benchmark-v1";

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function buildAccuracyBenchmarkV1({ records = [], returns = [] } = {}) {
  const labeled = records.filter((row) => row?.actual !== undefined && row?.predicted !== undefined);
  const tp = labeled.filter((row) => row.predicted === 1 && row.actual === 1).length;
  const tn = labeled.filter((row) => row.predicted === 0 && row.actual === 0).length;
  const fp = labeled.filter((row) => row.predicted === 1 && row.actual === 0).length;
  const fn = labeled.filter((row) => row.predicted === 0 && row.actual === 1).length;
  const precision = tp + fp ? tp / (tp + fp) : 0;
  const recall = tp + fn ? tp / (tp + fn) : 0;
  const f1 = precision + recall ? 2 * precision * recall / (precision + recall) : 0;
  const accuracy = labeled.length ? (tp + tn) / labeled.length : 0;
  const calibrationError = labeled.length
    ? labeled.reduce((sum, row) => sum + Math.abs(Math.min(1, Math.max(0, finite(row.confidence) > 1 ? finite(row.confidence) / 100 : finite(row.confidence))) - finite(row.actual)), 0) / labeled.length
    : 0;

  const validReturns = returns.map((value) => finite(value, null)).filter((value) => value !== null);
  const mean = validReturns.length ? validReturns.reduce((sum, value) => sum + value, 0) / validReturns.length : 0;
  const downside = validReturns.filter((value) => value < 0);
  const variance = validReturns.length ? validReturns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / validReturns.length : 0;
  const downsideVariance = downside.length ? downside.reduce((sum, value) => sum + value ** 2, 0) / downside.length : 0;
  const sharpe = variance > 0 ? mean / Math.sqrt(variance) : 0;
  const sortino = downsideVariance > 0 ? mean / Math.sqrt(downsideVariance) : 0;

  return {
    version: ACCURACY_BENCHMARK_V1,
    generatedAt: new Date().toISOString(),
    status: labeled.length ? "READY" : "BLOCKED",
    classification: { sampleSize: labeled.length, accuracy, precision, recall, f1, tp, tn, fp, fn, calibrationError },
    riskAdjusted: { sampleSize: validReturns.length, meanReturn: mean, sharpe, sortino },
    productionUpdateAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
  };
}

export default buildAccuracyBenchmarkV1;
