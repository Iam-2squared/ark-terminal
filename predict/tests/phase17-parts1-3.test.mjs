import test from "node:test";
import assert from "node:assert/strict";

import { buildHistoricalDatasetV1 } from "../data/historical-data-pipeline-v1.js";
import { runLargeScaleBacktestV1 } from "../backtest/large-scale-backtest-v1.js";
import { buildAccuracyBenchmarkV1 } from "../validation/accuracy-benchmark-v1.js";

test("historical pipeline deduplicates and adjusts splits", () => {
  const result = buildHistoricalDatasetV1({
    rows: [
      { symbol: "7203.T", timestamp: "2026-01-01", close: 1000, volume: 100 },
      { symbol: "7203.T", timestamp: "2026-01-01", close: 1000, volume: 100 },
    ],
    corporateActions: [{ symbol: "7203.T", effectiveAt: "2026-02-01", splitRatio: 2 }],
    asOf: "2026-03-01",
  });
  assert.equal(result.status, "READY");
  assert.equal(result.metadata.duplicateRowsRemoved, 1);
  assert.equal(result.rows[0].adjustedClose, 500);
});

test("large scale backtest includes fees and breakdowns", () => {
  const result = runLargeScaleBacktestV1({
    signals: [
      { symbol: "7203.T", sector: "AUTO", regime: "BULL", action: "BUY", return: 0.03, signalAt: "2026-01-01", outcomeAt: "2026-01-02" },
      { symbol: "6758.T", sector: "TECH", regime: "BULL", action: "BUY", return: -0.01, signalAt: "2026-01-01", outcomeAt: "2026-01-02" },
    ],
  });
  assert.equal(result.status, "READY");
  assert.equal(result.overall.sampleSize, 2);
  assert.ok(result.overall.expectedValue < 0.01);
  assert.equal(result.brokerExecutionAllowed, false);
});

test("accuracy benchmark calculates classification metrics and keeps approval gate", () => {
  const result = buildAccuracyBenchmarkV1({
    records: [
      { predicted: 1, actual: 1, confidence: 80 },
      { predicted: 1, actual: 0, confidence: 70 },
      { predicted: 0, actual: 0, confidence: 60 },
      { predicted: 0, actual: 1, confidence: 55 },
    ],
    returns: [0.02, -0.01, 0.01, 0.005],
  });
  assert.equal(result.classification.accuracy, 0.5);
  assert.equal(result.classification.precision, 0.5);
  assert.equal(result.classification.recall, 0.5);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});
