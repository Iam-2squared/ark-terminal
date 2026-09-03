import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  PHASE57_MSII_RUNTIME_VERSION,
  buildExitShadowOrderIntentsFromPhase57,
  processMsiiShadowRuntimePoint,
} from "../realtime/phase57-msii-shadow-runtime.js";

const DATE = "2026-09-04";
const ENTRY_AT = "2026-09-04T00:35:00.000Z";
const EXIT_AT = "2026-09-04T00:40:00.000Z";
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

function capture({ capturedAt, symbol, bid = 100, ask = 100.2, bidSize = 100_000, askSize = 100_000, direction = 1, ticks = [] } = {}) {
  return {
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt,
    symbol,
    sourceFunctions: ["RssMarket", "RssTickList"],
    market: { bestBid: bid, bestAsk: ask, bestBidSize: bidSize, bestAskSize: askSize },
    ticks,
    phase57Snapshot: {
      direction,
      asOf: capturedAt,
      modelId: "phase57-frozen-runtime-fixture",
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

function frozenEntry(variant, symbol, price = 100) {
  const cells = variant === "V1" ? ["V1_V3", "V1_V4"] : ["V2_V3", "V2_V4"];
  const strategyIds = STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`)));
  return Object.freeze({
    candidateId: `${DATE}|${ENTRY_AT}|DYNAMIC5M_${variant}|${symbol}`,
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol,
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    signalDirection: 1,
    entryPrice: price,
    confidence: 0.8,
    probability: 0.75,
    sector: "TEST",
    contextBars: Object.freeze([]),
    selectionLineage: Object.freeze({ variant, opportunityScore: 0.8, v2Score: variant === "V2" ? 0.82 : null }),
    strategyLineage: Object.freeze({ cells: Object.freeze(cells), strategyIds: Object.freeze(strategyIds) }),
  });
}

function safetyFalse(value) {
  for (const key of [
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
    "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
  ]) assert.equal(value.safety[key], false, key);
}

test("Lane M runtime commits a full 28-way prospective Entry point and pairs it to Lane Y", () => {
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(phase57State, {
    at: ENTRY_AT,
    entries: [frozenEntry("V1", "7203"), frozenEntry("V2", "8306")],
    marksBySymbol: { "7203": 100, "8306": 100 },
  });
  assert.equal(allocation.strategyCount, 28);
  assert.equal(allocation.decisions.filter((row) => row.status === "ACCEPTED").length, 28);
  const laneYDecisions = allocation.decisions.filter((row) => row.status === "ACCEPTED").map((row) => ({
    strategyId: row.strategyId,
    symbol: row.symbol,
    decisionAt: ENTRY_AT,
    intentKind: "ENTRY",
    referencePrice: 100,
  }));
  const captures = [
    capture({ capturedAt: ENTRY_AT, symbol: "7203", bid: 99.9, ask: 100.1 }),
    capture({ capturedAt: ENTRY_AT, symbol: "8306", bid: 99.9, ask: 100.1 }),
    capture({ capturedAt: "2026-09-04T00:35:00.200Z", symbol: "7203", bid: 100, ask: 100.2 }),
    capture({ capturedAt: "2026-09-04T00:35:00.200Z", symbol: "8306", bid: 100, ask: 100.2 }),
  ];

  const result = processMsiiShadowRuntimePoint({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    phase57State,
    pointResult: { at: ENTRY_AT, allocation, exitEvaluation: { at: ENTRY_AT, closed: [] } },
    captureRows: captures,
    versions: VERSIONS,
    marketSizeUnit: "SHARES",
    tickSizeUnit: "SHARES",
    laneYDecisions,
  });

  assert.equal(result.complete, true);
  assert.equal(result.version, PHASE57_MSII_RUNTIME_VERSION);
  assert.equal(result.entryIntentCount, 28);
  assert.equal(result.exitIntentCount, 0);
  assert.equal(result.score.intentCount, 28);
  assert.equal(result.score.statusCounts.FILLED, 28);
  assert.equal(result.pair.pairCount, 28);
  assert.equal(result.pair.unmatchedLaneYCount, 0);
  assert.equal(result.pair.unmatchedLaneMCount, 0);
  safetyFalse(result);
  assert.equal(phase57State.ledger.some((row) => String(row.type).includes("MSII")), false, "Lane M must not mutate Lane Y ledger");
  assert.throws(() => processMsiiShadowRuntimePoint({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    phase57State,
    pointResult: { at: ENTRY_AT, allocation, exitEvaluation: { at: ENTRY_AT, closed: [] } },
    captureRows: captures,
    versions: VERSIONS,
    marketSizeUnit: "UNKNOWN",
    tickSizeUnit: "SHARES",
  }), /explicit verified/);
});

test("Lane M runtime converts frozen EXIT into a causal fill and execution-aware closed trade", () => {
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(phase57State, {
    at: ENTRY_AT,
    entries: [frozenEntry("V1", "7203"), frozenEntry("V2", "8306")],
    marksBySymbol: { "7203": 100, "8306": 100 },
  });
  const first = processMsiiShadowRuntimePoint({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    phase57State,
    pointResult: { at: ENTRY_AT, allocation, exitEvaluation: { at: ENTRY_AT, closed: [] } },
    captureRows: [
      capture({ capturedAt: ENTRY_AT, symbol: "7203" }),
      capture({ capturedAt: ENTRY_AT, symbol: "8306" }),
      capture({ capturedAt: "2026-09-04T00:35:00.200Z", symbol: "7203" }),
      capture({ capturedAt: "2026-09-04T00:35:00.200Z", symbol: "8306" }),
    ],
    versions: VERSIONS,
    marketSizeUnit: "SHARES",
    tickSizeUnit: "SHARES",
  });
  const strategyId = allocation.decisions.find((row) => row.status === "ACCEPTED" && String(row.symbol).startsWith("7203")).strategyId;
  const position = phase57State.strategies[strategyId].positions["7203"] ?? phase57State.strategies[strategyId].positions["7203.T"];
  const closed = {
    ...position,
    strategyId,
    symbol: "7203",
    exitReferencePrice: 101,
    lastMarkPrice: 101,
  };
  const exitAllocation = Object.freeze({ at: EXIT_AT, strategyCount: 28, decisions: Object.freeze([]) });
  const second = processMsiiShadowRuntimePoint({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-04T00:00:00.000Z",
    actualStartAt: "2026-09-04T00:00:00.000Z",
    priorLedger: first.ledger,
    phase57State,
    pointResult: { at: EXIT_AT, allocation: exitAllocation, exitEvaluation: { at: EXIT_AT, closed: [closed] } },
    captureRows: [
      capture({ capturedAt: EXIT_AT, symbol: "7203", bid: 101, ask: 101.2 }),
      capture({ capturedAt: "2026-09-04T00:40:00.200Z", symbol: "7203", bid: 101.1, ask: 101.3 }),
    ],
    versions: VERSIONS,
    marketSizeUnit: "SHARES",
    tickSizeUnit: "SHARES",
    transactionCostJpy: 0,
  });

  assert.equal(second.complete, true);
  assert.equal(second.entryIntentCount, 0);
  assert.equal(second.exitIntentCount, 1);
  assert.equal(second.closedTradesCommitted, 1);
  assert.equal(second.score.closedTrades, 1);
  const exitIntent = second.ledger.find((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED" && row.intent.intentKind === "EXIT").intent;
  assert.equal(exitIntent.side, "SELL");
  assert.equal(exitIntent.strategyId, strategyId);
  safetyFalse(second);
});

test("EXIT adapter fails closed without a same-or-earlier MarketSpeed reference event", () => {
  assert.throws(() => buildExitShadowOrderIntentsFromPhase57({
    exitEvaluation: { at: EXIT_AT, closed: [{ strategyId: "V1_V3__MAX_10", symbol: "7203", signalDirection: 1, quantity: 100, exitReferencePrice: 101 }] },
    marketEventsBySymbol: new Map(),
    ttlMs: 5_000,
    decisionLatencyMs: 100,
    versions: VERSIONS,
  }), /source snapshot missing/);
});
