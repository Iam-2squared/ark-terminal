import {
  calculateAccuracyMetrics,
  normalizeAccuracyRows,
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

function createHealth(summary, risk, calibration) {
  const warnings = [];

  if (summary.total === 0) {
    warnings.push("No resolved BUY/SELL accuracy data is available.");
  }

  if (summary.total > 0 && summary.total < 30) {
    warnings.push(
      "The resolved directional sample is too small for reliable conclusions.",
    );
  }

  if (summary.excluded.pending > 0) {
    warnings.push(
      "Pending outcomes are excluded from the accuracy denominator.",
    );
  }

  if (
    summary.excluded.noTrade > 0 ||
    summary.excluded.hold > 0
  ) {
    warnings.push(
      "NO_TRADE and HOLD decisions are reported separately and excluded from directional accuracy.",
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

  const normalizedRows = normalizeAccuracyRows(rows);
  const summary = calculateAccuracyMetrics(rows);

  const accuracyRows = normalizedRows.filter(
    (row) => row.accuracyEligible,
  );
  const tradeRows = normalizedRows.filter(
    (row) => row.tradePerformanceEligible,
  );

  const riskAdjusted = calculateRiskAdjustedMetrics(
    tradeRows.map((row) => row.profit),
    options.riskAdjusted,
  );

  const confidenceCalibration =
    calculateConfidenceCalibration(
      accuracyRows,
      options.confidenceCalibration,
    );

  const periodPerformance =
    aggregatePeriodPerformance(tradeRows);

  const health = createHealth(
    summary,
    riskAdjusted,
    confidenceCalibration,
  );

  return {
    version: 2,

    summary,

    tradePerformance: {
      totalTrades: summary.trades.total,
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
      sourceRowCount: rows.length,
      accuracyDenominatorCount: accuracyRows.length,
      tradePerformanceCount: tradeRows.length,
      excluded: { ...summary.excluded },
      source:
        options.source ??
        "accuracy-dashboard-data-composer",
    },
  };
}

export default composeAccuracyDashboardData;
