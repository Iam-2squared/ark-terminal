import test from "node:test";
import assert from "node:assert/strict";
import { buildShadowDecision, normalizeShadowSnapshot, settleShadowDecision } from "../predict/shadow/phase50-shadow-live.js";
import { runShadowSession, verifyShadowReport } from "../predict/shadow/phase50-shadow-session.js";

const base = {
  symbol: "7203.T",
  bid: 2999,
  ask: 3001,
  last: 3000,
  volume: 100000,
  observedAt: "2026-08-06T00:00:00.000Z",
};

test("normalizes read-only shadow snapshots", () => {
  const snapshot = normalizeShadowSnapshot(base);
  assert.equal(snapshot.readOnly, true);
  assert.equal(snapshot.source, "MARKETSPEED_RSS_READ_ONLY");
});

test("shadow decisions can never transmit", () => {
  const decision = buildShadowDecision({ snapshot: base, signal: { side: "BUY", confidence: 0.8, expectedReturn: 0.02 } });
  assert.equal(decision.mode, "SHADOW_ONLY");
  assert.equal(decision.transmissionAllowed, false);
  assert.equal(decision.transmitted, false);
  assert.equal(decision.safety.brokerWriteAllowed, false);
  assert.equal(decision.safety.excelOrderWriteAllowed, false);
  assert.equal(decision.safety.rssOrderFunctionAllowed, false);
});

test("settles cost-aware shadow decisions", () => {
  const decision = buildShadowDecision({ snapshot: base, signal: { side: "BUY", confidence: 0.8, expectedReturn: 0.02 } });
  const settlement = settleShadowDecision({
    decision,
    nextSnapshot: { ...base, bid: 3020, ask: 3022, last: 3021, observedAt: "2026-08-06T01:00:00.000Z" },
    feeBps: 5,
    slippageBps: 5,
  });
  assert.equal(settlement.transmitted, false);
  assert.ok(settlement.netReturn > 0);
});

test("runs a complete shadow session with zero order writes", () => {
  const report = runShadowSession({
    observations: [
      base,
      { ...base, bid: 3020, ask: 3022, last: 3021, observedAt: "2026-08-06T01:00:00.000Z" },
      { ...base, bid: 3010, ask: 3012, last: 3011, observedAt: "2026-08-06T02:00:00.000Z" },
    ],
    signals: [
      { side: "BUY", confidence: 0.8, expectedReturn: 0.02 },
      { side: "SELL", confidence: 0.7, expectedReturn: -0.01 },
    ],
    feeBps: 2,
    slippageBps: 3,
  });
  assert.equal(report.status, "SHADOW_COMPLETE");
  assert.equal(report.transmittedOrderCount, 0);
  assert.equal(report.brokerWriteCount, 0);
  assert.equal(report.excelOrderWriteCount, 0);
  assert.equal(report.rssOrderFunctionCallCount, 0);
  assert.equal(verifyShadowReport(report).status, "VALID");
});
