export const IMPROVEMENT_SIMULATOR_V1_VERSION = "improvement-simulator-v1";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function delta(candidate, production) {
  return candidate === null || production === null ? null : candidate - production;
}

function normalize(metrics = {}) {
  return {
    accuracy: finite(metrics.accuracy ?? metrics.predictionAccuracy),
    winRate: finite(metrics.winRate ?? metrics.tradeWinRate),
    profitFactor: finite(metrics.profitFactor ?? metrics.pf),
    sharpe: finite(metrics.sharpe ?? metrics.sharpeRatio),
    maxDrawdown: finite(metrics.maxDrawdown ?? metrics.maxDrawdownPercent),
    expectedValue: finite(metrics.expectedValue ?? metrics.ev ?? metrics.averageReturn),
    sampleSize: finite(metrics.sampleSize ?? metrics.trades ?? metrics.count),
  };
}

export function simulateModelImprovement({ candidate = {}, production = {}, thresholds = {} } = {}) {
  const c = normalize(candidate);
  const p = normalize(production);
  const resolved = {
    minimumAccuracyDelta: 0,
    minimumProfitFactorDelta: 0,
    minimumSharpeDelta: 0,
    maximumDrawdownDeterioration: 0,
    minimumExpectedValueDelta: 0,
    minimumSampleSize: 100,
    ...thresholds,
  };
  const deltas = {
    accuracy: delta(c.accuracy, p.accuracy),
    profitFactor: delta(c.profitFactor, p.profitFactor),
    sharpe: delta(c.sharpe, p.sharpe),
    maxDrawdown: delta(c.maxDrawdown, p.maxDrawdown),
    expectedValue: delta(c.expectedValue, p.expectedValue),
  };
  const checks = {
    accuracy: deltas.accuracy !== null && deltas.accuracy >= resolved.minimumAccuracyDelta,
    profitFactor: deltas.profitFactor !== null && deltas.profitFactor >= resolved.minimumProfitFactorDelta,
    sharpe: deltas.sharpe !== null && deltas.sharpe >= resolved.minimumSharpeDelta,
    drawdown: deltas.maxDrawdown !== null && deltas.maxDrawdown <= resolved.maximumDrawdownDeterioration,
    expectedValue: deltas.expectedValue !== null && deltas.expectedValue >= resolved.minimumExpectedValueDelta,
    sampleSize: (c.sampleSize ?? 0) >= resolved.minimumSampleSize,
  };
  const failedChecks = Object.keys(checks).filter((key) => checks[key] !== true);

  return {
    version: IMPROVEMENT_SIMULATOR_V1_VERSION,
    generatedAt: new Date().toISOString(),
    candidate: c,
    production: p,
    deltas,
    checks,
    failedChecks,
    status: failedChecks.length === 0 ? "REVIEW_RECOMMENDED" : "NOT_RECOMMENDED",
    promotable: false,
    humanApprovalRequired: true,
    productionUpdateAllowed: false,
    brokerExecutionAllowed: false,
  };
}

export default simulateModelImprovement;
