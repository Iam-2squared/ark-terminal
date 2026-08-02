import assert from "node:assert/strict";
import test from "node:test";

import { refreshPredictionOutcomes } from "../analysis/prediction-outcome-service.js";

function record({ id, symbol, status = "pending", period = 1 } = {}) {
  return {
    id,
    symbol,
    status,
    period,
    analysisTime: 100,
    predictionPrice: 100,
    score: 80,
  };
}

test("Outcome refresh groups pending records and isolates provider failures", async () => {
  const records = [
    record({ id: "a", symbol: "7203.T" }),
    record({ id: "b", symbol: "7203.T" }),
    record({ id: "c", symbol: "6758.T" }),
    record({ id: "done", symbol: "9984.T", status: "resolved" }),
  ];
  const calls = [];
  const result = await refreshPredictionOutcomes({
    records,
    async fetchHistory(symbol) {
      calls.push(symbol);
      if (symbol === "6758.T") throw new Error("provider unavailable");
      return { provider: "test", candles: [{ time: 100 }, { time: 200 }] };
    },
    resolver(current, symbol) {
      return {
        changed: true,
        records: current.map((item) =>
          item.symbol === symbol && item.status === "pending"
            ? { ...item, status: "resolved", hit: true }
            : item,
        ),
      };
    },
  });

  assert.deepEqual(calls.sort(), ["6758.T", "7203.T"]);
  assert.equal(result.status, "partial");
  assert.equal(result.resolvedCount, 2);
  assert.deepEqual(result.resolvedIds.sort(), ["a", "b"]);
  assert.equal(result.errors[0].symbol, "6758.T");
  assert.equal(result.records.find((item) => item.id === "c").status, "pending");
  assert.equal(result.executionAllowed, false);
  assert.equal(records[0].status, "pending");
});

test("Outcome refresh returns ready without network calls when nothing is pending", async () => {
  let calls = 0;
  const result = await refreshPredictionOutcomes({
    records: [record({ id: "done", symbol: "7203.T", status: "resolved" })],
    async fetchHistory() {
      calls += 1;
      return { candles: [] };
    },
  });

  assert.equal(calls, 0);
  assert.equal(result.status, "ready");
  assert.equal(result.changed, false);
  assert.equal(result.pendingSymbolCount, 0);
});

test("Outcome refresh rejects invalid dependencies", async () => {
  await assert.rejects(
    refreshPredictionOutcomes({ records: {}, fetchHistory() {} }),
    /records must be an array/,
  );
  await assert.rejects(
    refreshPredictionOutcomes({ records: [] }),
    /history provider is required/,
  );
});
