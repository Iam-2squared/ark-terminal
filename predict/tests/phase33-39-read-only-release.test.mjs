import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPaperOperationsSnapshot,
  buildRiskAndAuditReport,
  buildReleaseReadinessDashboard,
  runPhase33To39ReadOnlyRelease,
} from "../release/phase33-39-read-only-release.js";

test("paper operations remain non-executable", () => {
  const snapshot = buildPaperOperationsSnapshot({
    cash: 100000,
    orders: [{ symbol: "7203.T", side: "BUY", quantity: 100, status: "PENDING" }],
  });
  assert.equal(snapshot.pendingOrders, 1);
  assert.equal(snapshot.brokerWrites, 0);
  assert.equal(snapshot.liveOrders, 0);
  assert.equal(snapshot.safety.liveTradingAllowed, false);
});

test("risk report fails closed on stale or disconnected data", () => {
  const report = buildRiskAndAuditReport({
    snapshots: [{ netPnl: -0.01, drawdown: 0.02 }],
    health: { dataFresh: false, rssConnected: false, bridgeConnected: true },
  });
  assert.equal(report.status, "HALTED");
  assert.ok(report.blockers.includes("STALE_DATA"));
  assert.ok(report.blockers.includes("RSS_DISCONNECTED"));
});

test("release dashboard requires validation and recovery evidence", () => {
  const dashboard = buildReleaseReadinessDashboard({
    operations: buildPaperOperationsSnapshot(),
    riskReport: buildRiskAndAuditReport({ health: { dataFresh: true, rssConnected: true, bridgeConnected: true } }),
    validation: { outOfSamplePassed: true, auditPassed: true },
    resilience: { backupVerified: true, restoreVerified: true, recoveryDrillPassed: true },
  });
  assert.equal(dashboard.status, "READY_FOR_HUMAN_RELEASE_REVIEW");
  assert.equal(dashboard.automaticReleaseAllowed, false);
  assert.equal(dashboard.productionUpdateAllowed, false);
});

test("full Phase33-39 runner never creates a real order path", () => {
  const result = runPhase33To39ReadOnlyRelease({
    risk: { health: { dataFresh: true, rssConnected: true, bridgeConnected: true } },
    validation: { outOfSamplePassed: true, auditPassed: true },
    resilience: { backupVerified: true, restoreVerified: true, recoveryDrillPassed: true },
  });
  assert.equal(result.status, "READY_FOR_HUMAN_RELEASE_REVIEW");
  assert.equal(result.realOrderPathImplemented, false);
  assert.equal(result.brokerWrites, 0);
  assert.equal(result.liveOrders, 0);
});
