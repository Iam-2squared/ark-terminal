import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  PHASE57_MSII_E2E_SAFETY,
  processLaneMEnvelope,
  validateCaptureBundle,
  validateLaneMEnvelope,
} from "../../tools/phase57_msii_e2e_runtime.mjs";

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

function capture(capturedAt, { bid = 100, ask = 100.2 } = {}) {
  return {
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt,
    symbol: "7203",
    sourceFunctions: ["RssMarket", "RssTickList"],
    market: { bestBid: bid, bestAsk: ask, bestBidSize: 10_000, bestAskSize: 10_000 },
    ticks: [],
    phase57Snapshot: {
      direction: 1,
      asOf: capturedAt,
      modelId: "phase57-frozen-e2e-fixture",
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

function envelope() {
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(phase57State, {
    at: AT,
    entries: [frozenEntry()],
    marksBySymbol: { "7203": 100 },
  });
  const laneYDecisions = allocation.decisions.filter((row) => row.status === "ACCEPTED").map((row) => ({
    strategyId: row.strategyId,
    symbol: row.symbol,
    decisionAt: AT,
    intentKind: "ENTRY",
    referencePrice: 100,
  }));
  return {
    schemaVersion: 1,
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    backfillUsed: false,
    phase57State,
    pointResult: { at: AT, allocation, exitEvaluation: { at: AT, closed: [] } },
    versions: VERSIONS,
    laneYDecisions,
    safety: SAFE,
  };
}

test("Lane M E2E coordinator processes one causal envelope and persists replay guards", () => {
  const input = envelope();
  const captures = [
    capture("2026-09-04T00:34:59.500Z", { bid: 99.9, ask: 100.1 }),
    capture("2026-09-04T00:35:00.200Z", { bid: 100, ask: 100.2 }),
  ];
  const checked = validateLaneMEnvelope(input);
  assert.deepEqual(checked.requiredSymbols, ["7203.T"]);
  const bundle = validateCaptureBundle(captures, { decisionAt: AT, requiredSymbols: checked.requiredSymbols, referenceMaxAgeMs: 5_000 });
  assert.equal(bundle.hasPostDecision, true);

  const first = processLaneMEnvelope({ envelope: input, captureRows: captures });
  assert.equal(first.result.complete, true);
  assert.equal(first.result.entryIntentCount, 14);
  assert.equal(first.result.score.statusCounts.FILLED, 14);
  assert.equal(first.result.pair.pairCount, 14);
  assert.equal(first.nextState.lastDecisionAt, AT);
  assert.equal(first.nextState.processedEvidenceHashes.length, 1);
  assert.ok(first.nextState.ledger.length > 0);
  for (const key of ["executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"]) {
    assert.equal(PHASE57_MSII_E2E_SAFETY[key], false);
  }
  assert.throws(() => processLaneMEnvelope({ envelope: input, captureRows: captures, priorState: first.nextState }), /strictly forward/);
});

test("Lane M E2E coordinator fails closed before core runtime on stale or unsafe evidence", () => {
  const input = envelope();
  assert.throws(() => validateCaptureBundle([
    capture("2026-09-04T00:34:50.000Z"),
    capture("2026-09-04T00:35:00.200Z"),
  ], { decisionAt: AT, requiredSymbols: ["7203.T"], referenceMaxAgeMs: 5_000 }), /stale/);

  const unsafe = structuredClone(input);
  unsafe.safety.liveTradingAllowed = true;
  assert.throws(() => validateLaneMEnvelope(unsafe), /liveTradingAllowed/);

  const backfilled = structuredClone(input);
  backfilled.backfillUsed = true;
  assert.throws(() => validateLaneMEnvelope(backfilled), /backfillUsed/);
});
