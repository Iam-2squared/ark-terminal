import test from "node:test";
import assert from "node:assert/strict";

import { runProductionSmokeTest } from "../validation/production-smoke-test-v1.js";
import { runHistoricalValidation } from "../validation/historical-validation-v1.js";

test("production smoke test passes healthy paper-only configuration", () => {
  const healthy = Object.fromEntries([
    "unifiedDashboard", "predictionLab", "discovery", "aiAnalysis", "paperTrading",
    "portfolio", "accuracyDashboard", "learningDashboard", "aiControlCenter",
  ].map((key) => [key, { status: "READY" }]));

  const report = runProductionSmokeTest({
    surfaces: healthy,
    api: { health: "READY", openai: "READY" },
    ui: { mobile: "READY", darkMode: "READY", loading: "READY", error: "READY" },
    runtime: { consoleErrors: 0, buildInfoPresent: true },
    safety: { liveExecutionAllowed: false, brokerConnected: false },
  });

  assert.equal(report.status, "READY");
  assert.deepEqual(report.blockers, []);
});

test("production smoke test blocks unsafe live configuration", () => {
  const report = runProductionSmokeTest({
    safety: { liveExecutionAllowed: true, brokerConnected: true },
  });
  assert.equal(report.status, "BLOCKED");
  assert.ok(report.blockers.includes("live-trading-disabled"));
  assert.ok(report.blockers.includes("broker-disabled"));
});

test("historical validation produces grouped metrics without future leak", () => {
  const records = [
    { timestamp: "2026-01-01", signalAt: "2026-01-01", outcomeAt: "2026-01-02", symbol: "7203.T", sector: "AUTO", marketRegime: "BULL", action: "BUY", return: 0.03, confidence: 80 },
    { timestamp: "2026-01-03", signalAt: "2026-01-03", outcomeAt: "2026-01-04", symbol: "7203.T", sector: "AUTO", marketRegime: "BEAR", action: "BUY", return: -0.01, confidence: 70 },
    { timestamp: "2026-01-05", symbol: "9984.T", sector: "TECH", marketRegime: "BULL", action: "NO_TRADE", return: 0, confidence: 40 },
  ];

  const report = runHistoricalValidation({ records });
  assert.equal(report.status, "READY");
  assert.equal(report.overall.sampleSize, 3);
  assert.equal(report.overall.tradeCount, 2);
  assert.equal(report.dataQuality.futureLeakDetected, false);
  assert.equal(report.productionUpdateAllowed, false);
});

test("historical validation blocks duplicate or leaked records", () => {
  const record = { timestamp: "2026-01-02", signalAt: "2026-01-03", outcomeAt: "2026-01-02", symbol: "7203.T", action: "BUY", return: 0.01 };
  const report = runHistoricalValidation({ records: [record, { ...record }] });
  assert.equal(report.status, "BLOCKED");
  assert.ok(report.blockers.includes("FUTURE_LEAK_DETECTED"));
  assert.ok(report.blockers.includes("DUPLICATE_RECORDS"));
});
