import test from "node:test";
import assert from "node:assert/strict";
import { evaluateSemiAutoReadiness, verifyReadinessGate } from "../shadow/phase50-9-readiness-gate.js";

function stable(overrides = {}) {
  return {
    mode: "SHADOW_ONLY",
    classification: "STABLE_CANDIDATE",
    metrics: {
      dayCount: 25,
      promotionRate: 0.72,
      demotionRate: 0.08,
      averageProfitFactor: 1.35,
      averageSharpe: 0.5,
      worstDrawdown: 0.08,
      ...overrides,
    },
  };
}

function latest(overrides = {}) {
  return {
    mode: "SHADOW_ONLY",
    classification: "PROMOTION_CANDIDATE",
    metrics: {
      sampleCount: 100,
      winRate: 0.56,
      profitFactor: 1.4,
      sharpe: 0.6,
      maxDrawdown: 0.07,
    },
    transmittedOrderCount: 0,
    brokerWriteCount: 0,
    excelOrderWriteCount: 0,
    rssOrderFunctionCallCount: 0,
    liveOrderCount: 0,
    ...overrides,
  };
}

test("Phase50.9 can mark a candidate READY without enabling execution", () => {
  const result = evaluateSemiAutoReadiness({ stability: stable(), latestEvaluation: latest() });
  assert.equal(result.status, "READY");
  assert.equal(result.semiAutoExecutionAllowed, false);
  assert.equal(result.liveTradingAllowed, false);
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
  assert.equal(result.transmittedOrderCount, 0);
  assert.equal(result.brokerWriteCount, 0);
  assert.equal(result.excelOrderWriteCount, 0);
  assert.equal(result.rssOrderFunctionCallCount, 0);
  assert.equal(result.liveOrderCount, 0);
  assert.equal(verifyReadinessGate(result).status, "VALID");
});

test("Phase50.9 remains NOT_READY with insufficient history", () => {
  const result = evaluateSemiAutoReadiness({ stability: stable({ dayCount: 8 }), latestEvaluation: latest() });
  assert.equal(result.status, "NOT_READY");
  assert.ok(result.blockers.includes("INSUFFICIENT_STABLE_DAYS"));
});

test("Phase50.9 blocks immediately on any safety counter", () => {
  const result = evaluateSemiAutoReadiness({ stability: stable(), latestEvaluation: latest({ brokerWriteCount: 1 }) });
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("SAFETY_COUNTER_NONZERO"));
});

test("verification rejects any attempt to enable semi-auto execution", () => {
  const result = evaluateSemiAutoReadiness({ stability: stable(), latestEvaluation: latest() });
  const tampered = { ...result, semiAutoExecutionAllowed: true };
  const audit = verifyReadinessGate(tampered);
  assert.equal(audit.status, "BLOCKED");
  assert.ok(audit.blockers.includes("SEMI_AUTO_EXECUTION_NOT_BLOCKED"));
});
