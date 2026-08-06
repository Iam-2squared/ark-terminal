import assert from "node:assert/strict";
import test from "node:test";

import { buildModelSegment, segmentRows } from "../strategy-selection/model-segmentation.js";
import { evaluateLiquidity } from "../strategy-selection/liquidity-gate.js";
import { evaluateCostAwareStrategy } from "../strategy-selection/cost-aware-evaluation.js";

test("buildModelSegment separates action horizon regime and industry", () => {
  const segment = buildModelSegment({ signal: "buy", evaluationHorizon: 5, marketRegime: "bull", industry: "AI" });
  assert.equal(segment.action, "BUY");
  assert.equal(segment.horizonBucket, "MEDIUM");
  assert.equal(segment.regime, "BULL");
  assert.equal(segment.industry, "AI");
  assert.equal(segment.key, "BUY::MEDIUM::BULL::AI");
});

test("segmentRows groups identical model segments", () => {
  const groups = segmentRows([
    { signal: "BUY", evaluationHorizon: 1, marketRegime: "BULL", industry: "TECH" },
    { signal: "BUY", evaluationHorizon: 3, marketRegime: "BULL", industry: "TECH" },
    { signal: "SELL", evaluationHorizon: 3, marketRegime: "BULL", industry: "TECH" },
  ]);
  assert.equal(groups.length, 2);
  assert.equal(groups.find((group) => group.segment.action === "BUY").rows.length, 2);
});

test("liquidity gate blocks low liquidity and passes healthy input", () => {
  const blocked = evaluateLiquidity({ price: 40, volume: 1000, spreadPercent: 3 });
  assert.equal(blocked.status, "BLOCKED");
  assert.ok(blocked.blockers.includes("PRICE_TOO_LOW_OR_MISSING"));
  assert.equal(blocked.safety.brokerWriteAllowed, false);

  const passed = evaluateLiquidity({ price: 500, volume: 200000, turnover: 100000000, spreadPercent: 0.5 });
  assert.equal(passed.status, "PASS");
  assert.deepEqual(passed.blockers, []);
});

test("cost-aware evaluation separates gross and net performance", () => {
  const result = evaluateCostAwareStrategy([
    { grossReturn: 2, feePercent: 0.1, slippagePercent: 0.2 },
    { grossReturn: -1, feePercent: 0.1, slippagePercent: 0.2 },
  ]);
  assert.equal(result.sampleCount, 2);
  assert.equal(result.grossAverageReturn, 0.5);
  assert.equal(result.netAverageReturn, 0.2);
  assert.equal(result.profitFactor, 1.7 / 1.3);
  assert.equal(result.safety.automaticPromotionAllowed, false);
  assert.equal(result.safety.productionUpdateAllowed, false);
});
