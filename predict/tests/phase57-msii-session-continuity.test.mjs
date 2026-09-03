import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { processLaneMEnvelope } from "../../tools/phase57_msii_e2e_runtime.mjs";

const DATE = "2026-09-04";
const AT = "2026-09-04T00:35:00.000Z";
const SAFE = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});
const VERSIONS = Object.freeze({
  selectorVersion: "PHASE57_DYNAMIC5M_FROZEN_SELECTOR",
  entryVersion: "PHASE57_FROZEN_ENTRY",
  exitV3Version: "PHASE57_EXIT_V3_FROZEN",
  exitV4Version: "PHASE57_EXIT_V4_FROZEN",
  allocationVersion: "PHASE57_CAPITAL_ALLOCATION_FROZEN",
});

function entry() {
  const cells = ["V1_V3", "V1_V4"];
  return {
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
    contextBars: [],
    selectionLineage: { variant: "V1", opportunityScore: 0.8, v2Score: null },
    strategyLineage: {
      cells,
      strategyIds: STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`))),
    },
  };
}
function capture(at) {
  return {
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt: at,
    symbol: "7203",
    sourceFunctions: ["RssMarket", "RssTickList"],
    market: { bestBid: 100, bestAsk: 100.2, bestBidSize: 10_000, bestAskSize: 10_000 },
    ticks: [],
    phase57Snapshot: {
      direction: 1,
      asOf: at,
      modelId: "phase57-frozen-session-fixture",
      artifactSha256: "a".repeat(64),
      frozen: true,
      futureOutcomeUsed: false,
      thresholdSearchAfterCapture: false,
      entryRetunedAfterCapture: false,
    },
    methodology: {
      phase57DirectionIsFrozenBase: true,
      phase58MayConfirmDeferOrAbstainOnly: true,
      phase58MayReverseDirection: false,
      pointInTimeOnly: true,
      futureOutcomeUsed: false,
      historicalDecisionReconstructionAllowed: false,
      sameCaptureBoundary: true,
    },
    safety: SAFE,
  };
}
function makeEnvelope({ missingCaptureCount = 1, actualStartAt = "2026-09-04T00:00:02.000Z" } = {}) {
  const state = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(state, { at: AT, entries: [entry()], marksBySymbol: { "7203": 100 } });
  return {
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt,
    missingCaptureCount,
    initialCapital: 1_000_000,
    backfillUsed: false,
    phase57State: state,
    pointResult: { at: AT, allocation, exitEvaluation: { at: AT, closed: [] } },
    versions: VERSIONS,
    safety: SAFE,
  };
}

test("Lane M persisted session metadata cannot be rewritten into a better session later", () => {
  const envelope = makeEnvelope({ missingCaptureCount: 1 });
  const rows = [capture("2026-09-04T00:34:59.500Z"), capture("2026-09-04T00:35:00.200Z")];
  const first = processLaneMEnvelope({ envelope, captureRows: rows });
  assert.equal(first.nextState.missingCaptureCount, 1);
  assert.equal(first.nextState.actualStartAt, "2026-09-04T00:00:02.000Z");

  const laterMissingImproved = structuredClone(envelope);
  laterMissingImproved.pointResult.at = "2026-09-04T00:40:00.000Z";
  laterMissingImproved.missingCaptureCount = 0;
  assert.throws(() => processLaneMEnvelope({
    envelope: laterMissingImproved,
    captureRows: [capture("2026-09-04T00:39:59.500Z"), capture("2026-09-04T00:40:00.200Z")],
    priorState: first.nextState,
  }), /cannot decrease/);

  const changedStart = structuredClone(envelope);
  changedStart.pointResult.at = "2026-09-04T00:40:00.000Z";
  changedStart.actualStartAt = "2026-09-04T00:00:00.000Z";
  assert.throws(() => processLaneMEnvelope({
    envelope: changedStart,
    captureRows: [capture("2026-09-04T00:39:59.500Z"), capture("2026-09-04T00:40:00.200Z")],
    priorState: first.nextState,
  }), /actualStartAt changed/);
});
