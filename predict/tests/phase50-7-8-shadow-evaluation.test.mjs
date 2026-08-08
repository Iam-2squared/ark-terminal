import test from "node:test";
import assert from "node:assert/strict";
import { evaluatePromotionCandidate, verifyPromotionEvaluation } from "../shadow/phase50-7-promotion-evaluation.js";
import { buildDailyShadowHistory, evaluateShadowStability, verifyShadowStability } from "../shadow/phase50-8-stability.js";

function snapshot(day, price) {
  return { symbol: "7203.T", observedAt: `${day}T06:00:00Z`, bid: price - 0.1, ask: price + 0.1, last: price, volume: 1000, source: "TEST_READ_ONLY" };
}

function decision(day) {
  return { mode: "SHADOW_ONLY", symbol: "7203.T", transmitted: false, safety: { brokerWriteAllowed: false, rssOrderFunctionAllowed: false, excelOrderWriteAllowed: false }, observedAt: `${day}T06:00:00Z` };
}

function settlements(count = 80) {
  return Array.from({ length: count }, (_, i) => ({
    quantity: 100,
    netReturn: i % 4 === 0 ? -0.004 : 0.003,
    pnl: i % 4 === 0 ? -40 : 30,
    transmitted: false,
    safety: { brokerWriteAllowed: false, rssOrderFunctionAllowed: false, excelOrderWriteAllowed: false },
  }));
}

test("Phase50.7 produces promotion candidate while keeping all writes disabled", () => {
  const snaps = [snapshot("2026-08-01", 100), snapshot("2026-08-02", 101)];
  const decisions = [decision("2026-08-01")];
  const result = evaluatePromotionCandidate({ snapshots: snaps, decisions, settlements: settlements(80), thresholds: { minSamples: 60, minProfitFactor: 1, minWinRate: 0.5, minSharpe: 0 } });
  assert.equal(result.mode, "SHADOW_ONLY");
  assert.equal(result.classification, "PROMOTION_CANDIDATE");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.liveOrderCount, 0);
  assert.equal(verifyPromotionEvaluation(result).status, "VALID");
});

test("Phase50.7 blocks any unsafe counter", () => {
  const unsafe = { mode: "SHADOW_ONLY", automaticPromotionAllowed: false, productionUpdateAllowed: false, humanApprovalRequired: true, transmittedOrderCount: 0, brokerWriteCount: 1, excelOrderWriteCount: 0, rssOrderFunctionCallCount: 0, liveOrderCount: 0 };
  assert.equal(verifyPromotionEvaluation(unsafe).status, "BLOCKED");
});

test("Phase50.8 deduplicates daily history and can classify stable candidate", () => {
  let history = [];
  for (let i = 1; i <= 10; i += 1) {
    const day = `2026-08-${String(i).padStart(2, "0")}`;
    history = buildDailyShadowHistory({
      previous: history,
      observedAt: `${day}T08:00:00Z`,
      evaluation: {
        mode: "SHADOW_ONLY",
        evaluationId: `e${i}`,
        classification: "PROMOTION_CANDIDATE",
        metrics: { sampleCount: 80 + i, winRate: 0.6, profitFactor: 1.5, sharpe: 0.6, maxDrawdown: 0.08, netReturn: 0.02, netPnl: 200 },
      },
    });
  }
  history = buildDailyShadowHistory({ previous: history, observedAt: "2026-08-10T09:00:00Z", evaluation: { mode: "SHADOW_ONLY", evaluationId: "replacement", classification: "PROMOTION_CANDIDATE", metrics: { sampleCount: 100, winRate: 0.61, profitFactor: 1.6, sharpe: 0.7, maxDrawdown: 0.07, netReturn: 0.03, netPnl: 300 } } });
  assert.equal(history.length, 10);
  const result = evaluateShadowStability({ history, thresholds: { minDays: 10 } });
  assert.equal(result.classification, "STABLE_CANDIDATE");
  assert.equal(result.automaticPromotionAllowed, false);
  assert.equal(result.liveOrderCount, 0);
  assert.equal(verifyShadowStability(result).status, "VALID");
});
