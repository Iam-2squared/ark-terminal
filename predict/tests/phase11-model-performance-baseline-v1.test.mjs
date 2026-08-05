import test from "node:test";
import assert from "node:assert/strict";

import {
  createModelPerformanceBaseline,
  ModelPerformanceBaselineStoreV1,
} from "../learning/model-performance-baseline-v1.js";

function records() {
  return [
    { action: "BUY", status: "WIN", returnPercent: 4, sector: "TECH", marketRegime: "BULL" },
    { action: "BUY", status: "LOSS", returnPercent: -2, sector: "TECH", marketRegime: "BULL" },
    { action: "SELL", status: "WIN", returnPercent: 3, sector: "AUTO", marketRegime: "BEAR" },
    { action: "SELL", status: "LOSS", returnPercent: -1, sector: "AUTO", marketRegime: "BEAR" },
    { action: "NO_TRADE", status: "WIN", returnPercent: 10, sector: "TECH", marketRegime: "BULL" },
    { action: "BUY", status: "PENDING", returnPercent: 5, sector: "TECH", marketRegime: "BULL" },
  ];
}

function memoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => map.has(key) ? map.get(key) : null,
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
  };
}

test("Phase11 Part1 freezes overall production baseline from closed trades only", () => {
  const result = createModelPerformanceBaseline({
    records: records(),
    productionModel: { version: "production-v3" },
    generatedAt: "2026-08-05T00:00:00.000Z",
  });

  assert.equal(result.productionModelVersion, "production-v3");
  assert.equal(result.sourceTradeCount, 4);
  assert.equal(result.overall.count, 4);
  assert.equal(result.overall.winRate, 50);
  assert.equal(result.overall.profitFactor, 7 / 3);
  assert.equal(result.frozen, true);
  assert.equal(Object.isFrozen(result), true);
});

test("Phase11 Part1 provides BUY SELL, Bull Bear, and sector baselines", () => {
  const result = createModelPerformanceBaseline({ records: records() });

  assert.equal(result.byAction.BUY.count, 2);
  assert.equal(result.byAction.SELL.count, 2);
  assert.equal(result.byRegime.BULL.count, 2);
  assert.equal(result.byRegime.BEAR.count, 2);
  assert.equal(result.bySector.TECH.count, 2);
  assert.equal(result.bySector.AUTO.count, 2);
});

test("Phase11 Part1 warns on insufficient sample and blocks production changes", () => {
  const result = createModelPerformanceBaseline({ records: records() });

  assert.ok(result.warnings.includes("INSUFFICIENT_BASELINE_SAMPLE"));
  assert.equal(result.safety.productionUpdateAllowed, false);
  assert.equal(result.safety.humanApprovalRequired, true);
  assert.equal(result.safety.brokerExecutionAllowed, false);
});

test("Phase11 Part1 persists one frozen baseline and prevents accidental overwrite", () => {
  const storage = memoryStorage();
  const store = new ModelPerformanceBaselineStoreV1({ storage });
  const first = createModelPerformanceBaseline({ records: records(), productionModel: { version: "v1" } });
  const second = createModelPerformanceBaseline({ records: records(), productionModel: { version: "v2" } });

  store.freeze(first);
  assert.equal(store.load().productionModelVersion, "v1");
  assert.throws(() => store.freeze(second), /BASELINE_ALREADY_FROZEN/);
  store.freeze(second, { replace: true });
  assert.equal(store.load().productionModelVersion, "v2");
});

test("Phase11 Part1 requires human approval to clear a frozen baseline", () => {
  const storage = memoryStorage();
  const store = new ModelPerformanceBaselineStoreV1({ storage });
  store.freeze(createModelPerformanceBaseline({ records: records() }));

  assert.throws(() => store.clear(), /HUMAN_APPROVAL_REQUIRED/);
  store.clear({ approvedBy: "human-reviewer" });
  assert.equal(store.load(), null);
});
