import test from "node:test";
import assert from "node:assert/strict";

import {
  composeAccuracyDashboardData,
} from "../analysis/accuracy-dashboard-data-composer.js";

const rows = [
  {
    timestamp: "2026-08-01T01:00:00.000Z",
    symbol: "7203.T",
    signal: "BUY",
    confidence: 0.9,
    correct: true,
    return: 0.02,
    profit: 2,
  },
  {
    timestamp: "2026-08-02T01:00:00.000Z",
    symbol: "7203.T",
    signal: "SELL",
    confidence: 0.7,
    correct: false,
    return: -0.01,
    profit: -1,
  },
];

test("Dashboard composer returns a UI-ready object", () => {
  const walkForward = {
    windows: 2,
    accuracy: 0.6,
  };

  const result = composeAccuracyDashboardData({
    rows,
    walkForward,
    options: {
      generatedAt:
        "2026-08-02T00:00:00.000Z",
    },
  });

  assert.equal(result.version, 1);
  assert.equal(result.summary.total, 2);
  assert.equal(
    result.tradePerformance.totalTrades,
    2,
  );
  assert.equal(result.walkForward, walkForward);
  assert.equal(
    result.metadata.generatedAt,
    "2026-08-02T00:00:00.000Z",
  );
  assert.ok(result.riskAdjusted);
  assert.ok(result.confidenceCalibration);
  assert.ok(result.periodPerformance);
  assert.ok(result.health);
});

test("Dashboard composer reports insufficient data", () => {
  const result = composeAccuracyDashboardData({
    rows: [],
  });

  assert.equal(
    result.health.status,
    "insufficient-data",
  );
  assert.equal(result.metadata.rowCount, 0);
});

test("Dashboard composer preserves custom source", () => {
  const result = composeAccuracyDashboardData({
    rows,
    options: {
      source: "walk-forward-audit",
    },
  });

  assert.equal(
    result.metadata.source,
    "walk-forward-audit",
  );
});

test("Dashboard composer validates rows", () => {
  assert.throws(
    () =>
      composeAccuracyDashboardData({
        rows: null,
      }),
    {
      name: "TypeError",
    },
  );
});
