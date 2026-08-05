import test from "node:test";
import assert from "node:assert/strict";

import { buildExplainabilityV3 } from "../analysis/explainability-v3.js";
import { simulateModelImprovement } from "../learning/improvement-simulator-v1.js";
import { buildAiControlCenter } from "../control/ai-control-center-v1.js";

test("Explainability V3 exposes layered reasons without execution", () => {
  const result = buildExplainabilityV3({
    decision: "BUY",
    aiScore: 82,
    confidence: 78,
    strategyReasons: ["TREND_SUPPORT"],
    technical: { score: 80, reasons: ["MACD_GC"] },
    marketIntelligence: { reasons: ["MARKET_TAILWIND"] },
    risk: { risks: ["EARNINGS_NEAR"] },
  });
  assert.equal(result.decision, "BUY");
  assert.ok(result.reasons.includes("MACD_GC"));
  assert.equal(result.safety.brokerExecutionAllowed, false);
});

test("Improvement simulator is review-only even when all checks pass", () => {
  const result = simulateModelImprovement({
    candidate: { accuracy: 65, profitFactor: 1.5, sharpe: 1.2, maxDrawdown: 10, expectedValue: 0.5, sampleSize: 150 },
    production: { accuracy: 60, profitFactor: 1.2, sharpe: 0.8, maxDrawdown: 12, expectedValue: 0.1, sampleSize: 150 },
  });
  assert.equal(result.status, "REVIEW_RECOMMENDED");
  assert.equal(result.promotable, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("AI Control Center blocks unsafe live configuration", () => {
  const result = buildAiControlCenter({
    prediction: { status: "READY" },
    discovery: { status: "READY" },
    marketIntelligence: { status: "READY" },
    paperTrading: { status: "READY" },
    portfolio: { status: "READY" },
    accuracy: { status: "READY" },
    learning: { status: "READY" },
    runtime: { status: "READY" },
    releaseAudit: { ready: true },
    ci: { predictTests: true, discoveryTests: true },
    safety: { liveExecutionAllowed: true },
  });
  assert.equal(result.overallStatus, "BLOCKED");
  assert.ok(result.blockers.includes("LIVE_EXECUTION_MUST_REMAIN_DISABLED"));
  assert.equal(result.safety.liveExecutionAllowed, false);
});
