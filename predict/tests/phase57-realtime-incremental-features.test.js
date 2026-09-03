import assert from "node:assert/strict";
import test from "node:test";
import { createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { applyMarketFiveMinuteBar, createSymbolFeatureState, applyFiveMinuteBar } from "../realtime/phase57-incremental-features.js";

test("updates rolling features using only each arriving 5m bar", () => {
  const state = createSymbolFeatureState("7203", { windows: [2, 3] });
  const f1 = applyFiveMinuteBar(state, { at: "2026-09-02T09:05:00+09:00", open: 100, high: 102, low: 99, close: 101, volume: 1000 });
  assert.equal(f1.barsSeen, 1);
  assert.equal(f1.barReturnPercent, null);
  assert.equal(f1.rolling[2].n, 1);

  const f2 = applyFiveMinuteBar(state, { at: "2026-09-02T09:10:00+09:00", open: 101, high: 104, low: 100, close: 103, volume: 2000 });
  assert.equal(f2.barsSeen, 2);
  assert.equal(f2.rolling[2].n, 2);
  assert.equal(f2.rolling[2].closeSma, 102);
  assert.equal(f2.cumulativeVolume, 3000);

  const f3 = applyFiveMinuteBar(state, { at: "2026-09-02T09:15:00+09:00", open: 103, high: 105, low: 102, close: 104, volume: 3000 });
  assert.equal(f3.rolling[2].n, 2);
  assert.equal(f3.rolling[2].closeSma, 103.5);
  assert.equal(f3.rolling[3].n, 3);
  assert.equal(state.rolling[2].length, 2);
});

test("rejects duplicate or backward bars instead of rewriting state", () => {
  const state = createSymbolFeatureState("8306");
  const bar = { at: "2026-09-02T09:05:00+09:00", open: 100, high: 101, low: 99, close: 100, volume: 10 };
  applyFiveMinuteBar(state, bar);
  assert.throws(() => applyFiveMinuteBar(state, bar), /strictly causal/);
  assert.equal(state.barsSeen, 1);
});

test("keeps per-symbol state inside the realtime session", () => {
  const session = createRealtimeSessionState({ sessionDate: "2026-09-02" });
  applyMarketFiveMinuteBar(session, { symbol: "7203", windows: [2], bar: { at: "2026-09-02T09:05:00+09:00", open: 100, high: 101, low: 99, close: 100, volume: 10 } });
  applyMarketFiveMinuteBar(session, { symbol: "8306", windows: [2], bar: { at: "2026-09-02T09:05:00+09:00", open: 200, high: 202, low: 198, close: 201, volume: 20 } });
  assert.equal(session.symbols["7203"].barsSeen, 1);
  assert.equal(session.symbols["8306"].barsSeen, 1);
  assert.equal(session.lastBarTime, "2026-09-02T09:05:00+09:00");
});

test("rejects market-wide cross-symbol timestamp regression while allowing a shared bucket", () => {
  const session = createRealtimeSessionState({ sessionDate: "2026-09-02" });
  const bar = (at, price) => ({ at, open: price, high: price + 1, low: price - 1, close: price, volume: 10 });
  applyMarketFiveMinuteBar(session, { symbol: "7203", bar: bar("2026-09-02T10:35:00+09:00", 100) });
  applyMarketFiveMinuteBar(session, { symbol: "8306", bar: bar("2026-09-02T10:35:00+09:00", 200) });
  assert.throws(
    () => applyMarketFiveMinuteBar(session, { symbol: "9984", bar: bar("2026-09-02T10:30:00+09:00", 300) }),
    /cannot move backward across symbols/,
  );
  assert.equal(session.symbols["9984"], undefined);
  assert.equal(session.lastBarTime, "2026-09-02T10:35:00+09:00");
});
