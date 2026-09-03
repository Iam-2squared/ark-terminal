import {
  PHASE57_MSII_FILL_STATUS,
  PHASE57_MSII_ORDER_STYLE,
  PHASE57_MSII_SHADOW_SAFETY,
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
} from "./phase57-msii-shadow-execution.js";

export const PHASE57_MSII_RUNTIME_VERSION = "phase57-msii-shadow-runtime-r3-audit";

const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

function assertSafety() {
  for (const key of FALSE_KEYS) {
    if (PHASE57_MSII_SHADOW_SAFETY[key] !== false) throw new Error(`Lane M runtime safety ${key} must remain false`);
  }
}

function ms(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a valid absolute timestamp`);
  return parsed;
}

function iso(value, label = "timestamp") {
  return new Date(ms(value, label)).toISOString();
}

function normalizeSymbol(value) {
  const raw = String(value ?? "").trim().toUpperCase();
  if (/^\d+(?:\.0+)?$/.test(raw)) return `${String(Math.trunc(Number(raw)))}.T`;
  return raw;
}

function requiredVersions(versions = {}) {
  const fields = ["selectorVersion", "entryVersion", "exitV3Version", "exitV4Version", "allocationVersion"];
  for (const field of fields) {
    if (!String(versions[field] ?? "").trim()) throw new Error(`Lane M runtime versions.${field} is required`);
  }
  return Object.freeze(Object.fromEntries(fields.map((field) => [field, String(versions[field]).trim()])));
}

function latestReferenceEvents(events, decisionAt, referenceMaxAgeMs) {
  const cutoff = ms(decisionAt, "decisionAt");
  const maxAge = Number(referenceMaxAgeMs);
  if (!Number.isFinite(maxAge) || maxAge < 0) throw new Error("referenceMaxAgeMs must be non-negative");
  const bySymbol = new Map();
  for (const event of events) {
    const observed = ms(event.capturedAt);
    if (observed > cutoff || cutoff - observed > maxAge) continue;
    const key = normalizeSymbol(event.symbol);
    const prior = bySymbol.get(key);
    if (!prior || observed > ms(prior.capturedAt)) bySymbol.set(key, event);
  }
  return bySymbol;
}

function eventRowsFromLedger(ledger) {
  return ledger
    .filter((row) => row.eventType === "MSII_MARKET_EVENT_COMMITTED")
    .map((row) => row.marketEvent);
}

function latestFillByIntent(ledger) {
  const out = new Map();
  for (const event of ledger.filter((row) => row.eventType === "SHADOW_FILL_COMMITTED")) {
    const prior = out.get(event.fill.intentId);
    if (!prior || event.sequence > prior.sequence) out.set(event.fill.intentId, event.fill);
  }
  return out;
}

function committedIntents(ledger) {
  return ledger
    .filter((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED")
    .map((row) => row.intent)
    .sort((left, right) => left.decisionSequence - right.decisionSequence || left.intentId.localeCompare(right.intentId));
}

function nextDecisionSequence(ledger) {
  return committedIntents(ledger).reduce((max, row) => Math.max(max, Number(row.decisionSequence) || 0), -1) + 1;
}

function exitVersionFor(strategyId, versions) {
  const cell = String(strategyId).split("__")[0];
  return cell.endsWith("_V4") ? versions.exitV4Version : versions.exitV3Version;
}

function executionInventory(ledger) {
  const fills = latestFillByIntent(ledger);
  const open = new Map();
  for (const intent of committedIntents(ledger)) {
    const filledQuantity = Number(fills.get(intent.intentId)?.filledQuantity ?? 0);
    if (!(filledQuantity > 0)) continue;
    const key = `${intent.strategyId}|${normalizeSymbol(intent.symbol)}`;
    const prior = Number(open.get(key) ?? 0);
    if (intent.intentKind === "ENTRY") open.set(key, prior + filledQuantity);
    else open.set(key, Math.max(0, prior - filledQuantity));
  }
  return open;
}

function capClosedPositionsToLaneMInventory(ledger, closed = []) {
  const inventory = executionInventory(ledger);
  return closed.map((position) => {
    const key = `${position.strategyId}|${normalizeSymbol(position.symbol)}`;
    const available = Number(inventory.get(key) ?? 0);
    const laneYQuantity = Number(position.quantity ?? 0);
    const quantity = Math.min(available, laneYQuantity);
    return quantity > 0 ? Object.freeze({ ...position, quantity }) : null;
  }).filter(Boolean);
}

export function buildExitShadowOrderIntentsFromPhase57({
  exitEvaluation,
  marketEventsBySymbol,
  decisionAt = exitEvaluation?.at,
  decisionSequenceStart = 0,
  orderStyleResearchLabel = PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
  ttlMs,
  decisionLatencyMs,
  versions,
} = {}) {
  assertSafety();
  const frozenVersions = requiredVersions(versions);
  if (!exitEvaluation || !Array.isArray(exitEvaluation.closed)) throw new Error("Phase57 exitEvaluation.closed[] is required");
  const at = iso(decisionAt, "exit decisionAt");
  const sorted = [...exitEvaluation.closed].sort((left, right) =>
    String(left.strategyId).localeCompare(String(right.strategyId)) || String(left.symbol).localeCompare(String(right.symbol)));
  return Object.freeze(sorted.map((position, index) => {
    const symbol = normalizeSymbol(position.symbol);
    const referenceEvent = marketEventsBySymbol instanceof Map
      ? marketEventsBySymbol.get(symbol)
      : marketEventsBySymbol?.[symbol];
    if (!referenceEvent) throw new Error(`MarketSpeed source snapshot missing for EXIT ${position.strategyId}/${symbol}`);
    const direction = Number(position.signalDirection);
    if (![-1, 1].includes(direction)) throw new Error(`closed Phase57 position has invalid signalDirection for ${position.strategyId}/${symbol}`);
    const quantity = Number(position.quantity);
    const referencePrice = Number(position.exitReferencePrice ?? position.lastMarkPrice);
    return createShadowOrderIntent({
      strategyId: position.strategyId,
      symbol,
      side: direction === 1 ? "SELL" : "BUY",
      intentKind: "EXIT",
      decisionAt: at,
      decisionSequence: Number(decisionSequenceStart) + index,
      requestedQuantity: quantity,
      referencePrice,
      referenceEvent,
      orderStyleResearchLabel,
      ttlMs,
      decisionLatencyMs,
      selectorVersion: frozenVersions.selectorVersion,
      entryVersion: frozenVersions.entryVersion,
      exitVersion: exitVersionFor(position.strategyId, frozenVersions),
      allocationVersion: frozenVersions.allocationVersion,
      futureOutcomeUsed: false,
    });
  }));
}

function rehydrateState({
  sessionDate,
  predeclaredStartAt,
  actualStartAt,
  missingCaptureCount,
  backfillUsed,
  initialCapital,
  priorLedger,
}) {
  const state = createMsiiShadowExecutionState({
    sessionDate,
    predeclaredStartAt,
    actualStartAt,
    missingCaptureCount,
    backfillUsed,
    initialCapital,
  });
  if (Array.isArray(priorLedger) && priorLedger.length) {
    verifyMsiiShadowLedger(priorLedger, { sessionDate });
    state.ledger = structuredClone(priorLedger);
    state.ledgerHeadHash = state.ledger.at(-1).eventHash;
    state.sessionQuality = classifyMsiiSession({ predeclaredStartAt, actualStartAt, missingCaptureCount, backfillUsed });
  }
  return state;
}

function newEventsOnly(state, events) {
  const committed = new Set(eventRowsFromLedger(state.ledger).map((event) => event.eventId));
  return events.filter((event) => !committed.has(event.eventId));
}

function commitEventsInRange(state, events, predicate) {
  const rows = newEventsOnly(state, events).filter(predicate)
    .sort((left, right) => ms(left.capturedAt) - ms(right.capturedAt) || left.symbol.localeCompare(right.symbol) || left.eventId.localeCompare(right.eventId));
  for (const event of rows) commitNormalizedMarketEvent(state, event);
  return rows.length;
}

function pairPositiveEntryForExit(ledger, exitIntent, fillsByIntent, consumedEntryIntentIds) {
  const candidates = committedIntents(ledger).filter((intent) =>
    intent.intentKind === "ENTRY"
    && intent.strategyId === exitIntent.strategyId
    && intent.symbol === exitIntent.symbol
    && ms(intent.decisionAt) < ms(exitIntent.decisionAt)
    && Number(fillsByIntent.get(intent.intentId)?.filledQuantity ?? 0) > 0
    && !consumedEntryIntentIds.has(intent.intentId))
    .sort((left, right) => ms(right.decisionAt) - ms(left.decisionAt));
  return candidates[0] ?? null;
}

function commitClosedTrades(state, { transactionCostJpy = 0 } = {}) {
  const fills = latestFillByIntent(state.ledger);
  const priorTrades = state.ledger
    .filter((row) => row.eventType === "SHADOW_EXECUTION_TRADE_CLOSED")
    .map((row) => row.trade);
  const existingExitIntentIds = new Set(priorTrades.map((trade) => trade.exitIntentId));
  const consumedEntryIntentIds = new Set(priorTrades.map((trade) => trade.entryIntentId));
  let committed = 0;
  for (const exitIntent of committedIntents(state.ledger).filter((row) => row.intentKind === "EXIT")) {
    if (existingExitIntentIds.has(exitIntent.intentId)) continue;
    const exitFill = fills.get(exitIntent.intentId);
    if (!(Number(exitFill?.filledQuantity) > 0)) continue;
    const entryIntent = pairPositiveEntryForExit(state.ledger, exitIntent, fills, consumedEntryIntentIds);
    if (!entryIntent) continue;
    const entryFill = fills.get(entryIntent.intentId);
    const trade = buildExecutionAwareClosedTrade({
      entryIntent,
      entryFill,
      exitIntent,
      exitFill,
      transactionCostJpy,
    });
    commitExecutionAwareClosedTrade(state, trade);
    existingExitIntentIds.add(exitIntent.intentId);
    consumedEntryIntentIds.add(entryIntent.intentId);
    committed += 1;
  }
  return committed;
}

/**
 * Process one already-frozen Phase57 realtime decision point against causal MarketSpeed II READ ONLY observations.
 * This function never creates a broker/RSS/Excel order and never mutates the supplied Phase57 state.
 */
export function processMsiiShadowRuntimePoint({
  sessionDate,
  predeclaredStartAt,
  actualStartAt,
  missingCaptureCount = 0,
  backfillUsed = false,
  initialCapital = 1_000_000,
  priorLedger = [],
  captureRows = [],
  phase57State,
  pointResult,
  versions,
  orderStyleResearchLabel = PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
  ttlMs = 5_000,
  decisionLatencyMs = 100,
  referenceMaxAgeMs = 5_000,
  marketSizeUnit,
  tickSizeUnit,
  transactionCostJpy = 0,
  laneYDecisions = [],
} = {}) {
  assertSafety();
  const frozenVersions = requiredVersions(versions);
  const decisionAt = iso(pointResult?.at, "pointResult.at");
  if (!phase57State?.strategies) throw new Error("Phase57 realtime state is required");
  if (!pointResult?.allocation || !pointResult?.exitEvaluation) throw new Error("Phase57 pointResult allocation and exitEvaluation are required");
  if (!Array.isArray(captureRows) || captureRows.length === 0) throw new Error("Lane M requires at least one MarketSpeed synchronized capture row");
  if (marketSizeUnit !== "SHARES" || tickSizeUnit !== "SHARES") {
    throw new Error("Lane M runtime requires explicit verified marketSizeUnit=SHARES and tickSizeUnit=SHARES attestation");
  }
  if (!Number.isFinite(Number(referenceMaxAgeMs)) || Number(referenceMaxAgeMs) < 0) {
    throw new Error("Lane M runtime referenceMaxAgeMs must be non-negative");
  }

  const state = rehydrateState({
    sessionDate,
    predeclaredStartAt,
    actualStartAt,
    missingCaptureCount,
    backfillUsed,
    initialCapital,
    priorLedger,
  });
  const normalized = captureRows.map((row) => normalizeMarketSpeedReadOnlyEvent(row, { marketSizeUnit, tickSizeUnit }))
    .sort((left, right) => ms(left.capturedAt) - ms(right.capturedAt) || left.symbol.localeCompare(right.symbol) || left.eventId.localeCompare(right.eventId));
  const referenceEvents = latestReferenceEvents(
    [...eventRowsFromLedger(state.ledger), ...normalized],
    decisionAt,
    Number(referenceMaxAgeMs),
  );

  const acceptedSymbols = new Set(pointResult.allocation.decisions
    .filter((row) => row.status === "ACCEPTED")
    .map((row) => normalizeSymbol(row.symbol)));
  const laneMClosed = capClosedPositionsToLaneMInventory(state.ledger, pointResult.exitEvaluation.closed ?? []);
  const exitSymbols = new Set(laneMClosed.map((row) => normalizeSymbol(row.symbol)));
  const requiredSymbols = [...new Set([...acceptedSymbols, ...exitSymbols])].sort();
  const missingReferenceSymbols = requiredSymbols.filter((symbol) => !referenceEvents.has(symbol));
  if (missingReferenceSymbols.length) {
    return Object.freeze({
      complete: false,
      status: "BLOCKED_MSII_REFERENCE_CAPTURE_MISSING_OR_STALE",
      decisionAt,
      referenceMaxAgeMs: Number(referenceMaxAgeMs),
      missingReferenceSymbols: Object.freeze(missingReferenceSymbols),
      ledger: Object.freeze(state.ledger),
      score: scoreMsiiShadowExecutionLedger(state.ledger, { sessionDate }),
      pair: compareLaneYWithMsii({ laneYDecisions, msiiLedger: state.ledger }),
      safety: PHASE57_MSII_SHADOW_SAFETY,
    });
  }

  commitEventsInRange(state, normalized, (event) => ms(event.capturedAt) <= ms(decisionAt));
  const sequenceStart = nextDecisionSequence(state.ledger);
  const entryIntents = buildEntryShadowOrderIntentsFromPhase57({
    phase57State,
    allocationResult: pointResult.allocation,
    marketEventsBySymbol: referenceEvents,
    decisionAt,
    decisionSequenceStart: sequenceStart,
    orderStyleResearchLabel,
    ttlMs,
    decisionLatencyMs,
    versions: frozenVersions,
  });
  const exitIntents = buildExitShadowOrderIntentsFromPhase57({
    exitEvaluation: { ...pointResult.exitEvaluation, closed: laneMClosed },
    marketEventsBySymbol: referenceEvents,
    decisionAt,
    decisionSequenceStart: sequenceStart + entryIntents.length,
    orderStyleResearchLabel,
    ttlMs,
    decisionLatencyMs,
    versions: frozenVersions,
  });
  const intents = [...entryIntents, ...exitIntents].sort((left, right) => left.decisionSequence - right.decisionSequence || left.intentId.localeCompare(right.intentId));
  for (const intent of intents) commitShadowOrderIntent(state, intent);

  commitEventsInRange(state, normalized, (event) => ms(event.capturedAt) > ms(decisionAt));
  const availableEvents = eventRowsFromLedger(state.ledger);
  const cutoffAt = availableEvents.length
    ? availableEvents.reduce((latest, event) => ms(event.capturedAt) > ms(latest) ? event.capturedAt : latest, availableEvents[0].capturedAt)
    : decisionAt;
  for (const intent of intents) {
    const fill = evaluateShadowFill(intent, availableEvents, { asOf: cutoffAt });
    commitShadowFill(state, fill);
  }
  const closedTradesCommitted = commitClosedTrades(state, { transactionCostJpy });
  const score = scoreMsiiShadowExecutionLedger(state.ledger, { sessionDate });
  const pair = compareLaneYWithMsii({ laneYDecisions, msiiLedger: state.ledger });

  return Object.freeze({
    complete: true,
    status: "PHASE57_MSII_RUNTIME_POINT_COMMITTED",
    version: PHASE57_MSII_RUNTIME_VERSION,
    decisionAt,
    normalizedCaptureCount: normalized.length,
    referenceMaxAgeMs: Number(referenceMaxAgeMs),
    requiredSymbols: Object.freeze(requiredSymbols),
    entryIntentCount: entryIntents.length,
    exitIntentCount: exitIntents.length,
    closedTradesCommitted,
    cutoffAt,
    ledger: Object.freeze(state.ledger),
    score,
    pair,
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  });
}

export default {
  PHASE57_MSII_RUNTIME_VERSION,
  buildExitShadowOrderIntentsFromPhase57,
  processMsiiShadowRuntimePoint,
};
