import assert from "node:assert/strict";
import test from "node:test";

import { buildShadowOrderProposal } from "../shadow/order-proposal.js";
import { assessShadowFillFeasibility } from "../shadow/fill-feasibility.js";
import { comparePaperAndShadow } from "../shadow/paper-shadow-diff.js";

test("Phase26 Part1 builds shadow-only order proposal without execution rights", () => {
  const result = buildShadowOrderProposal({
    symbol: "7203.t",
    signal: "BUY",
    referencePrice: 2500,
    quantity: 100,
    stopLossPercent: 3,
    takeProfitPercent: 6,
  });

  assert.equal(result.status, "READY_FOR_SHADOW_REVIEW");
  assert.equal(result.proposal.symbol, "7203.T");
  assert.equal(result.proposal.limitPrice, 2500);
  assert.equal(result.proposal.stopLossPrice, 2425);
  assert.equal(result.proposal.takeProfitPrice, 2650);
  assert.equal(result.proposal.maxLoss, 7500);
  assert.equal(result.safety.executionAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
  assert.equal(result.safety.orderCreationAllowed, false);
});

test("Phase26 Part1 blocks invalid proposal inputs", () => {
  const result = buildShadowOrderProposal({ symbol: "", side: "HOLD", referencePrice: 0, quantity: 0 });
  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("SYMBOL_MISSING"));
  assert.ok(result.blockers.includes("SIDE_NOT_DIRECTIONAL"));
  assert.ok(result.blockers.includes("REFERENCE_PRICE_INVALID"));
  assert.ok(result.blockers.includes("QUANTITY_INVALID"));
});

test("Phase26 Part2 evaluates feasible shadow fill", () => {
  const result = assessShadowFillFeasibility({
    quantity: 100,
    spreadPercent: 0.4,
    dailyVolume: 500000,
    availableAtPrice: 300,
    expectedDelayMs: 250,
  });

  assert.equal(result.status, "FEASIBLE");
  assert.equal(result.metrics.estimatedFillRatio, 1);
  assert.equal(result.safety.liveTradingAllowed, false);
});

test("Phase26 Part2 blocks wide spread and insufficient visible liquidity", () => {
  const result = assessShadowFillFeasibility({
    quantity: 1000,
    spreadPercent: 2,
    dailyVolume: 5000,
    availableAtPrice: 100,
  });

  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("SPREAD_TOO_WIDE"));
  assert.ok(result.blockers.includes("PARTICIPATION_TOO_HIGH"));
  assert.ok(result.blockers.includes("INSUFFICIENT_VISIBLE_LIQUIDITY"));
});

test("Phase26 Part3 reports paper and shadow within tolerance", () => {
  const result = comparePaperAndShadow({
    paperPrice: 1000,
    shadowPrice: 1005,
    paperFillRatio: 1,
    shadowFillRatio: 0.95,
    paperDelayMs: 100,
    shadowDelayMs: 500,
  });

  assert.equal(result.status, "WITHIN_TOLERANCE");
  assert.ok(Math.abs(result.metrics.priceDifferencePercent - 0.5) < 1e-12);
  assert.equal(result.safety.brokerWriteAllowed, false);
});

test("Phase26 Part3 blocks excessive price, fill and delay divergence", () => {
  const result = comparePaperAndShadow({
    paperPrice: 1000,
    shadowPrice: 1020,
    paperFillRatio: 1,
    shadowFillRatio: 0.5,
    paperDelayMs: 0,
    shadowDelayMs: 2000,
  });

  assert.equal(result.status, "BLOCKED");
  assert.ok(result.blockers.includes("PRICE_DIFFERENCE_TOO_LARGE"));
  assert.ok(result.blockers.includes("SHADOW_FILL_RATIO_TOO_LOW"));
  assert.ok(result.blockers.includes("SHADOW_DELAY_TOO_HIGH"));
});
