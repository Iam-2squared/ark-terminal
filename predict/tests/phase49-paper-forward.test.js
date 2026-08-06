import test from "node:test";
import assert from "node:assert/strict";
import {
  PHASE49_SAFETY,
  auditPaperForwardCycle,
  buildPaperForwardCycle,
  buildPaperOrderIdea,
  settlePaperTrade,
  simulatePaperFill,
  summarizePaperTrades,
} from "../paper/phase49-paper-forward.js";

test("builds deterministic paper-only order ideas", () => {
  const input = { symbol: "7203.T", probabilityUp: 0.64, confidence: 0.72, expectedReturn: 0.03, close: 2500, quantity: 100 };
  const a = buildPaperOrderIdea(input);
  const b = buildPaperOrderIdea(input);
  assert.equal(a.mode, "PAPER_ONLY");
  assert.equal(a.transmissionAllowed, false);
  assert.equal(a.orderId, b.orderId);
});

test("simulates fill and settlement with costs", () => {
  const order = buildPaperOrderIdea({ symbol: "7203.T", probabilityUp: 0.7, close: 1000, quantity: 10 });
  const fill = simulatePaperFill(order, { open: 1000 }, { spreadBps: 5, slippageBps: 10, feeBps: 2 });
  const trade = settlePaperTrade(fill, { exitPrice: 1020 });
  assert.equal(fill.transmitted, false);
  assert.equal(trade.status, "SETTLED_PAPER");
  assert.ok(Number.isFinite(trade.netPnl));
});

test("summarizes paper trades", () => {
  const order = buildPaperOrderIdea({ symbol: "7203.T", probabilityUp: 0.7, close: 1000, quantity: 10 });
  const fill = simulatePaperFill(order, { open: 1000 }, { spreadBps: 0, slippageBps: 0, feeBps: 0 });
  const trade = settlePaperTrade(fill, { exitPrice: 1010 });
  const summary = summarizePaperTrades([trade]);
  assert.equal(summary.tradeCount, 1);
  assert.equal(summary.winRate, 1);
});

test("runs and audits a complete paper-forward cycle", () => {
  const cycle = buildPaperForwardCycle({
    predictions: [
      { symbol: "7203.T", probabilityUp: 0.6, confidence: 0.7, expectedReturn: 0.02, close: 1000, quantity: 10 },
      { symbol: "6758.T", probabilityUp: 0.4, confidence: 0.65, expectedReturn: -0.01, close: 5000, quantity: 2 },
    ],
    marketBySymbol: { "7203.T": { open: 1000 }, "6758.T": { open: 5000 } },
    outcomeBySymbol: { "7203.T": { exitPrice: 1015 }, "6758.T": { exitPrice: 4950 } },
  });
  assert.equal(cycle.status, "PAPER_FORWARD_COMPLETE");
  assert.equal(auditPaperForwardCycle(cycle).status, "VALID");
  assert.equal(cycle.brokerWrites, 0);
  assert.equal(cycle.excelOrderWrites, 0);
  assert.equal(cycle.rssOrderCalls, 0);
  assert.equal(cycle.liveOrders, 0);
});

test("blocks tampered cycle and preserves safety invariants", () => {
  const cycle = buildPaperForwardCycle({
    predictions: [{ symbol: "7203.T", probabilityUp: 0.6, close: 1000 }],
    marketBySymbol: { "7203.T": { open: 1000 } },
    outcomeBySymbol: { "7203.T": { exitPrice: 1010 } },
  });
  assert.equal(auditPaperForwardCycle({ ...cycle, liveOrders: 1 }).status, "BLOCKED");
  assert.deepEqual(PHASE49_SAFETY, {
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    humanApprovalRequired: true,
  });
});
