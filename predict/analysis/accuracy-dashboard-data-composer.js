import {
  calculateAccuracyMetrics,
} from "./accuracy-metrics.js";

import {
  calculateRiskAdjustedMetrics,
} from "./risk-adjusted-metrics.js";

import {
  calculateConfidenceCalibration,
} from "./accuracy-confidence-calibration.js";

import {
  aggregatePeriodPerformance,
} from "./period-performance.js";

function readReturn(row) {
  const candidates = [
    row?.return,
    row?.returnRate,
    row?.profitRate,
    row?.profit,
    row?.pnl,
    row?.result?.return,
    row?.result?.profit,
  ];

  for (const candidate of candidates) {
    const number = Number(candidate);

    if (Number.isFinite(number)) {
      return number;
    }
  }

  return 0;
}

function createHealth(summary, risk, calibration) {
  const warnings = [];

  if (summary.total === 0) {
    warnings.push("No accuracy data is available.");
  }

  if (summary.total > 0 && summary.total < 30) {
    warnings.push(
      "The sample size is too small for reliable conclusions.",
    );
  }

  if (calibration.expectedCalibrationError > 0.1) {
    warnings.push(
      "Confidence calibration error is elevated.",
    );
  }

  if (risk.maxDrawdown > 0.2) {
    warnings.push("Maximum drawdown is elevated.");
  }

  let status = "healthy";

  if (summary.total === 0) {
    status = "insufficient-data";
  } else if (warnings.length >= 2) {
    status = "warning";
  } else if (warnings.length === 1) {
    status = "observe";
  }

  return {
    status,
    warnings,
  };
}

export function composeAccuracyDashboardData({
  rows = [],
  walkForward = null,
  options = {},
} = {}) {
  if (!Array.isArray(rows)) {
    throw new TypeError("rows must be an array");
  }

  const summary = calculateAccuracyMetrics(rows);

  const riskAdjusted = calculateRiskAdjustedMetrics(
    rows.map(readReturn),
    options.riskAdjusted,
  );

  const confidenceCalibration =
    calculateConfidenceCalibration(
      rows,
      options.confidenceCalibration,
    );

  const periodPerformance =
    aggregatePeriodPerformance(rows);

  const health = createHealth(
    summary,
    riskAdjusted,
    confidenceCalibration,
  );

  return {
    version: 1,

    summary,

    tradePerformance: {
      totalTrades: summary.total,
      winningTrades: summary.trades.winners,
      losingTrades: summary.trades.losers,
      flatTrades: summary.trades.flat,
      winRate: summary.trades.winRate,
      grossProfit: summary.grossProfit,
      grossLoss: summary.grossLoss,
      netProfit: summary.netProfit,
      averageProfit: summary.averageProfit,
      averageLoss: summary.averageLoss,
      expectancy: summary.expectancy,
      profitFactor: summary.profitFactor,
      maxDrawdown: summary.maxDrawdown,
    },

    riskAdjusted,
    confidenceCalibration,
    periodPerformance,
    walkForward,
    health,

    metadata: {
      generatedAt:
        options.generatedAt ??
        new Date().toISOString(),
      rowCount: rows.length,
      source:
        options.source ??
        "accuracy-dashboard-data-composer",
    },
  };
}

export default composeAccuracyDashboardData;

