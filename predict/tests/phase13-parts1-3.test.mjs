import test from "node:test";
import assert from "node:assert/strict";

import { buildAiSelfReviewV1 } from "../intelligence/ai-self-review-v1.js";
import { analyzeFailuresV1 } from "../intelligence/failure-analysis-v1.js";
import { buildLearningDashboardV1 } from "../intelligence/learning-dashboard-v1.js";

const records = [
  { id: "1", symbol: "7203.T", sector: "AUTO", marketRegime: "bull", action: "BUY", status: "WIN", returnPercent: 3, confidence: 80 },
  { id: "2", symbol: "7203.T", sector: "AUTO", marketRegime: "bear", action: "BUY", status: "LOSS", returnPercent: -2, confidence: 55, technical: { rsi: 75, volumeRatio: 0.8 }, risk: { atrPercent: 6 } },
  { id: "3", symbol: "6758.T", sector: "TECH", marketRegime: "bull", action: "NO_TRADE", status: "PENDING", confidence: 50 },
];

test("AI self review reuses accuracy dashboard and groups results", () => {
  const review = buildAiSelfReviewV1({ tradeMemoryRecords: records, performance: { sharpe: 1.1, maxDrawdownPercent: 8 } });
  assert.equal(review.version, "ai-self-review-v1");
  assert.equal(review.bySymbol.length, 2);
  assert.equal(review.bySector[0].key, "AUTO");
  assert.equal(review.safety.productionUpdateAllowed, false);
});

test("failure analysis classifies losses and produces review-only suggestions", () => {
  const result = analyzeFailuresV1(records);
  assert.equal(result.lossCount, 1);
  assert.ok(result.ranking.some((item) => item.reason === "RSI_OVERHEATED"));
  assert.ok(result.ranking.some((item) => item.reason === "MARKET_HEADWIND"));
  assert.equal(result.suggestions[0].humanApprovalRequired, true);
  assert.equal(result.automaticProductionUpdateAllowed, false);
});

test("learning dashboard normalizes candidates, validation, drift and logs", () => {
  const dashboard = buildLearningDashboardV1({
    productionModel: { version: "prod-1" },
    candidates: [{ id: "c1", version: "cand-1", status: "READY_FOR_REVIEW", metrics: { profitFactor: 1.4 } }],
    walkForwardReports: [{ candidateVersion: "cand-1", status: "PROMOTABLE_REQUIRES_HUMAN_APPROVAL", outOfSample: true, futureLeakChecked: true }],
    driftReports: [{ driftDetected: true, severity: "HIGH" }],
    learningLog: [{ type: "CANDIDATE_CREATED", timestamp: "2026-08-05T00:00:00Z", data: { candidateId: "c1" } }],
  });
  assert.equal(dashboard.summary.awaitingApproval, 1);
  assert.equal(dashboard.summary.passedWalkForward, 1);
  assert.equal(dashboard.summary.driftAlertCount, 1);
  assert.equal(dashboard.safety.automaticPromotionAllowed, false);
});
