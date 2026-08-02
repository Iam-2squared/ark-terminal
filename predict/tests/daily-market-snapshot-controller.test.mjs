import assert from "node:assert/strict";
import test from "node:test";

import {
  DailyMarketSnapshotController,
  tokyoMarketDateKey,
} from "../analysis/daily-market-snapshot-controller.js";

function state(timestamp = Date.parse("2026-08-03T06:00:00Z")) {
  return {
    symbol: "7203.T",
    history: { candles: [{ time: timestamp / 1000 }] },
    analysis: { totalScore: 70 },
    prediction: { confidence: 80 },
  };
}

test("Tokyo market date changes at Japanese midnight", () => {
  assert.equal(tokyoMarketDateKey("2026-08-02T14:59:59Z"), "2026-08-02");
  assert.equal(tokyoMarketDateKey("2026-08-02T15:00:00Z"), "2026-08-03");
});

test("Daily controller captures once per symbol and Tokyo market date", async () => {
  let currentState = state();
  let latest = null;
  let runnerCalls = 0;
  const controller = new DailyMarketSnapshotController({
    stateProvider: () => currentState,
    eventTarget: null,
    intervalMs: 0,
    inputBuilder({ state: supplied, settings }) {
      assert.equal(supplied, currentState);
      assert.equal(
        settings.marketIntelligence.captureHistoricalSnapshots,
        true,
      );
      return { symbol: supplied.symbol, marketIntelligence: {} };
    },
    runtimeRunner(input) {
      runnerCalls += 1;
      assert.equal(input.captureMarketIntelligenceSnapshot, true);
      latest = {
        id: `snapshot-${runnerCalls}`,
        symbol: input.symbol,
        asOf: new Date(currentState.history.candles[0].time * 1000).toISOString(),
        contentFingerprint: `fingerprint-${runnerCalls}`,
      };
      return {
        marketIntelligenceSnapshot: {
          status: "captured",
          reference: latest,
        },
      };
    },
    snapshotService: { latest: () => latest },
  });

  const first = await controller.capture();
  const duplicate = await controller.capture();

  assert.equal(first.status, "captured");
  assert.equal(duplicate.status, "duplicate");
  assert.equal(runnerCalls, 1);
  assert.equal(first.executionAllowed, false);

  currentState = state(Date.parse("2026-08-04T06:00:00Z"));
  const nextDay = await controller.capture();

  assert.equal(nextDay.status, "captured");
  assert.equal(runnerCalls, 2);
});

test("Daily controller waits safely until an analysis state exists", async () => {
  const controller = new DailyMarketSnapshotController({
    stateProvider: () => null,
    eventTarget: null,
    intervalMs: 0,
    inputBuilder() {
      throw new Error("must not run");
    },
    runtimeRunner() {
      throw new Error("must not run");
    },
    snapshotService: { latest: () => null },
  });

  const result = await controller.capture();
  assert.equal(result.status, "unavailable");
  assert.equal(result.reason, "analysis_state_unavailable");
  assert.equal(result.executionAllowed, false);
});

test("Daily controller validates required boundaries", () => {
  assert.throws(
    () => new DailyMarketSnapshotController(),
    /state provider is required/,
  );
  assert.throws(
    () =>
      new DailyMarketSnapshotController({
        stateProvider() {},
        snapshotService: {},
      }),
    /snapshot service is invalid/,
  );
});
