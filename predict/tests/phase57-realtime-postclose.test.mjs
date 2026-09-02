import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState, STRATEGY_IDS } from "../realtime/phase57-stateful-contract.js";
import { commitRealtimeDashboardSnapshot } from "../realtime/phase57-realtime-dashboard.js";
import {
  scoreRealtimeSessionFromLedger,
  replayRealtimeSnapshotsFromLedger,
  compareRealtimePostCloseToBatch,
  PHASE57_REALTIME_POSTCLOSE_SAFETY,
} from "../realtime/phase57-realtime-postclose.js";

const A = "2026-09-03T01:35:00.000Z";
const B = "2026-09-03T01:40:00.000Z";

function stateWithSnapshots() {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  state.lastBarTime = A;
  commitRealtimeDashboardSnapshot(state, { at: A, sessionQuality: "FULL_FRESH", missingBucketCount: 0, expectedBucketCount: 68 });
  const s = state.strategies["V1_V3__MAX_10"];
  s.closedTrades = 1;
  s.wins = 1;
  s.grossProfit = 10_000;
  s.realizedPnl = 10_000;
  s.cash = 1_010_000;
  s.equity = 1_010_000;
  s.netPercent = 1;
  s.peakEquity = 1_010_000;
  state.lastBarTime = B;
  commitRealtimeDashboardSnapshot(state, { at: B, sessionQuality: "FULL_FRESH", missingBucketCount: 0, expectedBucketCount: 68 });
  return state;
}

test("post-close scores only durable realtime snapshots and exposes exactly 28 strategies", () => {
  const state = stateWithSnapshots();
  const score = scoreRealtimeSessionFromLedger(state.ledger, { sessionDate: state.sessionDate });
  assert.equal(score.strategyCount, 28);
  assert.equal(score.strategies.length, 28);
  assert.equal(score.complete, true);
  assert.equal(score.coveragePercent, 100);
  const row = score.strategies.find((x) => x.strategyId === "V1_V3__MAX_10");
  assert.equal(row.n, 1);
  assert.equal(row.netPercent, 1);
  assert.equal(row.realizedPnl, 10_000);
  assert.equal(row.winRate, 100);
});

test("ledger replay reconstructs immutable intraday Net curve without post-close decision recompute", () => {
  const state = stateWithSnapshots();
  const replay = replayRealtimeSnapshotsFromLedger(state.ledger, { sessionDate: state.sessionDate });
  assert.equal(replay.snapshotCount, 2);
  assert.equal(replay.netCurve[0].at, A);
  assert.equal(replay.netCurve[1].at, B);
  assert.equal(replay.netCurve[1].strategies.find((x) => x.strategyId === "V1_V3__MAX_10").netPercent, 1);
  assert.equal(replay.ledgerHeadHash, state.ledgerHeadHash);
});

test("post-close preserves incomplete-session classification and missing coverage", () => {
  const state = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  state.lastBarTime = A;
  commitRealtimeDashboardSnapshot(state, { at: A, sessionQuality: "PARTIAL_INCOMPLETE_SESSION", missingBucketCount: 31, expectedBucketCount: 68 });
  const score = scoreRealtimeSessionFromLedger(state.ledger, { sessionDate: state.sessionDate });
  assert.equal(score.complete, false);
  assert.equal(score.missingBucketCount, 31);
  assert.equal(score.coveragePercent, (37 / 68) * 100);
});

test("batch/realtime comparator reports exact parity and mismatches without tuning", () => {
  const state = stateWithSnapshots();
  const score = scoreRealtimeSessionFromLedger(state.ledger, { sessionDate: state.sessionDate });
  const batch = score.strategies.map((row) => ({ ...row }));
  assert.equal(compareRealtimePostCloseToBatch(score, batch).parity, true);
  batch[0].netPercent += 0.01;
  const mismatch = compareRealtimePostCloseToBatch(score, batch);
  assert.equal(mismatch.parity, false);
  assert.equal(mismatch.mismatchCount, 1);
  assert.equal(mismatch.mismatches[0].field, "netPercent");
});

test("post-close safety remains shadow-only and rejects tampered ledger", () => {
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) {
    assert.equal(PHASE57_REALTIME_POSTCLOSE_SAFETY[key], false);
  }
  const state = stateWithSnapshots();
  const ledger = state.ledger.map((row) => ({ ...row }));
  ledger.at(-1).strategies = ledger.at(-1).strategies.map((row, index) => index === 0 ? { ...row, netPercent: 999 } : row);
  assert.throws(() => scoreRealtimeSessionFromLedger(ledger, { sessionDate: state.sessionDate }), /eventHash mismatch/);
  assert.equal(new Set(STRATEGY_IDS).size, 28);
});
