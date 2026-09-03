import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { processMsiiShadowRuntimePoint } from "../realtime/phase57-msii-shadow-runtime.js";

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

function capture({ capturedAt, symbol = "7203", bid = 100, ask = 100.2 } = {}) {
  return {
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt,
    symbol,
    sourceFunctions: ["RssMarket", "RssTickList"],
    market: { bestBid: bid, bestAsk: ask, bestBidSize: 10_000, bestAskSize: 10_000 },
    ticks: [],
    phase57Snapshot: {
      direction: 1,
      asOf: capturedAt,
      modelId: "phase57-frozen-audit-fixture",
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

function frozenEntry(symbol = "7203") {
  const cells = ["V1_V3", "V1_V4"];
  const strategyIds = STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`)));
  return Object.freeze({
    candidateId: `${DATE}|${AT}|DYNAMIC5M_V1|${symbol}`,
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol,
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

function runtimeBase(overrides = {}) {
  return {
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    versions: VERSIONS,
    marketSizeUnit: "SHARES",
    tickSizeUnit: "SHARES",
    ...overrides,
  };
}

test("Lane Y accepts the first finalized same-session bar and serializes afternoon writers", () => {
  const live = fs.readFileSync(new URL("../../scripts/run_phase57_realtime_live_point.mjs", import.meta.url), "utf8");
  assert.match(live, /if\(bars\.length>=1\)return bars;/);
  assert.doesNotMatch(live, /if\(bars\.length>=6\)return bars;/);
  assert.match(live, /Frozen Entry itself owns the >=6 closed-bar readiness gate/);

  const workflow = fs.readFileSync(new URL("../../.github/workflows/phase57-realtime-live.yml", import.meta.url), "utf8");
  assert.doesNotMatch(workflow, /^  push:/m, "code pushes must not start a second live writer");
  assert.match(workflow, /github\.event\.schedule == '25 3 \* \* 1-5' && 'AFTERNOON'/);
  assert.match(workflow, /inputs\.session_part/);
  assert.match(workflow, /cancel-in-progress: true/);
});

test("Lane M rejects a stale pre-decision reference even when an old symbol snapshot exists", () => {
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(phase57State, {
    at: AT,
    entries: [frozenEntry()],
    marksBySymbol: { "7203": 100 },
  });
  assert.ok(allocation.decisions.some((row) => row.status === "ACCEPTED"));

  const result = processMsiiShadowRuntimePoint(runtimeBase({
    phase57State,
    pointResult: { at: AT, allocation, exitEvaluation: { at: AT, closed: [] } },
    referenceMaxAgeMs: 5_000,
    captureRows: [
      capture({ capturedAt: "2026-09-04T00:34:50.000Z" }),
      capture({ capturedAt: "2026-09-04T00:35:00.200Z" }),
    ],
  }));

  assert.equal(result.complete, false);
  assert.equal(result.status, "BLOCKED_MSII_REFERENCE_CAPTURE_MISSING_OR_STALE");
  assert.deepEqual(result.missingReferenceSymbols, ["7203.T"]);
  assert.equal(result.ledger.length, 0, "stale-reference preflight must not mutate the durable Lane M ledger");
});

test("Lane M never creates an EXIT intent for inventory that never filled in Lane M", () => {
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const strategyId = "V1_V3__MAX_10";
  const result = processMsiiShadowRuntimePoint(runtimeBase({
    phase57State,
    pointResult: {
      at: AT,
      allocation: { at: AT, strategyCount: 28, decisions: [] },
      exitEvaluation: {
        at: AT,
        closed: [{
          strategyId,
          symbol: "7203",
          signalDirection: 1,
          quantity: 500,
          exitReferencePrice: 101,
          lastMarkPrice: 101,
        }],
      },
    },
    captureRows: [
      capture({ capturedAt: AT }),
      capture({ capturedAt: "2026-09-04T00:35:00.200Z", bid: 101, ask: 101.2 }),
    ],
  }));

  assert.equal(result.complete, true);
  assert.equal(result.exitIntentCount, 0);
  assert.equal(result.closedTradesCommitted, 0);
  assert.equal(result.score.closedTrades, 0);
});
