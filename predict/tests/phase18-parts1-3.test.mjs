import test from "node:test";
import assert from "node:assert/strict";

import { runDailyDataUpdateV1 } from "../operations/daily-data-update-v1.js";
import { buildPreMarketReportV1 } from "../operations/pre-market-report-v1.js";
import { runDailyPredictionV1 } from "../operations/daily-prediction-run-v1.js";

test("daily update blocks future data and requests rollback", () => {
  const result = runDailyDataUpdateV1({
    asOf: "2026-08-05T00:00:00Z",
    sources: [{ name: "quotes", rows: [{ timestamp: "2026-08-06T00:00:00Z" }] }],
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.rollbackRequired, true);
  assert.equal(result.commitAllowed, false);
});

test("pre-market report ranks candidates and remains advisory", () => {
  const result = buildPreMarketReportV1({
    market: { regime: "RISK_ON", riskScore: 0.4 },
    candidates: [{ symbol: "7203.T", score: 80 }, { symbol: "6758.T", score: 70 }],
  });
  assert.equal(result.status, "READY");
  assert.equal(result.topCandidates[0].symbol, "7203.T");
  assert.equal(result.brokerExecutionAllowed, false);
});

test("daily prediction creates BUY SELL and NO_TRADE with approval gate", () => {
  const result = runDailyPredictionV1({
    market: { riskScore: 0 },
    universe: [
      { symbol: "BUY.T", technicalScore: 90, newsScore: 80, earningsScore: 80 },
      { symbol: "SELL.T", technicalScore: 10, newsScore: 20, earningsScore: 20 },
      { symbol: "WAIT.T", technicalScore: 50, newsScore: 50, earningsScore: 50 },
    ],
  });
  assert.equal(result.summary.total, 3);
  assert.ok(result.predictions.some((row) => row.action === "BUY"));
  assert.ok(result.predictions.some((row) => row.action === "SELL"));
  assert.ok(result.predictions.some((row) => row.action === "NO_TRADE"));
  assert.equal(result.humanApprovalRequired, true);
  assert.equal(result.brokerExecutionAllowed, false);
});
