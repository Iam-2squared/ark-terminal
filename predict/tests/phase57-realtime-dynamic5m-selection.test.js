import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { applyRealtimeDynamic5mSelection } from "../realtime/phase57-realtime-dynamic5m-selection.js";
import { buildIntradayDynamicUniverseTimeline } from "../daytrade/phase57-p25-intraday-dynamic-universe.js";
import { buildIntradayDynamicUniverseTimelineV2 } from "../daytrade/phase57-p25-intraday-dynamic-universe-v2.js";

function rows() {
  return Array.from({ length: 160 }, (_, i) => ({
    symbol: String(1000 + i),
    sector: `S${i % 20}`,
    status: "analyzed",
    scannedAt: "2026-09-03T09:30:00+09:00",
    currentPrice: 500 + i,
    volume: 100000 + i * 1000,
    volumeRatio: 1 + (i % 7) * 0.2,
    dailyChangePercent: ((i % 11) - 5) * 0.4,
    atrPercent: 1.5 + (i % 5) * 0.2,
    discoveryScore: 40 + (i % 21),
    technicalScore: 42 + (i % 17),
    confidence: 0.55 + (i % 10) * 0.03,
    qualityScore: 60 + (i % 25),
  }));
}

test("realtime V1/V2 matches frozen batch selectors for the same causal snapshot", () => {
  const at = "2026-09-03T09:35:00+09:00";
  const entries = rows();
  const session = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const realtime = applyRealtimeDynamic5mSelection(session, { at, entries });
  const v1 = buildIntradayDynamicUniverseTimeline({ snapshots: [{ asOf: at, entries }] }).points[0];
  const v2 = buildIntradayDynamicUniverseTimelineV2({ snapshots: [{ asOf: at, entries }], priorSelections: [] }).points[0];
  assert.equal(v1.rawUniverse.length >= 20, true);
  assert.equal(v2.rawUniverse.length >= 15, true);
  assert.deepEqual(realtime.selectedV1.map((x) => x.symbol), v1.rawUniverse.map((x) => x.symbol));
  assert.deepEqual(realtime.selectedV2.map((x) => x.symbol), v2.rawUniverse.map((x) => x.symbol));
});

test("V2 persistence consumes only earlier realtime selection points", () => {
  const session = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const entries = rows();
  const p1 = applyRealtimeDynamic5mSelection(session, { at: "2026-09-03T09:35:00+09:00", entries });
  const altered = entries.map((row, i) => ({ ...row, volumeRatio: row.volumeRatio + (i % 3) * 0.1 }));
  const p2 = applyRealtimeDynamic5mSelection(session, { at: "2026-09-03T09:40:00+09:00", entries: altered });
  assert.equal(p1.priorV2PointCount, 0);
  assert.equal(p2.priorV2PointCount, 1);
  assert.equal(session.selection.history.length, 2);
  assert.equal(session.selection.priorV2.length, 2);
});

test("V2 persistence matches the frozen batch selector across at least four causal points", () => {
  const session = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const prior = [];
  const times = ["09:35", "09:40", "09:45", "09:50", "09:55"];
  for (let point = 0; point < times.length; point += 1) {
    const at = `2026-09-03T${times[point]}:00+09:00`;
    const entries = rows().map((row, i) => ({
      ...row,
      volumeRatio: row.volumeRatio + ((i + point) % 5) * 0.07,
      dailyChangePercent: row.dailyChangePercent + ((i + point) % 3) * 0.05,
    }));
    const batch = buildIntradayDynamicUniverseTimelineV2({
      snapshots: [{ asOf: at, entries }],
      priorSelections: prior,
    }).points[0];
    const realtime = applyRealtimeDynamic5mSelection(session, { at, entries });
    assert.equal(batch.rawUniverse.length >= 15, true, `V2 fixture must clear the frozen Entry gate at point ${point + 1}`);
    assert.deepEqual(
      realtime.selectedV2.map((x) => x.symbol),
      batch.rawUniverse.map((x) => x.symbol),
      `V2 mismatch at point ${point + 1}`,
    );
    prior.push(realtime.selectedV2.map((x) => x.symbol));
    while (prior.length > 3) prior.shift();
  }
  assert.equal(session.selection.history.length, 5);
  assert.equal(session.selection.priorV2.length, 3);
});

test("duplicate/backward selection points cannot overwrite committed history", () => {
  const session = createRealtimeSessionState({ sessionDate: "2026-09-03" });
  const entries = rows();
  const at = "2026-09-03T09:35:00+09:00";
  applyRealtimeDynamic5mSelection(session, { at, entries });
  assert.throws(() => applyRealtimeDynamic5mSelection(session, { at, entries }), /strictly causal/);
  assert.equal(session.selection.history.length, 1);
  assert.equal(session.ledger.filter((x) => x.type === "DYNAMIC5M_SELECTION_COMMITTED").length, 1);
});
