import { createWalkForwardWindows } from "../backtest/walk-forward-splitter-v2.js";

export const BACKTEST_FORWARD_VALIDATION_V1_VERSION = "backtest-forward-validation-v1";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function average(values) {
  const valid = values.map(finite).filter((value) => value !== null);
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null;
}

function normalizeMetrics(metrics = {}) {
  return {
    accuracy: finite(metrics.accuracy ?? metrics.predictionAccuracy ?? metrics.winRate),
    winRate: finite(metrics.winRate ?? metrics.tradeWinRate ?? metrics.accuracy),
    profitFactor: finite(metrics.profitFactor ?? metrics.pf),
    sharpe: finite(metrics.sharpe ?? metrics.sharpeRatio),
    maxDrawdown: finite(metrics.maxDrawdown ?? metrics.maximumDrawdown),
    cagr: finite(metrics.cagr),
    averageReturn: finite(metrics.averageReturn ?? metrics.averageReturnPercent),
    sampleSize: finite(metrics.sampleSize ?? metrics.count ?? metrics.trades),
  };
}

function aggregate(results = []) {
  const metrics = results.map((result) => normalizeMetrics(result.metrics ?? result));
  return {
    accuracy: average(metrics.map((item) => item.accuracy)),
    winRate: average(metrics.map((item) => item.winRate)),
    profitFactor: average(metrics.map((item) => item.profitFactor)),
    sharpe: average(metrics.map((item) => item.sharpe)),
    maxDrawdown: average(metrics.map((item) => item.maxDrawdown)),
    cagr: average(metrics.map((item) => item.cagr)),
    averageReturn: average(metrics.map((item) => item.averageReturn)),
    sampleSize: metrics.reduce((sum, item) => sum + (item.sampleSize ?? 0), 0),
  };
}

function compare(candidate, production, thresholds) {
  const deltas = {
    accuracy: candidate.accuracy === null || production.accuracy === null ? null : candidate.accuracy - production.accuracy,
    profitFactor: candidate.profitFactor === null || production.profitFactor === null ? null : candidate.profitFactor - production.profitFactor,
    sharpe: candidate.sharpe === null || production.sharpe === null ? null : candidate.sharpe - production.sharpe,
    maxDrawdown: candidate.maxDrawdown === null || production.maxDrawdown === null ? null : candidate.maxDrawdown - production.maxDrawdown,
    cagr: candidate.cagr === null || production.cagr === null ? null : candidate.cagr - production.cagr,
  };

  const checks = {
    accuracy: deltas.accuracy !== null && deltas.accuracy >= thresholds.minimumAccuracyImprovement,
    profitFactor: deltas.profitFactor !== null && deltas.profitFactor >= thresholds.minimumProfitFactorImprovement,
    sharpe: deltas.sharpe !== null && deltas.sharpe >= thresholds.minimumSharpeImprovement,
    drawdown: deltas.maxDrawdown !== null && deltas.maxDrawdown <= thresholds.maximumDrawdownDeterioration,
    sampleSize: (candidate.sampleSize ?? 0) >= thresholds.minimumSampleSize,
  };

  return {
    deltas,
    checks,
    promotable: Object.values(checks).every(Boolean),
    humanApprovalRequired: true,
    productionUpdateAllowed: false,
  };
}

export async function runBacktestForwardValidation({
  records = [],
  candidateModel,
  productionBaseline,
  evaluator,
  splitterOptions = {},
  forwardMetrics = null,
  futureLeakChecked = false,
  thresholds = {},
} = {}) {
  if (typeof evaluator !== "function") throw new TypeError("evaluator must be a function");
  if (!candidateModel?.version) throw new TypeError("candidateModel.version is required");

  const resolvedThresholds = {
    minimumAccuracyImprovement: 2,
    minimumProfitFactorImprovement: 0,
    minimumSharpeImprovement: 0,
    maximumDrawdownDeterioration: 0,
    minimumSampleSize: 100,
    ...thresholds,
  };

  const windows = createWalkForwardWindows(records, splitterOptions);
  const windowResults = [];
  for (const window of windows) {
    const result = await evaluator({
      candidateModel,
      training: window.training,
      validation: window.validation,
      test: window.test,
      window,
    });
    windowResults.push({
      windowId: window.id,
      metrics: normalizeMetrics(result?.metrics ?? result),
      futureLeakChecked: Boolean(result?.futureLeakChecked ?? futureLeakChecked),
      outOfSample: true,
    });
  }

  const backtest = aggregate(windowResults);
  const forward = forwardMetrics ? normalizeMetrics(forwardMetrics) : null;
  const candidateMetrics = forward ? {
    ...backtest,
    accuracy: average([backtest.accuracy, forward.accuracy]),
    winRate: average([backtest.winRate, forward.winRate]),
    profitFactor: average([backtest.profitFactor, forward.profitFactor]),
    sharpe: average([backtest.sharpe, forward.sharpe]),
    maxDrawdown: average([backtest.maxDrawdown, forward.maxDrawdown]),
    cagr: average([backtest.cagr, forward.cagr]),
    averageReturn: average([backtest.averageReturn, forward.averageReturn]),
    sampleSize: (backtest.sampleSize ?? 0) + (forward.sampleSize ?? 0),
  } : backtest;

  const productionMetrics = normalizeMetrics(productionBaseline?.overall ?? productionBaseline?.metrics ?? productionBaseline ?? {});
  const comparison = compare(candidateMetrics, productionMetrics, resolvedThresholds);
  const allFutureLeakChecked = futureLeakChecked && windowResults.every((result) => result.futureLeakChecked);
  const outOfSample = windows.length > 0 && windowResults.every((result) => result.outOfSample);

  return {
    version: BACKTEST_FORWARD_VALIDATION_V1_VERSION,
    generatedAt: new Date().toISOString(),
    candidateVersion: candidateModel.version,
    productionVersion: productionBaseline?.modelVersion ?? productionBaseline?.version ?? null,
    windows: windowResults,
    windowCount: windows.length,
    backtest,
    forward,
    candidateMetrics,
    productionMetrics,
    futureLeakChecked: allFutureLeakChecked,
    outOfSample,
    comparison,
    status: allFutureLeakChecked && outOfSample && comparison.promotable ? "PROMOTABLE_REQUIRES_HUMAN_APPROVAL" : "NOT_PROMOTABLE",
    safety: {
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
      brokerExecutionAllowed: false,
    },
    warnings: [
      ...(windows.length === 0 ? ["INSUFFICIENT_WALK_FORWARD_DATA"] : []),
      ...(!allFutureLeakChecked ? ["FUTURE_LEAK_CHECK_REQUIRED"] : []),
      ...(!outOfSample ? ["OUT_OF_SAMPLE_VALIDATION_REQUIRED"] : []),
    ],
  };
}

export default runBacktestForwardValidation;
