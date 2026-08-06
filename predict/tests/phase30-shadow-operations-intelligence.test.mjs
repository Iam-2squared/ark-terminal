import test from "node:test";
import assert from "node:assert/strict";

import {
  analyzeShadowPerformanceByRegime,
  buildShadowOperationsDashboard,
  buildShadowPeriodicReports,
  evaluateShadowOperationalSafety,
  runShadowOperationsIntelligence,
} from "../shadow/shadow-operations-intelligence.js";

const safety = {
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
};

const evaluations = [
  { status: "EVALUATED", marketRegime: "BULL", directionCorrect: true, netPnl: 1000, netReturn: 0.02, safety },
  { status: "EVALUATED", marketRegime: "BULL", directionCorrect: false, netPnl: -400, netReturn: -0.01, safety },
  { status: "EVALUATED", marketRegime: "BEAR", directionCorrect: true, netPnl: 600, netReturn: 0.015, safety },
];

const dailyLogs = [
  { date: "2026-08-03", predictionCount: 3, evaluatedCount: 2, pendingCount: 1, noTradeCount: 0, wins: 1, totalNetPnl: 600, safety },
  { date: "2026-08-04", predictionCount: 2, evaluatedCount: 1, pendingCount: 1, noTradeCount: 0, wins: 1, totalNetPnl: 600, safety },
];

test("Part5 separates shadow performance by market regime", () => {
  const result = analyzeShadowPerformanceByRegime(evaluations);
  assert.equal(result.status, "REGIME_ANALYSIS_READY");
  assert.equal(result.overall.sampleCount, 3);
  assert.equal(result.regimes.find((item) => item.marketRegime === "BULL").sampleCount, 2);
  assert.equal(result.regimes.find((item) => item.marketRegime === "BEAR").winRate, 1);
});

test("Part6 dashboard aggregates shadow-only operational data", () => {
  const dashboard = buildShadowOperationsDashboard({ dailyLogs, evaluations });
  assert.equal(dashboard.status, "SHADOW_DASHBOARD_READY");
  assert.equal(dashboard.totals.predictions, 5);
  assert.equal(dashboard.totals.evaluated, 3);
  assert.equal(dashboard.totals.netPnl, 1200);
  assert.equal(dashboard.executionAllowed, false);
});

test("Part7 builds weekly and monthly reports", () => {
  const reports = buildShadowPeriodicReports(dailyLogs);
  assert.equal(reports.weekly.length, 1);
  assert.equal(reports.monthly[0].period, "2026-08");
  assert.equal(reports.monthly[0].predictionCount, 5);
  assert.equal(reports.monthly[0].winRate, 2 / 3);
});

test("Part8 halts on disconnected RSS or stale data", () => {
  const result = evaluateShadowOperationalSafety({
    rssConnected: false,
    bridgeConnected: true,
    dataQualityHealthy: true,
    auditChecksumValid: true,
    pendingCount: 0,
    dailyNetPnl: 0,
    dataAgeMinutes: 1,
  });
  assert.equal(result.status, "HALTED");
  assert.equal(result.shadowOperationsAllowed, false);
  assert.ok(result.blockers.includes("RSS_DISCONNECTED"));
  assert.equal(result.liveOrders, 0);
});

test("Part8 blocks daily loss breach and checksum mismatch", () => {
  const result = evaluateShadowOperationalSafety({
    rssConnected: true,
    bridgeConnected: true,
    dataQualityHealthy: true,
    auditChecksumValid: false,
    pendingCount: 0,
    dailyNetPnl: -60000,
    dataAgeMinutes: 1,
  }, { maxDailyLoss: 50000 });
  assert.equal(result.status, "HALTED");
  assert.ok(result.blockers.includes("DAILY_LOSS_LIMIT_EXCEEDED"));
  assert.ok(result.blockers.includes("AUDIT_CHECKSUM_MISMATCH"));
});

test("operational intelligence remains non-executable even when healthy", () => {
  const result = runShadowOperationsIntelligence({
    dailyLogs,
    evaluations,
    operationalState: {
      rssConnected: true,
      bridgeConnected: true,
      dataQualityHealthy: true,
      auditChecksumValid: true,
      pendingCount: 2,
      dailyNetPnl: 1200,
      dataAgeMinutes: 1,
      sampleCount: 100,
    },
  });
  assert.equal(result.status, "SHADOW_OPERATIONS_READY");
  assert.equal(result.executionAllowed, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
  assert.equal(result.excelOrderWrites, 0);
  assert.equal(result.orderTriggerChanges, 0);
});

test("writable records are rejected", () => {
  assert.throws(
    () => analyzeShadowPerformanceByRegime([{ ...evaluations[0], safety: { brokerWriteAllowed: true, liveTradingAllowed: false } }]),
    /require broker and live trading writes to remain disabled/,
  );
});
