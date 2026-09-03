import { buildIntradayDynamicUniverseTimeline } from "../daytrade/phase57-p25-intraday-dynamic-universe.js";
import { buildIntradayDynamicUniverseTimelineV2 } from "../daytrade/phase57-p25-intraday-dynamic-universe-v2.js";

export const PHASE57_MSII_DYNAMIC_WATCHLIST_VERSION = "phase57-msii-dynamic-watchlist-r2";
export const PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY = Object.freeze({
  mode: "LANE_M_DYNAMIC_MARKET_DATA_QUERY_ONLY",
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  excelMarketDataQueryWriteAllowed: true,
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
const V1_MIN_READY = 20;
const V2_MIN_READY = 15;
const V1_MAX_FROZEN = 50;
const V2_MAX_FROZEN = 30;

function assertSafety() {
  for (const key of FALSE_KEYS) if (PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY[key] !== false) throw new Error(`unsafe dynamic watchlist ${key}`);
  if (PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY.excelMarketDataQueryWriteAllowed !== true) throw new Error("dynamic market-data query writes must be explicitly scoped");
}
function iso(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} invalid`);
  return new Date(parsed).toISOString();
}
function normalizeSymbol(value) {
  const raw = String(value ?? "").trim().toUpperCase();
  if (!raw) return "";
  if (/^\d+(?:\.0+)?$/.test(raw)) return `${String(Math.trunc(Number(raw)))}.T`;
  return raw.endsWith(".T") ? raw : raw;
}
function unique(values) { return [...new Set(values.map(normalizeSymbol).filter(Boolean))]; }
function validateSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") throw new Error("TradingView raw snapshot required");
  const entries = Array.isArray(snapshot) ? snapshot : snapshot.entries;
  if (!Array.isArray(entries) || entries.length < 3000) throw new Error("dynamic watchlist requires >=3000 marketwide entries");
  const observedAt = iso(snapshot?.meta?.observedAt, "marketwide observedAt");
  return { entries, observedAt };
}

/**
 * Build the prospective MarketSpeed observation set from the same point-in-time TradingView
 * snapshot used by Lane Y. V2 is computed with its frozen prior-selection state. No result,
 * fill, outcome or later Yahoo bar is used here.
 *
 * Important: the frozen V1 selector has a maximum combined size of 50, not a guarantee that
 * the DAY/SWING merged-and-diversified result is always exactly 50. Likewise V2 is capped at 30.
 * Requiring exact cardinalities here would silently redefine the frozen selector. Lane M instead
 * uses the same readiness floors already enforced by the realtime runner (V1 >=20, V2 >=15).
 */
export function buildPhase57MsiiDynamicWatchlist({
  snapshot,
  priorV2Selections = [],
  recentV1Selections = [],
  pinnedSymbols = [],
  slotCount = 80,
  retentionPoints = 3,
} = {}) {
  assertSafety();
  const { entries, observedAt } = validateSnapshot(snapshot);
  if (!Number.isInteger(Number(slotCount)) || Number(slotCount) < 50) throw new Error("slotCount must be an integer >= 50");
  if (!Number.isInteger(Number(retentionPoints)) || Number(retentionPoints) < 0) throw new Error("retentionPoints must be a non-negative integer");
  const heldSymbolsByCutoff = { [observedAt]: [] };
  const snapshots = [{ asOf: observedAt, entries }];
  const v1Result = buildIntradayDynamicUniverseTimeline({ snapshots, heldSymbolsByCutoff });
  const v2Result = buildIntradayDynamicUniverseTimelineV2({ snapshots, heldSymbolsByCutoff, priorSelections: priorV2Selections });
  const v1 = unique((v1Result.points?.[0]?.rawUniverse ?? []).map((row) => row.symbol));
  const v2 = unique((v2Result.points?.[0]?.rawUniverse ?? []).map((row) => row.symbol));
  if (v1.length < V1_MIN_READY || v1.length > V1_MAX_FROZEN) throw new Error(`dynamic V1 prospective watchlist outside frozen readiness range: observed ${v1.length}`);
  if (v2.length < V2_MIN_READY || v2.length > V2_MAX_FROZEN) throw new Error(`dynamic V2 prospective watchlist outside frozen readiness range: observed ${v2.length}`);
  const v1Set = new Set(v1);
  const v2OutsideV1 = v2.filter((symbol) => !v1Set.has(symbol));
  if (v2OutsideV1.length) throw new Error(`dynamic V2 escaped V1 base universe: ${v2OutsideV1.join(",")}`);

  const pinned = unique(pinnedSymbols);
  const hardRequired = unique([...v1, ...pinned]);
  if (hardRequired.length > Number(slotCount)) {
    return Object.freeze({
      schemaVersion: 1,
      version: PHASE57_MSII_DYNAMIC_WATCHLIST_VERSION,
      status: "BLOCKED_DYNAMIC_SLOT_CAPACITY",
      complete: false,
      observedAt,
      slotCount: Number(slotCount),
      currentV1Symbols: Object.freeze(v1),
      currentV2Symbols: Object.freeze(v2),
      pinnedSymbols: Object.freeze(pinned),
      requiredSymbolCount: hardRequired.length,
      overflowRequiredSymbols: Object.freeze(hardRequired.slice(Number(slotCount))),
      assignedSymbols: Object.freeze([]),
      futureOutcomeUsed: false,
      safety: PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY,
    });
  }

  const retainedCandidates = [];
  const recent = [...(Array.isArray(recentV1Selections) ? recentV1Selections : [])].slice(-Number(retentionPoints)).reverse();
  for (const selection of recent) retainedCandidates.push(...unique(Array.isArray(selection) ? selection : []));
  const requiredSet = new Set(hardRequired);
  const retained = unique(retainedCandidates).filter((symbol) => !requiredSet.has(symbol));
  const capacityLeft = Number(slotCount) - hardRequired.length;
  const retainedAssigned = retained.slice(0, capacityLeft);
  const assigned = unique([...hardRequired, ...retainedAssigned]);

  return Object.freeze({
    schemaVersion: 1,
    version: PHASE57_MSII_DYNAMIC_WATCHLIST_VERSION,
    status: "PHASE57_MSII_DYNAMIC_WATCHLIST_READY",
    complete: true,
    observedAt,
    slotCount: Number(slotCount),
    retentionPoints: Number(retentionPoints),
    currentV1Symbols: Object.freeze(v1),
    currentV2Symbols: Object.freeze(v2),
    pinnedSymbols: Object.freeze(pinned),
    retainedSymbols: Object.freeze(retainedAssigned),
    droppedRetentionSymbols: Object.freeze(retained.slice(capacityLeft)),
    requiredSymbolCount: hardRequired.length,
    assignedSymbolCount: assigned.length,
    assignedSymbols: Object.freeze(assigned),
    v2PriorSelectionsNext: Object.freeze([...(Array.isArray(priorV2Selections) ? priorV2Selections : []), v2].slice(-3).map((row) => Object.freeze([...row]))),
    recentV1SelectionsNext: Object.freeze([...(Array.isArray(recentV1Selections) ? recentV1Selections : []), v1].slice(-Math.max(1, Number(retentionPoints))).map((row) => Object.freeze([...row]))),
    methodology: Object.freeze({
      source: "TRADINGVIEW_JAPAN_SCANNER_POINT_IN_TIME",
      dynamicSelectionEvaluatedAtObservedAt: true,
      laterYahooBarUsed: false,
      laneYDelayedCapsuleUsedForCurrentSelection: false,
      pinnedSymbolsOnlyFromAlreadyObservedLaneMInventory: true,
      retentionIsCoverageOnly: true,
      retentionChangesResearchDecision: false,
      selectorCardinalityPreservedExactly: true,
      v1FrozenMaximum: V1_MAX_FROZEN,
      v2FrozenMaximum: V2_MAX_FROZEN,
      v1ReadinessFloor: V1_MIN_READY,
      v2ReadinessFloor: V2_MIN_READY,
      futureOutcomeUsed: false,
    }),
    futureOutcomeUsed: false,
    safety: PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY,
  });
}

export default { buildPhase57MsiiDynamicWatchlist };
