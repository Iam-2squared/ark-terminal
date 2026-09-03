import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  buildMsiiEnvelopeFromRealtimeState,
  PHASE57_MSII_DEFAULT_VERSIONS,
} from "../../tools/phase57_export_msii_envelope.mjs";

const DATE = "2026-09-04";
const AT = "2026-09-04T00:35:00.000Z";

function frozenEntry() {
  const cells = ["V1_V3", "V1_V4"];
  const strategyIds = STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`)));
  return Object.freeze({
    candidateId: `${DATE}|${AT}|DYNAMIC5M_V1|7203`,
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: "7203",
    sessionDate: DATE,
    entryTimestamp: AT,
    signalDirection: 1,
    entryPrice: 100,
    confidence: 0.8,
    probability: 0.75,
    sector: "TEST",
    contextBars: Object.freeze([]),
    selectionLineage: Object.freeze({ variant: "V1", opportunityScore: 0.8, v2Score: null }),
    strategyLineage: Object.freeze({ cells: Object.freeze(cells), strategyIds: Object.freeze(strategyIds) }),
  });
}

test("Lane Y realtime state exports an immutable exact-timestamp Lane M envelope", () => {
  const state = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(state, {
    at: AT,
    entries: [frozenEntry()],
    marksBySymbol: { "7203": 100 },
  });
  const point = Object.freeze({
    at: AT,
    allocation,
    exitEvaluation: Object.freeze({ at: AT, closed: Object.freeze([]) }),
    safety: state.safety,
  });
  state.pipeline = { lastPointTime: AT, lastRequestSha256: "fixture", history: [point] };

  const envelope = buildMsiiEnvelopeFromRealtimeState(state, {
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
  });
  assert.equal(envelope.status, "PHASE57_MSII_RUNTIME_ENVELOPE_READY");
  assert.equal(envelope.sessionDate, DATE);
  assert.equal(envelope.pointResult.at, AT);
  assert.equal(envelope.backfillUsed, false);
  assert.equal(envelope.laneYDecisions.length, 14);
  assert.ok(envelope.laneYDecisions.every((row) => row.intentKind === "ENTRY" && row.decisionAt === AT));
  assert.deepEqual(envelope.versions, PHASE57_MSII_DEFAULT_VERSIONS);
  assert.equal(envelope.methodology.exactLaneYDecisionTimestampPreserved, true);
  assert.equal(envelope.methodology.futureOutcomeUsed, false);
  assert.equal(envelope.safety.liveTradingAllowed, false);
  assert.equal(envelope.safety.rssOrderFunctionAllowed, false);
});

test("Lane M envelope export fails closed on unsafe or inconsistent Lane Y state", () => {
  const state = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(state, {
    at: AT,
    entries: [frozenEntry()],
    marksBySymbol: { "7203": 100 },
  });
  state.pipeline = { lastPointTime: AT, lastRequestSha256: "fixture", history: [{ at: AT, allocation, exitEvaluation: { at: AT, closed: [] }, safety: state.safety }] };
  const unsafe = structuredClone(state);
  unsafe.safety.paperTradingAllowed = true;
  assert.throws(() => buildMsiiEnvelopeFromRealtimeState(unsafe, {
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
  }), /paperTradingAllowed/);

  const inconsistent = structuredClone(state);
  inconsistent.pipeline.lastPointTime = "2026-09-04T00:40:00.000Z";
  assert.throws(() => buildMsiiEnvelopeFromRealtimeState(inconsistent, {
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
  }), /last point/);
});
