import assert from "node:assert/strict";
import test from "node:test";

import { buildFailureReviewV3 } from "../forward/failure-review-v3.js";
import { evaluatePromotionGate } from "../forward/promotion-gate.js";
import { buildPaperOperationsDashboard } from "../forward/paper-operations-dashboard.js";

test("Phase25 Part4 reviews only resolved losing outcomes", () => {
  const review = buildFailureReviewV3([
    {
      id: "a",
      symbol: "7203.t",
      status: "RESOLVED",
      predictedDirection: "UP",
      actualDirection: "DOWN",
      confidence: 0.82,
      marketRegime: "bull",
      holdingPeriod: 1,
      grossReturn: -1.2,
      netReturn: -1.5,
      feePercent: 0.1,
      slippagePercent: 0.2,
    },
    { id: "b", status: "PENDING", netReturn: -3 },
    { id: "c", status: "RESOLVED", netReturn: 2 },
  ]);

  assert.equal(review.failureCount, 1);
  assert.equal(review.failures[0].symbol, "7203.T");
  assert.ok(review.failures[0].hypotheses.includes("OVERCONFIDENT_SIGNAL"));
  assert.ok(review.failures[0].hypotheses.includes("HOLDING_PERIOD_TOO_SHORT"));
  assert.equal(review.safety.automaticPromotionAllowed, false);
  assert.equal(review.safety.brokerWriteAllowed, false);
});

test("Phase25 Part5 blocks incomplete promotion metrics", () => {
  const result = evaluatePromotionGate({
    resolvedPredictions: 120,
    sessions: 30,
    profitFactor: 1.1,
    maxDrawdown: 12,
    calibrationError: 0.1,
    symbolConcentration: 0.4,
    industryConcentration: 0.35,
    futureLeakChecked: false,
    dataQualityPassed: true,
    killSwitchTestPassed: false,
    majorIncidentCount: 1,
  });

  assert.equal(result.status, "NOT_READY");
  assert.ok(result.blockers.includes("INSUFFICIENT_RESOLVED_PREDICTIONS"));
  assert.ok(result.blockers.includes("PROFIT_FACTOR_BELOW_GATE"));
  assert.ok(result.blockers.includes("KILL_SWITCH_NOT_VERIFIED"));
  assert.equal(result.promotionExecuted, false);
});

test("Phase25 Part5 can only mark readiness for human review", () => {
  const result = evaluatePromotionGate({
    resolvedPredictions: 320,
    sessions: 70,
    profitFactor: 1.3,
    maxDrawdown: 8,
    calibrationError: 0.06,
    symbolConcentration: 0.2,
    industryConcentration: 0.25,
    futureLeakChecked: true,
    dataQualityPassed: true,
    killSwitchTestPassed: true,
    majorIncidentCount: 0,
  });

  assert.equal(result.status, "READY_FOR_HUMAN_REVIEW");
  assert.deepEqual(result.blockers, []);
  assert.equal(result.safety.humanApprovalRequired, true);
  assert.equal(result.safety.automaticPromotionAllowed, false);
});

test("Phase25 Part6 summarizes overall and grouped paper performance", () => {
  const dashboard = buildPaperOperationsDashboard([
    { status: "RESOLVED", netReturn: 2, marketRegime: "bull", strategy: "trend", candidateVersion: "c1", turnover: 100 },
    { status: "RESOLVED", netReturn: -1, marketRegime: "bull", strategy: "trend", candidateVersion: "c1", turnover: 120 },
    { status: "RESOLVED", netReturn: 1, marketRegime: "bear", strategy: "mean", candidateVersion: "c2", turnover: 80 },
    { status: "PENDING", marketRegime: "bear", strategy: "mean", candidateVersion: "c2" },
  ], { generatedAt: "2026-08-06T00:00:00Z", sessions: 61 });

  assert.equal(dashboard.overall.resolvedCount, 3);
  assert.equal(dashboard.overall.netReturn, 2);
  assert.ok(Math.abs(dashboard.overall.winRate - (2 / 3)) < 1e-12);
  assert.equal(dashboard.pendingCount, 1);
  assert.equal(dashboard.byMarketRegime.length, 2);
  assert.equal(dashboard.byStrategy.length, 2);
  assert.equal(dashboard.byCandidate.length, 2);
  assert.equal(dashboard.safety.liveTradingAllowed, false);
});
