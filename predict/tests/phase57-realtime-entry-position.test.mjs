import assert from "node:assert/strict";
import test from "node:test";
import { buildProspectiveP21FeatureFeed } from "../daytrade/phase57-p21-prospective-feature-feed.js";
import { buildProspectiveP21FrozenDecision } from "../daytrade/phase57-p21-prospective-frozen-base.js";
import { createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  PHASE57_REALTIME_ENTRY_SAFETY,
  POSITION_STATUS,
  commitShadowPositionEntry,
  evaluateRealtimeFrozenEntries,
  positionStateFor,
  scoreRealtimeFrozenEntry,
} from "../realtime/phase57-realtime-entry-position.js";

const SESSION_DATE = "2026-09-03";
const AT = "2026-09-03T00:30:00.000Z";

function bars(symbolIndex = 0) {
  return Array.from({ length: 6 }, (_, index) => {
    const price = 1000 + symbolIndex + index;
    return {
      timestamp: new Date(Date.parse("2026-09-03T00:00:00.000Z") + index * 5 * 60_000).toISOString(),
      open: price,
      high: price + 2,
      low: price - 1,
      close: price + 1,
      volume: 10_000 + index * 100,
    };
  });
}

function historicalRows() {
  const start = Date.parse("2026-09-01T00:00:00.000Z");
  return Array.from({ length: 80 }, (_, index) => ({
    symbol: "7203.T",
    sessionDate: "2026-09-01",
    featureCutoff: new Date(start + index * 10 * 60_000).toISOString(),
    outcomeAt: new Date(start + index * 10 * 60_000 + 5 * 60_000).toISOString(),
    pointInTimeValid: true,
    horizonBars: 1,
    label: 1,
    actualReturnPct: 0.2,
    features: { returnFromOpen: index / 100 },
  }));
}

const selectionOptions = Object.freeze({
  featureFamilies: { TEST: ["returnFromOpen"] },
  modelConfigs: [{ id: "TEST", type: "LOGISTIC_REGRESSION", options: {} }],
  thresholds: [0.55],
  innerTrainFraction: 0.6,
  innerTestFraction: 0.15,
  innerMinTrainRows: 20,
  minInnerSignals: 5,
  minimumInnerNetReturnPct: 0,
  roundTripCostPct: 0.05,
  fitPredictor: () => () => 0.8,
});

function selectionAndBars() {
  const rows = Array.from({ length: 20 }, (_, index) => ({
    symbol: `${1001 + index}.T`,
    sector: `S${index % 4}`,
    currentPrice: 1000 + index,
    opportunityScore: 0.8 - index / 100,
    v2Score: 0.75 - index / 100,
  }));
  return {
    point: {
      at: AT,
      sourceAsOf: AT,
      v1CandidateId: "DYNAMIC5M_V1_FROZEN",
      v2CandidateId: "DYNAMIC5M_V2_FROZEN",
      selectedV1: rows,
      selectedV2: rows.slice(0, 15),
    },
    barsBySymbol: Object.fromEntries(rows.map((row, index) => [row.symbol, bars(index)])),
  };
}

function stubScore({ symbol, bars5m }) {
  const featureCutoff = bars5m.at(-1).timestamp;
  return {
    complete: true,
    modelId: "phase57-p21-prospective-test-h1",
    artifactSha256: "a".repeat(64),
    decision: {
      direction: 1,
      confidence: 0.8,
      setup: "TEST",
      asOf: featureCutoff,
      frozenByPhase57: true,
      pointInTimeOnly: true,
      futureOutcomeUsed: false,
      thresholdSearchAfterCapture: false,
      entryRetunedAfterCapture: false,
      context: {
        probability: 0.8,
        signalEligible: true,
        selectedHorizonBars: 1,
        selectedFeatureFamily: "TEST",
        selectedModelType: "LOGISTIC_REGRESSION",
        selectedConfigId: "TEST",
        selectedThreshold: 0.55,
        symbol,
      },
    },
  };
}

test("Realtime Frozen Entry adapter matches the existing batch P21 scorer", () => {
  const prefix = bars();
  const history = { 1: historicalRows() };
  const feed = buildProspectiveP21FeatureFeed({
    symbol: "7203.T",
    sessionDate: SESSION_DATE,
    bars5m: prefix,
    horizons: [1],
    latestBarClosed: true,
  });
  const batch = buildProspectiveP21FrozenDecision({
    historicalHorizonRowsByBars: history,
    currentRowsByHorizon: feed.currentRowsByHorizon,
    options: selectionOptions,
  });
  const realtime = scoreRealtimeFrozenEntry({
    symbol: "7203.T",
    sessionDate: SESSION_DATE,
    bars5m: prefix,
    historicalHorizonRowsByBars: history,
    selectionOptions,
  });
  assert.equal(batch.complete, true);
  assert.equal(realtime.complete, true);
  assert.deepEqual(realtime.decision, batch.decision);
  assert.equal(realtime.modelId, batch.modelId);
  assert.equal(realtime.artifactSha256, batch.artifactSha256);
});

test("finalized selection point freezes V1/V2 Entry price and lineage append-only", () => {
  const session = createRealtimeSessionState({ sessionDate: SESSION_DATE });
  const { point, barsBySymbol } = selectionAndBars();
  const first = evaluateRealtimeFrozenEntries(session, { at: AT, selectionPoint: point, barsBySymbol, scoreEntry: stubScore });
  assert.equal(first.frozenEntries.length, 35);
  assert.equal(first.audits.filter((row) => row.status === "DYNAMIC_POINT_ENTRY_SET_FROZEN").length, 2);
  const entry = first.frozenEntries[0];
  assert.equal(entry.entryTimestamp, AT);
  assert.equal(entry.entryPrice, 1000);
  assert.equal(entry.selectionLineage.variantId, "DYNAMIC5M_V1");
  assert.equal(entry.strategyLineage.strategyIds.length, 14);
  assert.equal(entry.currentOutcomeUsed, false);
  assert.equal("futureBars" in entry, false);
  assert.equal(session.ledger.filter((event) => event.type === "FROZEN_ENTRY_DECISIONS_COMMITTED").length, 1);

  const replayed = evaluateRealtimeFrozenEntries(session, { at: AT, selectionPoint: point, barsBySymbol, scoreEntry: stubScore });
  assert.equal(replayed, first);
  assert.equal(session.entry.history.length, 1);
  assert.equal(session.ledger.filter((event) => event.type === "FROZEN_ENTRY_DECISIONS_COMMITTED").length, 1);

  const changed = { ...point, selectedV1: point.selectedV1.map((row, index) => index ? row : { ...row, currentPrice: row.currentPrice + 1 }) };
  assert.throws(
    () => evaluateRealtimeFrozenEntries(session, { at: AT, selectionPoint: changed, barsBySymbol, scoreEntry: stubScore }),
    /conflicting duplicate Entry evaluation timestamp/,
  );
});

test("Entry evaluation rejects backward timestamps", () => {
  const session = createRealtimeSessionState({ sessionDate: SESSION_DATE });
  const { point, barsBySymbol } = selectionAndBars();
  evaluateRealtimeFrozenEntries(session, { at: AT, selectionPoint: point, barsBySymbol, scoreEntry: stubScore });
  const earlier = "2026-09-03T00:25:00.000Z";
  assert.throws(
    () => evaluateRealtimeFrozenEntries(session, { at: earlier, selectionPoint: { ...point, at: earlier }, barsBySymbol, scoreEntry: stubScore }),
    /cannot move backward/,
  );
});

test("per-strategy position state moves FLAT to OPEN exactly once", () => {
  const session = createRealtimeSessionState({ sessionDate: SESSION_DATE });
  const { point, barsBySymbol } = selectionAndBars();
  const frozen = evaluateRealtimeFrozenEntries(session, { at: AT, selectionPoint: point, barsBySymbol, scoreEntry: stubScore });
  const entry = frozen.frozenEntries.find((row) => row.selectionLineage.variant === "V1");
  const strategyId = "V1_V3__MAX_10";
  assert.equal(positionStateFor(session, strategyId, entry.symbol).status, POSITION_STATUS.FLAT);
  const accounting = {
    quantity: 100,
    entryExecutionPrice: entry.entryPrice,
    referenceNotional: entry.entryPrice * 100,
    entryExecutionNotional: entry.entryPrice * 100,
    entryCostJpy: entry.entryPrice * 100 * 0.00025,
    entrySlippageCostJpy: 0,
    collateralJpy: entry.entryPrice * 100,
    cashRequiredJpy: entry.entryPrice * 100 * 1.00025,
  };
  const opened = commitShadowPositionEntry(session, { strategyId, entry, accounting });
  assert.equal(opened.status, POSITION_STATUS.OPEN);
  assert.equal(session.strategies[strategyId].positions[entry.symbol], opened);
  assert.equal(session.strategies[strategyId].positionStates[entry.symbol], opened);
  assert.equal(session.strategies[strategyId].cash, 1_000_000 - accounting.cashRequiredJpy);
  assert.equal(session.ledger.filter((event) => event.type === "SHADOW_POSITION_OPENED").length, 1);

  const duplicate = commitShadowPositionEntry(session, { strategyId, entry, accounting });
  assert.equal(duplicate, opened);
  assert.equal(session.strategies[strategyId].cash, 1_000_000 - accounting.cashRequiredJpy);
  assert.equal(session.ledger.filter((event) => event.type === "SHADOW_POSITION_OPENED").length, 1);
  assert.throws(
    () => commitShadowPositionEntry(session, { strategyId, entry, accounting: { ...accounting, quantity: 200 } }),
    /conflicting duplicate Shadow position Entry/,
  );
});

test("R4 safety remains Shadow-only with all write surfaces disabled", () => {
  for (const key of [
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
    "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
  ]) assert.equal(PHASE57_REALTIME_ENTRY_SAFETY[key], false, key);
});
