import { createHash } from "node:crypto";
import { buildProspectiveP21FeatureFeed } from "../daytrade/phase57-p21-prospective-feature-feed.js";
import { buildProspectiveP21FrozenDecision } from "../daytrade/phase57-p21-prospective-frozen-base.js";
import { buildFrozenPhase57SnapshotFromRuntimeDecision } from "../scalping/phase58-phase57-runtime-adapter.js";
import {
  ALLOCATION_PROFILES,
  SAFETY,
  STRATEGY_IDS,
  appendLedgerEvent,
} from "./phase57-stateful-contract.js";

export const POSITION_STATUS = Object.freeze({ FLAT: "FLAT", OPEN: "OPEN", CLOSED: "CLOSED" });

export const REALTIME_FROZEN_ENTRY_POLICY = Object.freeze({
  scorer: "PHASE57_P21_FROZEN_ENTRY",
  scannerObservedPriceIsEntryReference: true,
  completedFiveMinutePrefixOnly: true,
  minimumClosedPrefixBars: 6,
  variants: Object.freeze({
    V1: Object.freeze({ variantId: "DYNAMIC5M_V1", minimumSelected: 20, cells: Object.freeze(["V1_V3", "V1_V4"]) }),
    V2: Object.freeze({ variantId: "DYNAMIC5M_V2", minimumSelected: 15, cells: Object.freeze(["V2_V3", "V2_V4"]) }),
  }),
  entryThresholdRelaxationAllowed: false,
  futureBarsPassedToScorer: false,
  resultBasedRetuning: false,
});

export const PHASE57_REALTIME_ENTRY_SAFETY = SAFETY;

const FALSE_SAFETY_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

const finite = (value) => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
const sym = (value) => String(value ?? "").trim().toUpperCase();

function assertSafety() {
  for (const key of FALSE_SAFETY_KEYS) {
    if (PHASE57_REALTIME_ENTRY_SAFETY[key] !== false) throw new Error(`realtime Entry safety ${key} must remain false`);
  }
}

function timestampMs(value, label = "timestamp") {
  const milliseconds = Date.parse(String(value ?? ""));
  if (!Number.isFinite(milliseconds)) throw new Error(`${label} must be a valid timestamp`);
  return milliseconds;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

function fingerprint(value) {
  return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
}

function normalizeBar(bar) {
  const timestamp = bar?.timestamp ?? bar?.time ?? bar?.at;
  const parsed = Date.parse(String(timestamp ?? ""));
  const normalized = {
    timestamp: Number.isFinite(parsed) ? new Date(parsed).toISOString() : null,
    open: Number(bar?.open),
    high: Number(bar?.high),
    low: Number(bar?.low),
    close: Number(bar?.close),
    volume: Number(bar?.volume ?? 0),
  };
  if (!normalized.timestamp || ![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)) return null;
  if (normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.volume < 0) return null;
  return Object.freeze(normalized);
}

function sourceRows(source, symbol) {
  if (source instanceof Map) return source.get(symbol) ?? source.get(symbol.replace(/\.T$/, "")) ?? source.get(`${symbol}.T`) ?? [];
  return source?.[symbol] ?? source?.[symbol.replace(/\.T$/, "")] ?? source?.[`${symbol}.T`] ?? [];
}

function closedPrefix(source, symbol, atMs) {
  const rows = Array.isArray(sourceRows(source, symbol)) ? sourceRows(source, symbol) : [];
  return Object.freeze(rows.map(normalizeBar).filter(Boolean)
    // This is the exact Dynamic5m batch convention: bar.timestamp is its start,
    // therefore it becomes visible only after its five-minute close.
    .filter((bar) => Date.parse(bar.timestamp) + 5 * 60_000 <= atMs)
    .sort((left, right) => left.timestamp.localeCompare(right.timestamp)));
}

function selectionRows(point, variant) {
  return variant === "V1" ? point?.selectedV1 : point?.selectedV2;
}

function ensureUniqueSelection(rows, variant) {
  const symbols = rows.map((row) => sym(row?.symbol));
  if (symbols.some((symbol) => !symbol)) throw new Error(`${variant} selection contains a blank symbol`);
  if (new Set(symbols).size !== symbols.length) throw new Error(`${variant} selection contains duplicate symbols`);
}

export function ensureRealtimeEntryState(sessionState) {
  if (!sessionState?.strategies || !sessionState?.ledger) throw new Error("realtime session state required");
  sessionState.entry ??= { lastEvaluationTime: null, latest: [], history: [] };
  sessionState.entry.latest ??= [];
  sessionState.entry.history ??= [];
  sessionState.entry.lastEvaluationTime ??= null;
  return sessionState.entry;
}

/**
 * Adapter around the exact Frozen Entry functions used by the Dynamic5m batch matrix.
 * It builds the same P21 feature feed, calls the same prior-only scorer, then applies
 * the same frozen runtime attestation. No Entry threshold or weight is reimplemented.
 */
export function scoreRealtimeFrozenEntry({
  symbol,
  sessionDate,
  bars5m = [],
  historicalHorizonRowsByBars = {},
  selectionOptions = {},
  priorOnlyCache = null,
} = {}) {
  assertSafety();
  const feed = buildProspectiveP21FeatureFeed({
    symbol: sym(symbol),
    sessionDate,
    bars5m,
    horizons: Object.keys(historicalHorizonRowsByBars).map(Number),
    latestBarClosed: true,
  });
  if (!feed.complete) return Object.freeze({ complete: false, status: "BLOCKED_P21_CURRENT_FEATURE_FEED", feed, safety: SAFETY });

  const base = buildProspectiveP21FrozenDecision({
    historicalHorizonRowsByBars,
    currentRowsByHorizon: feed.currentRowsByHorizon,
    options: selectionOptions,
    priorOnlyCache,
  });
  if (!base.complete || !base.decision) return Object.freeze({ complete: false, status: "BLOCKED_P21_PROSPECTIVE_BASE", feed, base, safety: SAFETY });

  const snapshot = buildFrozenPhase57SnapshotFromRuntimeDecision({
    decision: base.decision,
    modelId: base.modelId,
    artifactSha256: base.artifactSha256,
  });
  if (!snapshot.complete) return Object.freeze({ complete: false, status: "BLOCKED_PHASE57_RUNTIME_ADAPTER", feed, base, snapshot, safety: SAFETY });

  return Object.freeze({
    complete: true,
    status: "REALTIME_FROZEN_ENTRY_SCORED",
    decision: base.decision,
    modelId: base.modelId,
    artifactSha256: base.artifactSha256,
    featureCutoff: feed.featureCutoff,
    frozenSnapshot: snapshot.snapshot,
    safety: SAFETY,
  });
}

function strategyLineage(variant) {
  const cells = REALTIME_FROZEN_ENTRY_POLICY.variants[variant].cells;
  const strategyIds = cells.flatMap((cell) => ALLOCATION_PROFILES.map((profile) => `${cell}__${profile}`));
  if (strategyIds.some((id) => !STRATEGY_IDS.includes(id))) throw new Error(`invalid ${variant} strategy lineage`);
  return Object.freeze({ cells, strategyIds: Object.freeze(strategyIds) });
}

function requestFingerprint({ at, selectionPoint, barsBySymbol }) {
  const atMs = timestampMs(at, "Entry evaluation timestamp");
  const variants = {};
  for (const variant of ["V1", "V2"]) {
    const rows = Array.isArray(selectionRows(selectionPoint, variant)) ? selectionRows(selectionPoint, variant) : [];
    variants[variant] = rows.map((row) => ({ row, closedPrefix: closedPrefix(barsBySymbol, sym(row?.symbol), atMs) }));
  }
  return fingerprint({ at, selectionAt: selectionPoint?.at ?? null, variants });
}

/** Evaluate one finalized Dynamic5m selection point with only already-closed bars. */
export function evaluateRealtimeFrozenEntries(sessionState, {
  at,
  selectionPoint = sessionState?.selection?.history?.at(-1),
  barsBySymbol = {},
  scoreEntry,
} = {}) {
  assertSafety();
  if (typeof scoreEntry !== "function") throw new Error("scoreEntry function required");
  const atMs = timestampMs(at, "Entry evaluation timestamp");
  if (!selectionPoint || timestampMs(selectionPoint.at, "selectionPoint.at") !== atMs) {
    throw new Error("Entry evaluation requires the selection point from the same timestamp");
  }

  const entryState = ensureRealtimeEntryState(sessionState);
  const requestSha256 = requestFingerprint({ at, selectionPoint, barsBySymbol });
  if (entryState.lastEvaluationTime) {
    const lastMs = timestampMs(entryState.lastEvaluationTime, "last Entry evaluation timestamp");
    if (atMs < lastMs) throw new Error("Entry evaluation timestamp cannot move backward");
    if (atMs === lastMs) {
      const previous = entryState.history.at(-1);
      if (previous?.requestSha256 !== requestSha256) throw new Error("conflicting duplicate Entry evaluation timestamp");
      return previous;
    }
  }

  const frozenEntries = [];
  const audits = [];
  for (const variant of ["V1", "V2"]) {
    const policy = REALTIME_FROZEN_ENTRY_POLICY.variants[variant];
    const rows = Array.isArray(selectionRows(selectionPoint, variant)) ? selectionRows(selectionPoint, variant) : [];
    ensureUniqueSelection(rows, variant);
    const validRows = rows.filter((row) => sym(row?.symbol) && finite(row?.currentPrice) && Number(row.currentPrice) > 0);
    if (validRows.length !== rows.length || validRows.length < policy.minimumSelected) {
      audits.push(Object.freeze({ at, variant, status: "BLOCKED_DYNAMIC_POINT_MISSING_ENTRY_REFERENCE", selectedCount: validRows.length }));
      continue;
    }

    const scored = [];
    let blockedReason = null;
    for (const row of validRows) {
      const symbol = sym(row.symbol);
      const prefix = closedPrefix(barsBySymbol, symbol, atMs);
      if (prefix.length < REALTIME_FROZEN_ENTRY_POLICY.minimumClosedPrefixBars) {
        blockedReason = `INSUFFICIENT_CLOSED_PREFIX:${symbol}`;
        break;
      }
      let result;
      try {
        result = scoreEntry({ symbol, sessionDate: sessionState.sessionDate, bars5m: prefix, at, selectionRow: row });
      } catch (error) {
        blockedReason = `SCORER_EXCEPTION:${String(error?.message ?? error)}`;
        break;
      }
      const decision = result?.decision;
      if (!result?.complete || !decision) {
        blockedReason = String(result?.status ?? "SCORER_NOT_READY");
        break;
      }
      if (decision.futureOutcomeUsed !== false || decision.frozenByPhase57 !== true || decision.pointInTimeOnly !== true) {
        blockedReason = "FROZEN_ENTRY_ATTESTATION_FAILED";
        break;
      }
      scored.push({ row, symbol, prefix, result, decision, context: decision.context ?? {} });
    }
    if (blockedReason) {
      audits.push(Object.freeze({ at, variant, status: "BLOCKED_DYNAMIC_POINT_ENTRY_SET", reason: blockedReason, selectedCount: validRows.length }));
      continue;
    }

    const lineage = strategyLineage(variant);
    let signalCount = 0;
    for (const scoredRow of scored) {
      const direction = Number(scoredRow.decision.direction);
      if (scoredRow.context.signalEligible !== true || ![-1, 1].includes(direction)) continue;
      signalCount += 1;
      const candidateId = `${sessionState.sessionDate}|${at}|${policy.variantId}|${scoredRow.symbol}`;
      frozenEntries.push(Object.freeze({
        candidateId,
        batchEntryKey: `${sessionState.sessionDate}|${at}|${scoredRow.symbol}`,
        entryAccepted: true,
        symbol: scoredRow.symbol,
        sessionDate: sessionState.sessionDate,
        entryTimestamp: at,
        featureCutoff: String(scoredRow.decision.asOf ?? scoredRow.prefix.at(-1)?.timestamp ?? at),
        signalDirection: direction,
        direction: direction === 1 ? "LONG" : "SHORT",
        baseHorizonBars: Number(scoredRow.context.selectedHorizonBars),
        confidence: finite(scoredRow.decision.confidence) ? Number(scoredRow.decision.confidence) : null,
        probability: finite(scoredRow.context.probability) ? Number(scoredRow.context.probability) : null,
        selectedFeatureFamily: scoredRow.context.selectedFeatureFamily ?? scoredRow.decision.setup ?? null,
        selectedModelType: scoredRow.context.selectedModelType ?? null,
        selectedConfigId: scoredRow.context.selectedConfigId ?? null,
        selectedThreshold: finite(scoredRow.context.selectedThreshold) ? Number(scoredRow.context.selectedThreshold) : null,
        modelId: scoredRow.result.modelId,
        artifactSha256: scoredRow.result.artifactSha256,
        sector: String(scoredRow.row.sector ?? "UNKNOWN"),
        variantMemberships: Object.freeze([policy.variantId]),
        entryPrice: Number(scoredRow.row.currentPrice),
        contextBars: scoredRow.prefix,
        outcomePending: true,
        frozenBeforeOutcome: true,
        currentOutcomeUsed: false,
        selectionLineage: Object.freeze({
          variant,
          variantId: policy.variantId,
          selectionTimestamp: at,
          sourceAsOf: selectionPoint.sourceAsOf ?? null,
          selectorCandidateId: variant === "V1" ? selectionPoint.v1CandidateId : selectionPoint.v2CandidateId,
          opportunityScore: finite(scoredRow.row.opportunityScore) ? Number(scoredRow.row.opportunityScore) : null,
          v2Score: finite(scoredRow.row.v2Score) ? Number(scoredRow.row.v2Score) : null,
        }),
        strategyLineage: lineage,
      }));
    }
    audits.push(Object.freeze({ at, variant, status: "DYNAMIC_POINT_ENTRY_SET_FROZEN", selectedCount: validRows.length, signalCount }));
  }

  const result = Object.freeze({
    at,
    requestSha256,
    frozenEntries: Object.freeze(frozenEntries),
    audits: Object.freeze(audits),
    safety: SAFETY,
  });
  entryState.lastEvaluationTime = at;
  entryState.latest = result.frozenEntries;
  entryState.history.push(result);
  appendLedgerEvent(sessionState, {
    eventId: `${sessionState.sessionDate}:${at}:FROZEN_ENTRY_DECISIONS`,
    at,
    type: "FROZEN_ENTRY_DECISIONS_COMMITTED",
    requestSha256,
    candidateIds: frozenEntries.map((entry) => entry.candidateId),
  });
  return result;
}

export function positionStateFor(sessionState, strategyId, symbol) {
  const strategy = sessionState?.strategies?.[strategyId];
  if (!strategy) throw new Error(`unknown strategyId ${strategyId}`);
  strategy.positionStates ??= {};
  const normalizedSymbol = sym(symbol);
  if (!normalizedSymbol) throw new Error("position symbol required");
  strategy.positionStates[normalizedSymbol] ??= Object.freeze({
    status: POSITION_STATUS.FLAT,
    strategyId,
    symbol: normalizedSymbol,
    lastEventTime: null,
  });
  return strategy.positionStates[normalizedSymbol];
}

/** Commit an allocator-approved Shadow Entry. This function never creates an order payload. */
export function commitShadowPositionEntry(sessionState, {
  strategyId,
  entry,
  accounting,
} = {}) {
  assertSafety();
  const strategy = sessionState?.strategies?.[strategyId];
  if (!strategy) throw new Error(`unknown strategyId ${strategyId}`);
  if (!entry?.entryAccepted || entry?.frozenBeforeOutcome !== true || entry?.currentOutcomeUsed !== false) {
    throw new Error("Shadow position Entry requires an outcome-free Frozen Entry");
  }
  if (!entry?.strategyLineage?.strategyIds?.includes(strategyId)) throw new Error("strategy is outside Frozen Entry lineage");
  const symbol = sym(entry.symbol);
  const at = String(entry.entryTimestamp ?? "");
  timestampMs(at, "position Entry timestamp");
  const quantity = Number(accounting?.quantity);
  const entryReferencePrice = Number(entry.entryPrice);
  const entryExecutionPrice = Number(accounting?.entryExecutionPrice);
  const referenceNotional = Number(accounting?.referenceNotional);
  const entryExecutionNotional = Number(accounting?.entryExecutionNotional);
  const entryCostJpy = Number(accounting?.entryCostJpy);
  const entrySlippageCostJpy = Number(accounting?.entrySlippageCostJpy ?? 0);
  const collateralJpy = Number(accounting?.collateralJpy);
  const cashRequiredJpy = Number(accounting?.cashRequiredJpy);
  if (!Number.isInteger(quantity) || quantity <= 0 || ![entryReferencePrice, entryExecutionPrice, referenceNotional, entryExecutionNotional, entryCostJpy, entrySlippageCostJpy, collateralJpy, cashRequiredJpy].every(Number.isFinite)) {
    throw new Error("invalid Shadow position Entry accounting");
  }
  if ([entryReferencePrice, entryExecutionPrice, referenceNotional, entryExecutionNotional, collateralJpy, cashRequiredJpy].some((value) => value <= 0) || entryCostJpy < 0) {
    throw new Error("Shadow position Entry accounting must be positive");
  }

  const eventId = `${sessionState.sessionDate}:${at}:POSITION_ENTRY:${strategyId}:${symbol}`;
  const entrySha256 = fingerprint({ strategyId, entry, accounting });
  const prior = positionStateFor(sessionState, strategyId, symbol);
  if (prior.status === POSITION_STATUS.OPEN && prior.entryEventId === eventId) {
    if (prior.entrySha256 !== entrySha256) throw new Error("conflicting duplicate Shadow position Entry");
    return prior;
  }
  if (prior.status !== POSITION_STATUS.FLAT) throw new Error(`position ${strategyId}/${symbol} is not FLAT`);
  if (prior.lastEventTime && timestampMs(at) <= timestampMs(prior.lastEventTime)) throw new Error("position Entry timestamp must be strictly causal");
  if (cashRequiredJpy > Number(strategy.cash) + 1e-8) throw new Error("insufficient Shadow strategy cash");

  strategy.transactionCosts ??= 0;
  strategy.slippageCosts ??= 0;
  strategy.turnoverNotional ??= 0;
  strategy.cash -= cashRequiredJpy;
  strategy.realizedPnl -= entryCostJpy;
  strategy.transactionCosts += entryCostJpy;
  strategy.slippageCosts += entrySlippageCostJpy;
  strategy.turnoverNotional += entryExecutionNotional;

  const position = Object.freeze({
    status: POSITION_STATUS.OPEN,
    strategyId,
    symbol,
    positionId: `${strategyId}|${entry.candidateId}`,
    entryEventId: eventId,
    entrySha256,
    entryCandidateId: entry.candidateId,
    entryTimestamp: at,
    entryReferencePrice,
    entryExecutionPrice,
    signalDirection: Number(entry.signalDirection),
    quantity,
    referenceNotional,
    entryExecutionNotional,
    entryCostJpy,
    entrySlippageCostJpy,
    collateralJpy,
    cashRequiredJpy,
    sector: entry.sector,
    contextBars: entry.contextBars,
    selectionLineage: entry.selectionLineage,
    strategyLineage: Object.freeze({ strategyId, cells: entry.strategyLineage.cells }),
    openedInShadowOnly: true,
    lastEventTime: at,
    lastMarkPrice: entryReferencePrice,
    unrealizedPnl: -entryCostJpy,
    exitState: null,
  });
  strategy.positions[symbol] = position;
  strategy.positionStates[symbol] = position;
  appendLedgerEvent(sessionState, {
    eventId,
    at,
    type: "SHADOW_POSITION_OPENED",
    strategyId,
    symbol,
    positionId: position.positionId,
    entryCandidateId: entry.candidateId,
    entryReferencePrice,
    quantity,
    selectionLineage: entry.selectionLineage,
    strategyLineage: position.strategyLineage,
    executable: false,
  });
  return position;
}

export default {
  POSITION_STATUS,
  REALTIME_FROZEN_ENTRY_POLICY,
  PHASE57_REALTIME_ENTRY_SAFETY,
  ensureRealtimeEntryState,
  scoreRealtimeFrozenEntry,
  evaluateRealtimeFrozenEntries,
  positionStateFor,
  commitShadowPositionEntry,
};
