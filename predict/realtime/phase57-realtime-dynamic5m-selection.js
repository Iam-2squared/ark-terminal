import {
  buildIntradayDynamicUniverseTimeline,
} from "../daytrade/phase57-p25-intraday-dynamic-universe.js";
import {
  buildIntradayDynamicUniverseTimelineV2,
  PHASE57_INTRADAY_UNIVERSE_V2_POLICY,
} from "../daytrade/phase57-p25-intraday-dynamic-universe-v2.js";
import { appendLedgerEvent } from "./phase57-stateful-contract.js";

const sym = (value) => String(value ?? "").trim().toUpperCase();

function normalizeSelection(rows) {
  return Object.freeze((rows ?? []).map((row) => Object.freeze({ ...row })));
}

export function ensureRealtimeSelectionState(sessionState) {
  if (!sessionState?.selection) throw new Error("realtime session state required");
  sessionState.selection.lastSelectionTime ??= null;
  sessionState.selection.priorV2 ??= [];
  sessionState.selection.history ??= [];
  return sessionState.selection;
}

export function applyRealtimeDynamic5mSelection(sessionState, {
  at,
  entries,
  heldSymbols = [],
} = {}) {
  if (!at) throw new Error("at required");
  if (!Array.isArray(entries)) throw new Error("entries[] required");
  const selectionState = ensureRealtimeSelectionState(sessionState);
  if (selectionState.lastSelectionTime && at <= selectionState.lastSelectionTime) {
    throw new Error("selection timestamp must be strictly causal");
  }

  const heldSymbolsByCutoff = { [at]: heldSymbols.map(sym).filter(Boolean) };
  const snapshots = [{ asOf: at, entries }];

  // Reuse the frozen batch selectors so realtime and batch share identical research semantics.
  const v1Timeline = buildIntradayDynamicUniverseTimeline({ snapshots, heldSymbolsByCutoff });
  const v2Timeline = buildIntradayDynamicUniverseTimelineV2({
    snapshots,
    heldSymbolsByCutoff,
    priorSelections: selectionState.priorV2,
  });

  const v1Point = v1Timeline.points[0];
  const v2Point = v2Timeline.points[0];
  if (!v1Point || !v2Point) throw new Error("Dynamic5m selector returned no cadence point");

  const selectedV1 = normalizeSelection(v1Point.rawUniverse);
  const selectedV2 = normalizeSelection(v2Point.rawUniverse);
  const allocationEligibleV1 = normalizeSelection(v1Point.allocationEligibleUniverse);
  const allocationEligibleV2 = normalizeSelection(v2Point.allocationEligibleUniverse);

  selectionState.V1 = selectedV1;
  selectionState.V2 = selectedV2;
  selectionState.lastSelectionTime = at;
  selectionState.priorV2.push(selectedV2.map((row) => row.symbol));
  while (selectionState.priorV2.length > PHASE57_INTRADAY_UNIVERSE_V2_POLICY.persistenceWindowPoints) {
    selectionState.priorV2.shift();
  }

  const point = Object.freeze({
    at,
    sourceAsOf: v1Point.sourceAsOf,
    selectedV1,
    selectedV2,
    allocationEligibleV1,
    allocationEligibleV2,
    selectedV1Count: selectedV1.length,
    selectedV2Count: selectedV2.length,
    priorV2PointCount: Math.max(0, selectionState.priorV2.length - 1),
    v1CandidateId: v1Timeline.candidateId,
    v2CandidateId: v2Timeline.candidateId,
  });
  selectionState.history.push(point);

  appendLedgerEvent(sessionState, {
    eventId: `${sessionState.sessionDate}:${at}:DYNAMIC5M_SELECTION`,
    at,
    type: "DYNAMIC5M_SELECTION_COMMITTED",
    selectedV1: selectedV1.map((row) => row.symbol),
    selectedV2: selectedV2.map((row) => row.symbol),
    allocationEligibleV1: allocationEligibleV1.map((row) => row.symbol),
    allocationEligibleV2: allocationEligibleV2.map((row) => row.symbol),
  });

  return point;
}

export function realtimeSelectionSnapshot(sessionState) {
  const selectionState = ensureRealtimeSelectionState(sessionState);
  return Object.freeze({
    at: selectionState.lastSelectionTime,
    selectedV1: normalizeSelection(selectionState.V1),
    selectedV2: normalizeSelection(selectionState.V2),
    historyPoints: selectionState.history.length,
    priorV2PointCount: selectionState.priorV2.length,
  });
}
