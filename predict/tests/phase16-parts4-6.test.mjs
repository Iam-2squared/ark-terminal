import test from "node:test";
import assert from "node:assert/strict";

import { buildMarketAiV1 } from "../market/market-ai-v1.js";
import { runStrategyLabV1 } from "../strategy/strategy-lab-v1.js";
import { analyzeContinuousAccuracyV1 } from "../learning/continuous-accuracy-v1.js";

test("market AI identifies risk-on conditions without live execution", () => {
  const result = buildMarketAiV1({
    indices: {
      NIKKEI: { return1d: 0.02, return5d: 0.05, timestamp: "2026-08-01" },
      TOPIX: { return1d: 0.01, return5d: 0.04, timestamp: "2026-08-01" },
    },
    breadth: { advancers: 1200, decliners: 400 },
    sectorRotation: [{ sector: "TECH", score: 0.08 }],
    macro: { rateChange: -0.1, fxTailwind: 0.5 },
    asOf: "2026-08-02",
  });
  assert.equal(result.status, "READY");
  assert.equal(result.regime, "RISK_ON");
  assert.equal(result.brokerExecutionAllowed, false);
});

test("market AI blocks future data", () => {
  const result = buildMarketAiV1({
    indices: { NIKKEI: { return1d: 0.01, timestamp: "2026-08-03" } },
    asOf: "2026-08-02",
  });
  assert.equal(result.status, "BLOCKED");
  assert.equal(result.quality.futureLeakDetected, true);
});

test("strategy lab ranks out-of-sample candidates and keeps approval gate", () => {
  const result = runStrategyLabV1({
    strategies: [
      {
        id: "trend",
        inSample: { winRate: 0.62, profitFactor: 1.5, sharpe: 1.2, expectedValue: 0.01, maxDrawdown: 8 },
        outOfSample: { winRate: 0.59, profitFactor: 1.4, sharpe: 1.0, expectedValue: 0.008, maxDrawdown: 9, sampleSize: 150 },
      },
      {
        id: "overfit",
        inSample: { winRate: 0.9, profitFactor: 3, sharpe: 3, expectedValue: 0.05, maxDrawdown: 2 },
        outOfSample: { winRate: 0.4, profitFactor: 0.8, sharpe: 0.2, expectedValue: -0.01, maxDrawdown: 20, sampleSize: 50 },
      },
    ],
  });
  assert.equal(result.bestStrategy.id, "trend");
  assert.ok(result.rejectedStrategies.some((row) => row.id === "overfit"));
  assert.equal(result.productionUpdateAllowed, false);
  assert.equal(result.humanApprovalRequired, true);
});

test("continuous accuracy finds weak segments and drift", () => {
  const records = Array.from({ length: 10 }, (_, index) => ({
    outcome: 1,
    correct: index < 4,
    confidence: 80,
    action: "BUY",
    symbol: "7203.T",
    sector: "AUTO",
    regime: "BEAR",
  }));
  const result = analyzeContinuousAccuracyV1({ records, previous: { accuracy: 0.55 } });
  assert.equal(result.overall.accuracy, 0.4);
  assert.ok(result.suggestions.includes("RECALIBRATE_CONFIDENCE"));
  assert.ok(result.suggestions.includes("REVIEW_WEAK_SEGMENTS"));
  assert.ok(result.suggestions.includes("INVESTIGATE_ACCURACY_DRIFT"));
  assert.equal(result.automaticPromotionAllowed, false);
});
