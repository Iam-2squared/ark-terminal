import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateAccuracyMetrics,
  normalizeAccuracyRows,
} from "../analysis/accuracy-metrics.js";

import {
  composeAccuracyDashboardData,
} from "../analysis/accuracy-dashboard-data-composer.js";

const mixedRows = [
  {
    id: "resolved-buy-win",
    action: "BUY",
    status: "WIN",
    profit: 5,
    confidence: 0.8,
  },
  {
    id: "resolved-sell-loss",
    action: "SELL",
    status: "LOSS",
    profit: -2,
    confidence: 0.7,
  },
  {
    id: "pending-buy",
    action: "BUY",
    status: "PENDING",
    confidence: 0.9,
  },
  {
    id: "no-trade-decision",
    action: "NO_TRADE",
    status: "LOSS",
    profit: 0,
    confidence: 0.4,
  },
  {
    id: "hold-decision",
    action: "HOLD",
    correct: true,
    profit: 0,
    confidence: 0.5,
  },
  {
    id: "cancelled-buy",
    action: "BUY",
    status: "CANCELLED",
    profit: 10,
    confidence: 0.6,
  },
  {
    id: "resolved-by-actual-signal",
    prediction: "SELL",
    actualSignal: "SELL",
    profit: 1,
    confidence: 0.75,
  },
];

test(
  "PENDING・NO_TRADE・HOLD・CANCELLEDをAccuracy分母から除外する",
  () => {
    const metrics =
      calculateAccuracyMetrics(mixedRows);

    assert.equal(metrics.sourceTotal, 7);
    assert.equal(metrics.total, 3);
    assert.equal(metrics.correct, 2);
    assert.equal(metrics.incorrect, 1);
    assert.equal(metrics.accuracyPercent, 66.666667);

    assert.equal(metrics.buy.total, 1);
    assert.equal(metrics.buy.correct, 1);
    assert.equal(metrics.sell.total, 2);
    assert.equal(metrics.sell.correct, 1);

    assert.equal(metrics.excluded.noTrade, 1);
    assert.equal(metrics.excluded.hold, 1);
    assert.equal(metrics.excluded.pending >= 1, true);
  },
);

test(
  "損益がない未確定予測を0円・不正解として捏造しない",
  () => {
    const rows = normalizeAccuracyRows([
      {
        action: "BUY",
        status: "PENDING",
      },
    ]);

    assert.equal(rows[0].profit, null);
    assert.equal(rows[0].correct, null);
    assert.equal(rows[0].resolved, false);
    assert.equal(rows[0].accuracyEligible, false);
    assert.equal(rows[0].tradePerformanceEligible, false);

    const metrics = calculateAccuracyMetrics(rows);
    assert.equal(metrics.total, 0);
    assert.equal(metrics.correct, 0);
    assert.equal(metrics.netProfit, 0);
  },
);

test(
  "NO_TRADEの評価結果を方向予測Accuracyへ混ぜない",
  () => {
    const metrics = calculateAccuracyMetrics([
      {
        action: "NO_TRADE",
        status: "LOSS",
        profit: -1,
      },
      {
        action: "BUY",
        status: "WIN",
        profit: 2,
      },
    ]);

    assert.equal(metrics.sourceTotal, 2);
    assert.equal(metrics.total, 1);
    assert.equal(metrics.correct, 1);
    assert.equal(metrics.accuracyPercent, 100);
    assert.equal(metrics.noTrade.total, 1);
    assert.equal(metrics.trades.total, 1);
  },
);

test(
  "Accuracy Dashboardのリスク指標へ未確定行のゼロを流さない",
  () => {
    const dashboard = composeAccuracyDashboardData({
      rows: mixedRows,
      options: {
        generatedAt: "2026-08-06T00:00:00.000Z",
      },
    });

    assert.equal(dashboard.version, 1);
    assert.equal(dashboard.metricsPolicyVersion, 2);
    assert.equal(dashboard.metadata.rowCount, 7);
    assert.equal(dashboard.metadata.sourceRowCount, 7);
    assert.equal(dashboard.metadata.accuracyDenominatorCount, 3);
    assert.equal(dashboard.metadata.tradePerformanceCount, 3);
    assert.equal(dashboard.tradePerformance.totalTrades, 3);
    assert.equal(dashboard.tradePerformance.winningTrades, 2);
    assert.equal(dashboard.tradePerformance.losingTrades, 1);
    assert.equal(dashboard.tradePerformance.netProfit, 4);
  },
);

test(
  "Accuracyの分母定義を出力へ明示する",
  () => {
    const metrics = calculateAccuracyMetrics(mixedRows);

    assert.match(
      metrics.denominatorPolicy.accuracy,
      /Resolved BUY\/SELL/,
    );
    assert.equal(
      metrics.denominatorPolicy.excludes.includes("PENDING"),
      true,
    );
    assert.equal(
      metrics.denominatorPolicy.excludes.includes("NO_TRADE"),
      true,
    );
  },
);
