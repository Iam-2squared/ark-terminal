import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState, STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import { processRealtimeFiveMinutePoint, PHASE57_REALTIME_ORCHESTRATOR_SAFETY } from "../realtime/phase57-realtime-orchestrator.js";

const AT = "2026-09-03T09:35:00+09:00";
const BAR_START = "2026-09-03T09:30:00+09:00";

function selectionRows() {
  return Array.from({ length: 160 }, (_, i) => ({
    symbol: String(1000 + i), sector: `S${i % 20}`, status: "analyzed", currentPrice: 500 + i,
    scannedAt: BAR_START,
    volume: 100000 + i * 1000, volumeRatio: 1 + (i % 7) * 0.2,
    dailyChangePercent: ((i % 11) - 5) * 0.4, atrPercent: 1.5 + (i % 5) * 0.2,
    discoveryScore: 40 + (i % 21), technicalScore: 42 + (i % 17),
    confidence: 0.55 + (i % 10) * 0.03, qualityScore: 60 + (i % 25),
  }));
}

function historyFor(rows) {
  const times = ["09:00", "09:05", "09:10", "09:15", "09:20", "09:25"];
  return Object.fromEntries(rows.map((row, i) => [row.symbol, times.map((hhmm, j) => ({
    timestamp: `2026-09-03T${hhmm}:00+09:00`, open: 490 + i + j, high: 492 + i + j,
    low: 489 + i + j, close: 491 + i + j, volume: 10000 + j * 100,
  }))]));
}

function currentBars(rows) {
  return rows.map((row, i) => ({ symbol: row.symbol, bar: {
    at: BAR_START, open: row.currentPrice - 1, high: row.currentPrice + 1, low: row.currentPrice - 2,
    close: row.currentPrice, volume: 20000 + i,
  }}));
}

function mockFrozenScore({ at, bars5m }) {
  assert.equal(bars5m.at(-1).timestamp, new Date(BAR_START).toISOString());
  return {
    complete: true,
    modelId: "TEST_FROZEN_MODEL",
    artifactSha256: "a".repeat(64),
    decision: {
      asOf: at,
      futureOutcomeUsed: false,
      frozenByPhase57: true,
      pointInTimeOnly: true,
      direction: 1,
      confidence: 0.8,
      setup: "TEST",
      context: {
        signalEligible: true,
        selectedHorizonBars: 1,
        probability: 0.7,
        selectedFeatureFamily: "TEST",
        selectedModelType: "TEST",
        selectedConfigId: "TEST",
        selectedThreshold: 0.5,
      },
    },
  };
}

test("one finalized point uses S bar only at T=S+5m then runs the full 28-way shadow pipeline", () => {
  const rows = selectionRows();
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const input = {
    at: AT,
    marketBars: currentBars(rows),
    selectionEntries: rows,
    barsBySymbolHistory: historyFor(rows),
    scoreEntry: mockFrozenScore,
    sessionQuality: "FULL_FRESH",
    missingBucketCount: 0,
    expectedBucketCount: 68,
  };
  const result = processRealtimeFiveMinutePoint(state, input);
  assert.equal(result.dashboard.strategyCount, 28);
  assert.equal(result.selection.v1 >= 20, true);
  assert.equal(result.selection.v2 >= 15, true);
  assert.equal(result.frozenEntryCount > 0, true);
  assert.equal(result.allocation.strategyCount, 28);
  assert.deepEqual(new Set(result.dashboard.strategies.map((x) => x.strategyId)), new Set(STRATEGY_IDS));
  assert.equal(state.lastBarTime, BAR_START);
  assert.equal(state.ledger.some((x) => x.type === "BAR_FINALIZED"), true);
  assert.equal(state.ledger.some((x) => x.type === "FEATURES_UPDATED"), true);
  assert.equal(state.ledger.some((x) => x.type === "DYNAMIC5M_SELECTION_COMMITTED"), true);
  assert.equal(state.ledger.some((x) => x.type === "FROZEN_ENTRY_DECISIONS_COMMITTED"), true);
  assert.equal(state.ledger.some((x) => x.type === "REALTIME_28WAY_ALLOCATION_COMMITTED"), true);
  assert.equal(state.ledger.some((x) => x.type === "STRATEGY_SNAPSHOT_COMMITTED"), true);
  const duplicate = processRealtimeFiveMinutePoint(state, input);
  assert.equal(duplicate, result);
  assert.equal(state.pipeline.history.length, 1);
});

test("orchestrator rejects a bar that is not finalized at the decision timestamp", () => {
  const rows = selectionRows();
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const bars = currentBars(rows);
  bars[0] = { ...bars[0], bar: { ...bars[0].bar, at: AT } };
  assert.throws(() => processRealtimeFiveMinutePoint(state, {
    at: AT,
    marketBars: bars,
    selectionEntries: rows,
    barsBySymbolHistory: historyFor(rows),
    scoreEntry: mockFrozenScore,
  }), /decisionAt = barStart \+ 5m/);
});

test("orchestrator remains research/shadow-only", () => {
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) {
    assert.equal(PHASE57_REALTIME_ORCHESTRATOR_SAFETY[key], false);
  }
});
