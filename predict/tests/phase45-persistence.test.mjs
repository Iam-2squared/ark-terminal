import test from "node:test";
import assert from "node:assert/strict";
import { buildPhase45PersistencePlan } from "../data/phase45-persistence.js";

const validRows = [
  { kind: "OHLCV", symbol: "7203.T", Date: "2026-08-01", Open: 100, High: 110, Low: 95, Close: 108, "Adj Close": 108, Volume: 1000, source: "FIXTURE" },
  { kind: "INDEX", symbol: "TOPIX", Date: "2026-08-01", Close: 2800, source: "FIXTURE" },
];

test("builds a Phase41-ready persistence plan", () => {
  const plan = buildPhase45PersistencePlan({ records: validRows, provider: "CSV", runId: "test-run" });
  assert.equal(plan.status, "READY_TO_PERSIST");
  assert.equal(plan.checkpoint.runId, "test-run");
  assert.equal(plan.brokerWrites, 0);
  assert.equal(plan.excelOrderWrites, 0);
  assert.equal(plan.rssOrderCalls, 0);
  assert.equal(plan.liveOrders, 0);
});

test("blocks invalid historical data before persistence", () => {
  const plan = buildPhase45PersistencePlan({ records: [
    { kind: "OHLCV", symbol: "7203.T", Date: "2026-08-01", Open: 120, High: 110, Low: 95, Close: 108, Volume: 1000 },
  ] });
  assert.equal(plan.status, "BLOCKED");
  assert.equal(plan.ingestionPlan, null);
  assert.equal(plan.checkpoint, null);
});

test("keeps every execution path disabled", () => {
  const plan = buildPhase45PersistencePlan({ records: validRows });
  assert.deepEqual(plan.safety, {
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
