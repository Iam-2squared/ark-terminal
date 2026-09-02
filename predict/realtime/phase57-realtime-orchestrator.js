import { createHash } from "node:crypto";
import { SAFETY, appendLedgerEvent, verifyRealtimeLedger } from "./phase57-stateful-contract.js";
import { applyMarketFiveMinuteBar } from "./phase57-incremental-features.js";
import { applyRealtimeDynamic5mSelection } from "./phase57-realtime-dynamic5m-selection.js";
import { evaluateRealtimeFrozenEntries } from "./phase57-realtime-entry-position.js";
import { applyRealtimeExitBar } from "./phase57-realtime-exit-v3-v4.js";
import { allocateRealtimeFrozenEntries } from "./phase57-realtime-allocation.js";
import { commitRealtimeDashboardSnapshot } from "./phase57-realtime-dashboard.js";

const FALSE_KEYS = [
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
];

function assertSafety() {
  for (const key of FALSE_KEYS) if (SAFETY[key] !== false) throw new Error(`unsafe realtime orchestrator ${key}`);
}
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
}
function sha256(value) { return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex"); }
function atOf(bar) { return bar?.at ?? bar?.time ?? bar?.timestamp; }
function normalizeSymbol(value) { return String(value ?? "").trim().toUpperCase(); }
function marksFromBars(bars) {
  return Object.fromEntries((bars ?? []).map((row) => [normalizeSymbol(row.symbol), Number(row.bar?.close)]));
}
function currentBarsFromRows(rows, at) {
  return Object.fromEntries((rows ?? []).map((row) => {
    const symbol = normalizeSymbol(row.symbol);
    const bar = row.bar ?? {};
    return [symbol, { ...bar, timestamp: at }];
  }));
}
function openSymbols(state) {
  const out = new Set();
  for (const strategy of Object.values(state.strategies ?? {})) for (const symbol of Object.keys(strategy.positions ?? {})) out.add(symbol);
  return [...out].sort();
}

export function ensureRealtimePipelineState(state) {
  state.pipeline ??= { lastPointTime: null, lastRequestSha256: null, history: [] };
  state.pipeline.history ??= [];
  return state.pipeline;
}

/**
 * One finalized 5-minute research cycle. No order payload is ever created.
 * Ordering is intentionally fixed: Bars/Features -> Selection -> Frozen Entry -> EXIT existing positions -> Allocation -> Dashboard.
 */
export function processRealtimeFiveMinutePoint(state, {
  at,
  marketBars = [],
  selectionEntries = [],
  barsBySymbolHistory = {},
  scoreEntry,
  analogPool = [],
  sessionEnd = false,
  sessionQuality = "UNKNOWN",
  missingBucketCount = 0,
  expectedBucketCount = 68,
} = {}) {
  assertSafety();
  if (!at || !Number.isFinite(Date.parse(String(at)))) throw new Error("realtime point timestamp required");
  if (!Array.isArray(marketBars) || !Array.isArray(selectionEntries)) throw new Error("marketBars[] and selectionEntries[] required");
  if (typeof scoreEntry !== "function") throw new Error("scoreEntry function required");

  const pipeline = ensureRealtimePipelineState(state);
  const requestSha256 = sha256({ at, marketBars, selectionEntries, sessionEnd, sessionQuality, missingBucketCount, expectedBucketCount });
  if (pipeline.lastPointTime) {
    const current = Date.parse(String(at));
    const previous = Date.parse(String(pipeline.lastPointTime));
    if (current < previous) throw new Error("realtime pipeline timestamp cannot move backward");
    if (current === previous) {
      if (pipeline.lastRequestSha256 !== requestSha256) throw new Error("conflicting duplicate realtime point");
      return pipeline.history.at(-1);
    }
  }

  for (const row of marketBars) {
    const symbol = normalizeSymbol(row?.symbol);
    if (!symbol) throw new Error("market bar symbol required");
    const barAt = atOf(row?.bar);
    if (Date.parse(String(barAt ?? "")) !== Date.parse(String(at))) throw new Error(`market bar timestamp mismatch for ${symbol}`);
    applyMarketFiveMinuteBar(state, { symbol, bar: row.bar });
  }

  appendLedgerEvent(state, {
    eventId: `${state.sessionDate}:${at}:BAR_FINALIZED_SET`, at, type: "BAR_FINALIZED",
    symbolCount: marketBars.length, executable: false,
  });
  appendLedgerEvent(state, {
    eventId: `${state.sessionDate}:${at}:FEATURES_UPDATED`, at, type: "FEATURES_UPDATED",
    symbolCount: marketBars.length, executable: false,
  });

  const selection = applyRealtimeDynamic5mSelection(state, { at, entries: selectionEntries, heldSymbols: openSymbols(state) });
  const entries = evaluateRealtimeFrozenEntries(state, { at, selectionPoint: selection, barsBySymbol: barsBySymbolHistory, scoreEntry });

  const finalizedBarsBySymbol = currentBarsFromRows(marketBars, at);
  const exits = applyRealtimeExitBar(state, { at, barsBySymbol: finalizedBarsBySymbol, analogPool, sessionEnd });
  const marksBySymbol = marksFromBars(marketBars);
  const allocation = allocateRealtimeFrozenEntries(state, { at, entries: entries.frozenEntries, marksBySymbol });
  const dashboard = commitRealtimeDashboardSnapshot(state, { at, sessionQuality, missingBucketCount, expectedBucketCount });

  verifyRealtimeLedger(state.ledger, { sessionDate: state.sessionDate });
  const result = Object.freeze({
    at,
    requestSha256,
    selection: Object.freeze({ v1: selection.selectedV1Count, v2: selection.selectedV2Count }),
    frozenEntryCount: entries.frozenEntries.length,
    exitEvaluation: exits,
    allocation,
    dashboard,
    ledgerHeadHash: state.ledgerHeadHash,
    safety: SAFETY,
  });
  pipeline.lastPointTime = at;
  pipeline.lastRequestSha256 = requestSha256;
  pipeline.history.push(result);
  return result;
}

export const PHASE57_REALTIME_ORCHESTRATOR_SAFETY = SAFETY;
