import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import {
  ALLOCATION_PROFILES,
  MATRIX_CELLS,
  STRATEGY_IDS,
  createRealtimeSessionState,
} from "../realtime/phase57-stateful-contract.js";
import {
  PHASE57_MSII_FILL_STATUS,
  PHASE57_MSII_ORDER_STYLE,
  PHASE57_MSII_SESSION_QUALITY,
  PHASE57_MSII_SHADOW_SAFETY,
  appendMsiiShadowLedgerEvent,
  buildEntryShadowOrderIntentsFromPhase57,
  buildExecutionAwareClosedTrade,
  classifyMsiiSession,
  commitExecutionAwareClosedTrade,
  commitNormalizedMarketEvent,
  commitShadowFill,
  commitShadowOrderIntent,
  compareLaneYWithMsii,
  createMsiiShadowExecutionState,
  createShadowOrderIntent,
  evaluateShadowFill,
  normalizeMarketSpeedReadOnlyEvent,
  scoreMsiiShadowExecutionLedger,
  verifyMsiiShadowLedger,
} from "../realtime/phase57-msii-shadow-execution.js";

const DATE = "2026-09-03";
const DECISION_AT = "2026-09-03T00:35:00.000Z";
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
const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);
const VERSIONS = Object.freeze({
  selectorVersion: "PHASE57_DYNAMIC5M_FROZEN_SELECTOR",
  entryVersion: "PHASE57_FROZEN_ENTRY",
  exitVersion: "PHASE57_EXIT_V3_FROZEN",
  allocationVersion: "PHASE57_CAPITAL_ALLOCATION_FROZEN",
});

function assertShadowOnly(value) {
  for (const key of FALSE_KEYS) assert.equal(value.safety?.[key] ?? value[key], false, key);
  if ("futureOutcomeUsed" in value) assert.equal(value.futureOutcomeUsed, false);
  if ("transmitted" in value) assert.equal(value.transmitted, false);
  if ("executable" in value) assert.equal(value.executable, false);
}

function capture({
  capturedAt = DECISION_AT,
  symbol = "7203",
  bid = 100,
  ask = 100.2,
  bidSize = 500,
  askSize = 500,
  ticks = [],
  direction = 1,
  phase57AsOf = capturedAt,
  sourceFunctions = ["RssMarket", "RssTickList"],
} = {}) {
  return {
    schemaVersion: 2,
    phase: "58.p9.sync-capture",
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    capturedAt,
    symbol,
    tickOrder: "DESC",
    sourceFunctions,
    market: { bestBid: bid, bestAsk: ask, bestBidSize: bidSize, bestAskSize: askSize },
    orderBook: null,
    ticks,
    phase57Snapshot: {
      direction,
      asOf: phase57AsOf,
      modelId: "phase57-frozen-fixture",
      artifactSha256: "a".repeat(64),
      frozen: true,
      futureOutcomeUsed: false,
      thresholdSearchAfterCapture: false,
      entryRetunedAfterCapture: false,
    },
    methodology: {
      phase57DirectionIsFrozenBase: true,
      phase58MayConfirmDeferOrAbstainOnly: true,
      pointInTimeOnly: true,
      sameCaptureBoundary: true,
      futureOutcomeUsed: false,
      historicalDecisionReconstructionAllowed: false,
      phase58MayReverseDirection: false,
    },
    safety: SAFE,
  };
}

function marketEvent(options = {}, units = { marketSizeUnit: "SHARES", tickSizeUnit: "SHARES" }) {
  return normalizeMarketSpeedReadOnlyEvent(capture(options), units);
}

function intent({
  strategyId = "V1_V3__MAX_10",
  symbol = "7203",
  side = "BUY",
  intentKind = "ENTRY",
  decisionAt = DECISION_AT,
  decisionSequence = 1,
  requestedQuantity = 500,
  referencePrice = 100.1,
  referenceEvent = marketEvent({ capturedAt: decisionAt, symbol }),
  orderStyleResearchLabel = PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
  ttlMs = 5_000,
  decisionLatencyMs = 100,
  versions = VERSIONS,
} = {}) {
  return createShadowOrderIntent({
    strategyId,
    symbol,
    side,
    intentKind,
    decisionAt,
    decisionSequence,
    requestedQuantity,
    referencePrice,
    referenceEvent,
    orderStyleResearchLabel,
    ttlMs,
    decisionLatencyMs,
    selectorVersion: versions.selectorVersion,
    entryVersion: versions.entryVersion,
    exitVersion: versions.exitVersion,
    allocationVersion: versions.allocationVersion,
    futureOutcomeUsed: false,
  });
}

function frozenEntry(variant, symbol, price = 100) {
  const cells = variant === "V1" ? ["V1_V3", "V1_V4"] : ["V2_V3", "V2_V4"];
  const strategyIds = STRATEGY_IDS.filter((id) => cells.some((cell) => id.startsWith(`${cell}__`)));
  return Object.freeze({
    candidateId: `${DATE}|${DECISION_AT}|DYNAMIC5M_${variant}|${symbol}`,
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol,
    sessionDate: DATE,
    entryTimestamp: DECISION_AT,
    signalDirection: 1,
    entryPrice: price,
    confidence: 0.8,
    probability: 0.75,
    sector: "TEST",
    selectionLineage: Object.freeze({
      variant,
      opportunityScore: 0.8,
      v2Score: variant === "V2" ? 0.82 : null,
    }),
    strategyLineage: Object.freeze({ cells: Object.freeze(cells), strategyIds: Object.freeze(strategyIds) }),
  });
}

test("normalizes only prospective MarketSpeed II READ ONLY evidence and fails closed on unknown size units", () => {
  const raw = capture({
    ticks: [{ timestamp: "09:34:59.900", executionPrice: 100.1, volume: 200 }],
  });
  const event = normalizeMarketSpeedReadOnlyEvent(raw, { marketSizeUnit: "SHARES", tickSizeUnit: "SHARES" });
  const replay = normalizeMarketSpeedReadOnlyEvent(raw, { marketSizeUnit: "SHARES", tickSizeUnit: "SHARES" });
  assert.equal(event.symbol, "7203.T");
  assert.equal(event.bestBid, 100);
  assert.equal(event.bestAsk, 100.2);
  assert.ok(Math.abs(event.referenceSpread - 0.2) < 1e-12);
  assert.equal(event.ticks[0].timestamp, "2026-09-03T00:34:59.900Z");
  assert.equal(event.quoteSourceReady, true);
  assert.equal(event.tickSourceReady, true);
  assert.equal(event.eventId, replay.eventId);
  assert.equal(event.normalizedEventSha256, replay.normalizedEventSha256);
  assert.ok(Object.isFrozen(event));
  assert.ok(Object.isFrozen(event.ticks));
  assertShadowOnly(event);

  const unitsUnknown = normalizeMarketSpeedReadOnlyEvent(raw);
  assert.equal(unitsUnknown.quoteSourceReady, false);
  assert.equal(unitsUnknown.tickSourceReady, false);
  assert.ok(unitsUnknown.blockers.includes("MARKET_SIZE_UNIT_NOT_DECLARED_AS_SHARES"));
  assert.ok(unitsUnknown.blockers.includes("TICK_SIZE_UNIT_NOT_DECLARED_AS_SHARES"));

  assert.throws(
    () => marketEvent({ sourceFunctions: ["RssMarket", "RssStockOrder"] }),
    /forbidden RSS order function/,
  );
  assert.throws(
    () => marketEvent({ sourceFunctions: ["RssMarket", "rssfopmultiopenorder_v"] }),
    /forbidden RSS order function/,
  );
  assert.throws(
    () => marketEvent({ ticks: [{ timestamp: "2026-09-03T00:35:01.000Z", price: 100, size: 100 }] }),
    /future relative to capturedAt/,
  );
  assert.throws(() => marketEvent({ bid: 101, ask: 100 }), /crossed MarketSpeed quote/);
  assert.throws(() => marketEvent({ direction: 2 }), /direction must be -1, 0, or 1/);
  assert.throws(
    () => normalizeMarketSpeedReadOnlyEvent({ ...raw, safety: { ...SAFE, brokerWriteAllowed: !SAFE.brokerWriteAllowed } }),
    /brokerWriteAllowed must remain false/,
  );
});

test("creates immutable 28-way ShadowOrderIntent with explicit frozen lineage and no execution capability", () => {
  const created = intent();
  assert.equal(created.strategyId, "V1_V3__MAX_10");
  assert.equal(created.matrixCell, "V1_V3");
  assert.equal(created.allocationProfile, "MAX_10");
  assert.equal(created.requestedNotional, 50_050);
  assert.equal(created.referenceBid, 100);
  assert.equal(created.referenceAsk, 100.2);
  assert.equal(created.sourceReadyAtDecision, true);
  assert.ok(/^[a-f0-9]{64}$/.test(created.intentSha256));
  assert.ok(Object.isFrozen(created));
  assertShadowOnly(created);

  assert.throws(() => intent({ requestedQuantity: 150 }), /100-share lot multiple/);
  assert.throws(() => intent({ strategyId: "V9_V9__MAX_10" }), /outside frozen 28-way/);
  assert.throws(() => intent({ versions: { ...VERSIONS, exitVersion: "" } }), /exitVersion is required/);
  assert.throws(
    () => intent({
      decisionAt: DECISION_AT,
      referenceEvent: marketEvent({ capturedAt: "2026-09-03T00:35:00.001Z" }),
    }),
    /future MarketSpeed snapshot/,
  );
});

test("marketable fill uses the first ready post-decision quote, caps quantity at observed size, and ignores future rows", () => {
  const orderIntent = intent();
  const notReady = marketEvent(
    { capturedAt: "2026-09-03T00:35:00.150Z", ask: 100.25, askSize: 900 },
    { marketSizeUnit: null, tickSizeUnit: "SHARES" },
  );
  const firstReady = marketEvent({ capturedAt: "2026-09-03T00:35:00.200Z", ask: 100.3, askSize: 300 });
  const future = marketEvent({ capturedAt: "2026-09-03T00:35:04.000Z", bid: 98.8, ask: 99, askSize: 5_000 });
  const fill = evaluateShadowFill(orderIntent, [future, firstReady, notReady], { asOf: "2026-09-03T00:35:00.300Z" });
  const samePrefix = evaluateShadowFill(orderIntent, [firstReady, notReady], { asOf: "2026-09-03T00:35:00.300Z" });
  assert.equal(fill.status, PHASE57_MSII_FILL_STATUS.PARTIAL);
  assert.equal(fill.filledQuantity, 300);
  assert.equal(fill.remainingQuantity, 200);
  assert.equal(fill.fillPrice, 100.3);
  assert.equal(fill.firstFillAt, "2026-09-03T00:35:00.200Z");
  assert.equal(fill.decisionToFirstFillLatencyMs, 200);
  assert.equal(fill.fillSha256, samePrefix.fillSha256);
  assert.equal(fill.evidence.length, 1);
  assertShadowOnly(fill);

  const unavailable = evaluateShadowFill(orderIntent, [notReady], { asOf: "2026-09-03T00:35:00.300Z" });
  assert.equal(unavailable.status, PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY);
  assert.equal(unavailable.filledQuantity, 0);
  const noObservation = evaluateShadowFill(orderIntent, [], { asOf: "2026-09-03T00:35:00.300Z" });
  assert.equal(noObservation.status, PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY);
});

test("passive fill uses only observed post-decision tick volume and distinguishes NO_FILL from EXPIRED", () => {
  const orderIntent = intent({
    requestedQuantity: 500,
    orderStyleResearchLabel: PHASE57_MSII_ORDER_STYLE.PASSIVE_REFERENCE,
  });
  const first = marketEvent({
    capturedAt: "2026-09-03T00:35:00.400Z",
    ticks: [
      { timestamp: "2026-09-03T00:35:00.150Z", price: 100.1, size: 100 },
      { timestamp: "2026-09-03T00:35:00.250Z", price: 100.0, size: 200 },
    ],
  });
  const rollingDuplicate = marketEvent({
    capturedAt: "2026-09-03T00:35:00.600Z",
    ticks: [
      { timestamp: "2026-09-03T00:35:00.150Z", price: 100.1, size: 100 },
      { timestamp: "2026-09-03T00:35:00.250Z", price: 100.0, size: 200 },
    ],
  });
  const fill = evaluateShadowFill(orderIntent, [first, rollingDuplicate], { asOf: "2026-09-03T00:35:00.700Z" });
  assert.equal(fill.status, PHASE57_MSII_FILL_STATUS.PARTIAL);
  assert.equal(fill.filledQuantity, 300);
  assert.equal(fill.fillPrice, (100.1 * 100 + 100 * 200) / 300);
  assert.equal(fill.evidence.length, 2, "rolling RssTickList rows must not double-count identical evidence");

  const noCrossEvent = marketEvent({
    capturedAt: "2026-09-03T00:35:00.400Z",
    ticks: [{ timestamp: "2026-09-03T00:35:00.200Z", price: 100.5, size: 1_000 }],
  });
  const noFill = evaluateShadowFill(orderIntent, [noCrossEvent], { asOf: "2026-09-03T00:35:01.000Z" });
  const expired = evaluateShadowFill(orderIntent, [noCrossEvent], { asOf: "2026-09-03T00:35:05.000Z" });
  assert.equal(noFill.status, PHASE57_MSII_FILL_STATUS.NO_FILL);
  assert.equal(expired.status, PHASE57_MSII_FILL_STATUS.EXPIRED);
  assert.equal(noFill.fillPrice, null);
  assert.equal(expired.fillPrice, null);
});

test("session freshness never upgrades late, gapped, or backfilled capture to FULL_FRESH_MSII", () => {
  const predeclaredStartAt = "2026-09-03T00:00:00.000Z";
  assert.equal(classifyMsiiSession({ predeclaredStartAt, actualStartAt: predeclaredStartAt }), PHASE57_MSII_SESSION_QUALITY.FULL_FRESH_MSII);
  assert.equal(classifyMsiiSession({ predeclaredStartAt, actualStartAt: "2026-09-03T00:00:01.000Z" }), PHASE57_MSII_SESSION_QUALITY.PARTIAL_INCOMPLETE_MSII);
  assert.equal(classifyMsiiSession({ predeclaredStartAt, actualStartAt: predeclaredStartAt, missingCaptureCount: 1 }), PHASE57_MSII_SESSION_QUALITY.PARTIAL_INCOMPLETE_MSII);
  assert.equal(classifyMsiiSession({ predeclaredStartAt, actualStartAt: predeclaredStartAt, backfillUsed: true }), PHASE57_MSII_SESSION_QUALITY.PARTIAL_INCOMPLETE_MSII);
  assert.equal(classifyMsiiSession({ predeclaredStartAt, actualStartAt: null }), PHASE57_MSII_SESSION_QUALITY.SOURCE_NOT_READY);
});

test("Shadow ledger is append-only, hash-chained, idempotent for identical input, and fail-closed on conflicts", () => {
  const state = createMsiiShadowExecutionState({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-03T00:00:00.000Z",
    actualStartAt: "2026-09-03T00:00:00.000Z",
  });
  const reference = marketEvent();
  const orderIntent = intent({ requestedQuantity: 300, referenceEvent: reference });
  const observation = marketEvent({ capturedAt: "2026-09-03T00:35:00.200Z", askSize: 300 });
  const fill = evaluateShadowFill(orderIntent, [observation], { asOf: "2026-09-03T00:35:00.300Z" });
  const sourceCommit = commitNormalizedMarketEvent(state, reference);
  assert.equal(commitNormalizedMarketEvent(state, reference), sourceCommit);
  const firstCommit = commitShadowOrderIntent(state, orderIntent);
  const repeatedCommit = commitShadowOrderIntent(state, orderIntent);
  assert.equal(firstCommit, repeatedCommit);
  assert.equal(state.ledger.length, 2);
  commitNormalizedMarketEvent(state, observation);
  commitShadowFill(state, fill);
  const verified = verifyMsiiShadowLedger(state.ledger, { sessionDate: DATE });
  assert.equal(verified.valid, true);
  assert.equal(verified.eventCount, 4);
  assert.equal(verified.headHash, state.ledgerHeadHash);
  assertShadowOnly(state);

  const cloned = structuredClone(state.ledger);
  cloned.find((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED").intent.requestedQuantity += 100;
  assert.throws(() => verifyMsiiShadowLedger(cloned, { sessionDate: DATE }), /eventHash mismatch|eventFingerprint mismatch/);

  const conflictState = createMsiiShadowExecutionState({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-03T00:00:00.000Z",
    actualStartAt: "2026-09-03T00:00:00.000Z",
  });
  const first = appendMsiiShadowLedgerEvent(conflictState, {
    eventId: "TEST|1",
    eventType: "TEST",
    eventAt: DECISION_AT,
    value: 1,
  });
  assert.equal(appendMsiiShadowLedgerEvent(conflictState, {
    eventId: "TEST|1",
    eventType: "TEST",
    eventAt: DECISION_AT,
    value: 1,
  }), first);
  assert.throws(() => appendMsiiShadowLedgerEvent(conflictState, {
    eventId: "TEST|1",
    eventType: "TEST",
    eventAt: DECISION_AT,
    value: 2,
  }), /EVENT_ID_CONFLICT/);
  assert.throws(() => appendMsiiShadowLedgerEvent(conflictState, {
    eventId: "TEST|BACKWARD",
    eventType: "TEST",
    eventAt: "2026-09-03T00:34:59.999Z",
  }), /cannot move backward/);

  const marketConflictState = createMsiiShadowExecutionState({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-03T00:00:00.000Z",
    actualStartAt: "2026-09-03T00:00:00.000Z",
  });
  commitNormalizedMarketEvent(marketConflictState, reference);
  commitNormalizedMarketEvent(marketConflictState, marketEvent({ symbol: "8306" }));
  assert.throws(() => commitNormalizedMarketEvent(
    marketConflictState,
    marketEvent({ ask: 100.3 }),
  ), /EVENT_ID_CONFLICT/);
  assert.throws(() => commitNormalizedMarketEvent(
    marketConflictState,
    marketEvent({ symbol: "9984", capturedAt: "2026-09-03T00:34:59.999Z" }),
  ), /cannot move backward/);
});

test("ledger-read-only scoring reports observed execution metrics for all 28 identities", () => {
  const state = createMsiiShadowExecutionState({
    sessionDate: DATE,
    predeclaredStartAt: "2026-09-03T00:00:00.000Z",
    actualStartAt: "2026-09-03T00:00:00.000Z",
    initialCapital: 1_000_000,
  });
  const entryReference = marketEvent();
  const entryIntent = intent({ requestedQuantity: 300, decisionSequence: 10, referenceEvent: entryReference });
  const entryObservation = marketEvent({ capturedAt: "2026-09-03T00:35:00.200Z", ask: 100.2, askSize: 300 });
  const entryFill = evaluateShadowFill(entryIntent, [entryObservation], { asOf: "2026-09-03T00:35:00.300Z" });

  const exitAt = "2026-09-03T00:40:00.000Z";
  const exitReference = marketEvent({ capturedAt: exitAt, bid: 101, ask: 101.2, bidSize: 300, askSize: 300 });
  const exitIntent = intent({
    side: "SELL",
    intentKind: "EXIT",
    decisionAt: exitAt,
    decisionSequence: 11,
    requestedQuantity: 300,
    referencePrice: 101.1,
    referenceEvent: exitReference,
  });
  const exitObservation = marketEvent({ capturedAt: "2026-09-03T00:40:00.200Z", bid: 101, ask: 101.2, bidSize: 300, askSize: 300 });
  const exitFill = evaluateShadowFill(exitIntent, [exitObservation], { asOf: "2026-09-03T00:40:00.300Z" });
  const trade = buildExecutionAwareClosedTrade({ entryIntent, entryFill, exitIntent, exitFill, transactionCostJpy: 10 });

  commitNormalizedMarketEvent(state, entryReference);
  commitShadowOrderIntent(state, entryIntent);
  commitNormalizedMarketEvent(state, entryObservation);
  commitShadowFill(state, entryFill);
  commitNormalizedMarketEvent(state, exitReference);
  commitShadowOrderIntent(state, exitIntent);
  commitNormalizedMarketEvent(state, exitObservation);
  commitShadowFill(state, exitFill);
  commitExecutionAwareClosedTrade(state, trade);

  const score = scoreMsiiShadowExecutionLedger(state.ledger, { sessionDate: DATE });
  assert.equal(score.strategyCount, 28);
  assert.deepEqual(score.strategies.map((row) => row.strategyId), STRATEGY_IDS);
  assert.equal(score.decisionCount, 2);
  assert.equal(score.statusCounts.FILLED, 2);
  assert.equal(score.closedTrades, 1);
  assert.ok(Math.abs(score.netPnlJpy - 230) < 1e-9);
  assert.equal(score.averageDecisionToFillLatencyMs, 200);
  const strategy = score.strategies.find((row) => row.strategyId === entryIntent.strategyId);
  assert.equal(strategy.closedTrades, 1);
  assert.equal(strategy.wins, 1);
  assert.equal(strategy.openPositions, 0);
  assert.ok(Math.abs(strategy.realizedPnl - 230) < 1e-9);
  assert.equal(score.postCloseDecisionRecomputationAllowed, false);
  assertShadowOnly(score);

  const paired = compareLaneYWithMsii({
    msiiLedger: state.ledger,
    laneYDecisions: [
      { strategyId: entryIntent.strategyId, symbol: "7203", decisionAt: DECISION_AT, intentKind: "ENTRY", referencePrice: 100.1 },
      { strategyId: entryIntent.strategyId, symbol: "7203", decisionAt: "2026-09-03T00:36:00.000Z", intentKind: "ENTRY", referencePrice: 100.1 },
    ],
  });
  assert.equal(paired.exactIdentityTimestampJoin, true);
  assert.equal(paired.pairCount, 1);
  assert.equal(paired.unmatchedLaneYCount, 1);
  assert.equal(paired.unmatchedLaneMCount, 1, "the EXIT intent has no Lane Y pair in this fixture");
  assert.equal(paired.pairs[0].laneMFillStatus, PHASE57_MSII_FILL_STATUS.FILLED);
  assertShadowOnly(paired);
});

test("adapts the existing Frozen Phase57 allocation result into exactly the same 28 strategy identities", () => {
  assert.equal(MATRIX_CELLS.length, 4);
  assert.equal(ALLOCATION_PROFILES.length, 7);
  assert.equal(STRATEGY_IDS.length, 28);
  const phase57State = createRealtimeSessionState({ sessionDate: DATE });
  const allocation = allocateRealtimeFrozenEntries(phase57State, {
    at: DECISION_AT,
    entries: [frozenEntry("V1", "7203"), frozenEntry("V2", "8306")],
    marksBySymbol: { "7203": 100, "8306": 100 },
  });
  assert.equal(allocation.decisions.filter((row) => row.status === "ACCEPTED").length, 28);
  const laneYLedgerLength = phase57State.ledger.length;
  const marketEventsBySymbol = {
    "7203.T": marketEvent({ symbol: "7203", capturedAt: DECISION_AT }),
    "8306.T": marketEvent({ symbol: "8306", capturedAt: DECISION_AT, bid: 200, ask: 200.2 }),
  };
  const intents = buildEntryShadowOrderIntentsFromPhase57({
    phase57State,
    allocationResult: allocation,
    marketEventsBySymbol,
    decisionSequenceStart: 1_000,
    orderStyleResearchLabel: PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
    ttlMs: 5_000,
    decisionLatencyMs: 100,
    versions: {
      selectorVersion: "PHASE57_DYNAMIC5M_FROZEN_SELECTOR",
      entryVersion: "PHASE57_FROZEN_ENTRY",
      exitV3Version: "PHASE57_EXIT_V3_FROZEN",
      exitV4Version: "PHASE57_EXIT_V4_FROZEN",
      allocationVersion: "PHASE57_CAPITAL_ALLOCATION_FROZEN",
    },
  });
  assert.equal(intents.length, 28);
  assert.deepEqual(new Set(intents.map((row) => row.strategyId)), new Set(STRATEGY_IDS));
  assert.equal(intents.filter((row) => row.exitVersion === "PHASE57_EXIT_V3_FROZEN").length, 14);
  assert.equal(intents.filter((row) => row.exitVersion === "PHASE57_EXIT_V4_FROZEN").length, 14);
  assert.equal(phase57State.ledger.length, laneYLedgerLength, "Lane M adapter must not mutate the existing Lane Y ledger");
  for (const row of intents) assertShadowOnly(row);

  assert.throws(() => buildEntryShadowOrderIntentsFromPhase57({
    phase57State,
    allocationResult: allocation,
    marketEventsBySymbol,
    orderStyleResearchLabel: PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
    ttlMs: 5_000,
    decisionLatencyMs: 100,
    versions: {
      selectorVersion: "PHASE57_DYNAMIC5M_FROZEN_SELECTOR",
      entryVersion: "PHASE57_FROZEN_ENTRY",
      exitV3Version: "PHASE57_EXIT_V3_FROZEN",
      allocationVersion: "PHASE57_CAPITAL_ALLOCATION_FROZEN",
    },
  }), /exitVersion is required/);
});

test("Lane M safety contract keeps all eight kill-switches false", () => {
  assertShadowOnly({ safety: PHASE57_MSII_SHADOW_SAFETY, futureOutcomeUsed: false, transmitted: false });
});
