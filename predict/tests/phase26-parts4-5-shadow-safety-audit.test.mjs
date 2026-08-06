import assert from "node:assert/strict";
import test from "node:test";

import { assessShadowSafety } from "../shadow/shadow-safety-gate.js";
import { buildShadowOrderAuditEntry } from "../shadow/order-audit-log.js";

test("Phase26 Part4 allows only healthy shadow analysis", () => {
  const result = assessShadowSafety({
    apiStatus: "HEALTHY",
    rssStatus: "HEALTHY",
    bridgeStatus: "HEALTHY",
    priceAgeMs: 5000,
    clockSkewMs: 200,
    duplicateDetected: false,
    timestampOrderValid: true,
    symbolMatched: true,
    dataQualityPassed: true,
  });

  assert.equal(result.status, "SAFE_FOR_SHADOW_ANALYSIS");
  assert.deepEqual(result.blockers, []);
  assert.equal(result.safety.executionAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("Phase26 Part4 blocks stale, mismatched and unhealthy data", () => {
  const result = assessShadowSafety({
    apiStatus: "DOWN",
    rssStatus: "HEALTHY",
    bridgeStatus: "DOWN",
    priceAgeMs: 30000,
    clockSkewMs: 3000,
    duplicateDetected: true,
    timestampOrderValid: false,
    symbolMatched: false,
    dataQualityPassed: false,
  });

  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("API_UNHEALTHY"));
  assert.ok(result.blockers.includes("BRIDGE_UNHEALTHY"));
  assert.ok(result.blockers.includes("STALE_PRICE"));
  assert.ok(result.blockers.includes("CLOCK_SKEW_TOO_LARGE"));
  assert.ok(result.blockers.includes("DUPLICATE_DATA"));
  assert.ok(result.blockers.includes("TIMESTAMP_ORDER_INVALID"));
  assert.ok(result.blockers.includes("SYMBOL_MISMATCH"));
  assert.ok(result.blockers.includes("DATA_QUALITY_FAILED"));
  assert.equal(result.safety.haltOnBlocker, true);
});

test("Phase26 Part5 builds frozen shadow audit entry with zero broker side effects", () => {
  const result = buildShadowOrderAuditEntry({
    auditId: "audit-1",
    timestamp: "2026-08-06T06:00:00Z",
    marketDate: "2026-08-06",
    proposal: {
      symbol: "7203.t",
      side: "BUY",
      quantity: 100,
      orderType: "LIMIT",
      referencePrice: 2500,
      limitPrice: 2495,
      stopLossPrice: 2425,
      takeProfitPrice: 2650,
      maxLoss: 7500,
      rationale: ["trend", "liquidity"],
    },
    decision: "SHADOW_REVIEW_ONLY",
    modelVersion: "candidate-v2",
    datasetVersion: "dataset-v3",
    marketSnapshotId: "snapshot-1",
    safety: { humanApprovalRequired: true },
  });

  assert.equal(result.symbol, "7203.T");
  assert.equal(result.decision, "SHADOW_REVIEW_ONLY");
  assert.equal(result.sideEffects.brokerWrites, 0);
  assert.equal(result.sideEffects.liveOrders, 0);
  assert.equal(result.safety.orderCreationAllowed, false);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.rationale), true);
});

test("Phase26 Part5 records blocked decision when blockers exist", () => {
  const result = buildShadowOrderAuditEntry({
    proposal: { symbol: "6758.t", side: "BUY", quantity: 10 },
    blockers: ["STALE_PRICE"],
    decision: "SHADOW_REVIEW_ONLY",
  });

  assert.equal(result.decision, "BLOCKED");
  assert.deepEqual(result.blockers, ["STALE_PRICE"]);
  assert.equal(result.safety.executionAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
});
