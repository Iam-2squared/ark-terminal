import { createHash } from "node:crypto";
import { MATRIX_CELLS, ALLOCATION_PROFILES, STRATEGY_IDS } from "./phase57-stateful-contract.js";
import { PHASE57_P25_LANE_C_POLICY } from "../portfolio/phase57-p25-lane-c-portfolio-simulator.js";

export const PHASE57_MSII_SHADOW_VERSION = "phase57-msii-shadow-execution-r1";
export const PHASE57_MSII_SOURCE_MODE = "MARKETSPEED_II_RSS_READ_ONLY";
export const PHASE57_MSII_SHADOW_SAFETY = Object.freeze({
  mode: "MARKETSPEED_II_PROSPECTIVE_SHADOW_EXECUTION_READ_ONLY",
  researchOnly: true,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
  futureOutcomeUsed: false,
});

export const PHASE57_MSII_FILL_STATUS = Object.freeze({
  FILLED: "FILLED",
  PARTIAL: "PARTIAL",
  NO_FILL: "NO_FILL",
  EXPIRED: "EXPIRED",
  SOURCE_NOT_READY: "SOURCE_NOT_READY",
});

export const PHASE57_MSII_ORDER_STYLE = Object.freeze({
  MARKETABLE_QUOTE: "MARKETABLE_QUOTE",
  PASSIVE_REFERENCE: "PASSIVE_REFERENCE",
});

export const PHASE57_MSII_SESSION_QUALITY = Object.freeze({
  FULL_FRESH_MSII: "FULL_FRESH_MSII",
  PARTIAL_INCOMPLETE_MSII: "PARTIAL_INCOMPLETE_MSII",
  SOURCE_NOT_READY: "SOURCE_NOT_READY",
});

const SAFETY_FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);
const FORBIDDEN_RSS_ORDER_FUNCTIONS = Object.freeze([
  "RssStockOrder", "RssStockOrder_v",
  "RssMarginOpenOrder", "RssMarginOpenOrder_v", "RssMarginCloseOrder", "RssMarginCloseOrder_v",
  "RssModifyOrder", "RssModifyOrder_v", "RssCancelOrder", "RssCancelOrder_v",
  "RssFOPOpenOrder", "RssFOPOpenOrder_v", "RssFOPCloseOrder", "RssFOPCloseOrder_v",
  "RssFOPMultiOpenOrder", "RssFOPMultiOpenOrder_v", "RssFOPMultiCloseOrder", "RssFOPMultiCloseOrder_v",
  "RssFOPModifyOrder", "RssFOPModifyOrder_v", "RssFOPCancelOrder", "RssFOPCancelOrder_v",
  "RssFutureOrder", "RssOptionOrder",
]);
const FORBIDDEN_RSS_ORDER_FUNCTION_SET = new Set(FORBIDDEN_RSS_ORDER_FUNCTIONS.map((name) => name.toUpperCase()));
const GENESIS_HASH = "0".repeat(64);
const LOT_SIZE = Number(PHASE57_P25_LANE_C_POLICY.lotSize);

function canonical(value) {
  if (value instanceof Map) {
    return Object.fromEntries([...value.entries()]
      .sort(([left], [right]) => String(left).localeCompare(String(right)))
      .map(([key, row]) => [String(key), canonical(row)]));
  }
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

function sha256(value) {
  return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
}

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) deepFreeze(child);
  return Object.freeze(value);
}

function finite(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function numberOrNull(value) {
  return finite(value) ? Number(value) : null;
}

function requiredText(value, label) {
  const text = String(value ?? "").trim();
  if (!text) throw new TypeError(`${label} is required`);
  return text;
}

function timestamp(value, label) {
  const milliseconds = Date.parse(String(value ?? ""));
  if (!Number.isFinite(milliseconds)) throw new TypeError(`${label} must be a valid absolute timestamp`);
  return new Date(milliseconds).toISOString();
}

function jstSessionDate(value) {
  const iso = timestamp(value, "timestamp");
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(iso));
  const fields = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}

function normalizeSymbol(value) {
  const raw = requiredText(value, "symbol").toUpperCase();
  if (/^\d+(?:\.0+)?$/.test(raw)) return `${String(Math.trunc(Number(raw)))}.T`;
  if (/^\d+\.T$/.test(raw)) return raw;
  return raw;
}

function assertSafetyMap(safety, label) {
  if (!safety || typeof safety !== "object") throw new Error(`${label} safety contract is required`);
  for (const key of SAFETY_FALSE_KEYS) {
    if (safety[key] !== false) throw new Error(`${label}.${key} must remain false`);
  }
  if (safety.transmitted !== undefined && safety.transmitted !== false) throw new Error(`${label}.transmitted must remain false`);
}

function assertModuleSafety() {
  assertSafetyMap(PHASE57_MSII_SHADOW_SAFETY, "Lane M safety");
}

function normalizeTickTimestamp(value, sessionDate, capturedAt) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  if (/^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?$/.test(raw)) {
    const [clock, fraction = ""] = raw.split(".");
    const [hour, minute, second] = clock.split(":").map(Number);
    if (hour > 23 || minute > 59 || second > 59) return null;
    const time = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}${fraction ? `.${fraction}` : ""}`;
    return timestamp(`${sessionDate}T${time}+09:00`, "tick timestamp");
  }
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return null;
  const iso = new Date(parsed).toISOString();
  if (jstSessionDate(iso) !== sessionDate) return null;
  if (Date.parse(iso) > Date.parse(capturedAt)) throw new Error("MarketSpeed tick is in the future relative to capturedAt");
  return iso;
}

function sourceFunctions(row) {
  const values = row?.sourceFunctions ?? row?.rssFunctionsUsed ?? [];
  return Array.isArray(values) ? values.map((value) => String(value).trim()).filter(Boolean) : [];
}

/** Normalize one Phase58 synchronized capture without filling absent market values. */
export function normalizeMarketSpeedReadOnlyEvent(row, {
  marketSizeUnit = row?.marketSizeUnit ?? null,
  tickSizeUnit = row?.tickSizeUnit ?? null,
} = {}) {
  assertModuleSafety();
  if (!row || typeof row !== "object" || Array.isArray(row)) throw new TypeError("Phase58 synchronized capture row is required");
  if (row.schemaVersion !== 2 || row.phase !== "58.p9.sync-capture") throw new Error("Lane M requires Phase58 synchronized capture schemaVersion 2");
  if (row.sourceMode !== PHASE57_MSII_SOURCE_MODE) throw new Error("Lane M accepts MarketSpeed II RSS READ ONLY source only");
  assertSafetyMap(row.safety, "capture.safety");
  if (row.methodology?.futureOutcomeUsed !== false || row.methodology?.historicalDecisionReconstructionAllowed !== false) {
    throw new Error("Lane M capture must be prospective and outcome-free");
  }
  if (row.methodology?.phase57DirectionIsFrozenBase !== true
    || row.methodology?.phase58MayConfirmDeferOrAbstainOnly !== true
    || row.methodology?.phase58MayReverseDirection !== false
    || row.methodology?.pointInTimeOnly !== true
    || row.methodology?.sameCaptureBoundary !== true) {
    throw new Error("Lane M requires the Frozen Phase57 point-in-time methodology boundary");
  }
  if (row.phase57Snapshot?.frozen !== true
    || row.phase57Snapshot?.futureOutcomeUsed !== false
    || row.phase57Snapshot?.thresholdSearchAfterCapture !== false
    || row.phase57Snapshot?.entryRetunedAfterCapture !== false) {
    throw new Error("Lane M requires a Frozen Phase57 snapshot with futureOutcomeUsed=false");
  }
  requiredText(row.phase57Snapshot.modelId, "phase57Snapshot.modelId");
  if (!/^[a-f0-9]{64}$/i.test(String(row.phase57Snapshot.artifactSha256 ?? ""))) {
    throw new Error("phase57Snapshot.artifactSha256 must be 64 hex chars");
  }
  const functions = sourceFunctions(row);
  const forbidden = functions.find((name) => FORBIDDEN_RSS_ORDER_FUNCTION_SET.has(name.toUpperCase()));
  if (forbidden) throw new Error(`forbidden RSS order function in capture provenance: ${forbidden}`);

  const capturedAt = timestamp(row.capturedAt, "capturedAt");
  const phase57AsOf = timestamp(row.phase57Snapshot.asOf, "phase57Snapshot.asOf");
  if (Date.parse(phase57AsOf) > Date.parse(capturedAt)) throw new Error("Frozen Phase57 snapshot is in the future relative to capturedAt");
  const selectorDirection = Number(row.phase57Snapshot.direction);
  if (![-1, 0, 1].includes(selectorDirection)) throw new Error("Frozen Phase57 direction must be -1, 0, or 1");
  const sessionDate = jstSessionDate(capturedAt);
  const symbol = normalizeSymbol(row.symbol);
  const market = row.market && typeof row.market === "object" ? row.market : {};
  const bestBid = numberOrNull(market.bestBid ?? market.bid);
  const bestAsk = numberOrNull(market.bestAsk ?? market.ask);
  const bidSize = numberOrNull(market.bestBidSize ?? market.bidSize ?? market.bidSize1);
  const askSize = numberOrNull(market.bestAskSize ?? market.askSize ?? market.askSize1);
  if (bestBid !== null && bestAsk !== null && bestAsk < bestBid) throw new Error("crossed MarketSpeed quote rejected");

  const blockers = [];
  if (!(bestBid > 0) || !(bestAsk > 0)) blockers.push("TOP_OF_BOOK_NOT_READY");
  if (!(bidSize >= 0) || !(askSize >= 0)) blockers.push("TOP_OF_BOOK_SIZE_NOT_READY");
  if (marketSizeUnit !== "SHARES") blockers.push("MARKET_SIZE_UNIT_NOT_DECLARED_AS_SHARES");
  if (tickSizeUnit !== "SHARES") blockers.push("TICK_SIZE_UNIT_NOT_DECLARED_AS_SHARES");

  const sourceTicks = Array.isArray(row.ticks) ? row.ticks : [];
  const ticks = [];
  for (let index = 0; index < sourceTicks.length; index += 1) {
    const raw = sourceTicks[index] ?? {};
    const tickAt = normalizeTickTimestamp(raw.timestamp ?? raw.time, sessionDate, capturedAt);
    const price = numberOrNull(raw.price ?? raw.executionPrice);
    const size = numberOrNull(raw.size ?? raw.volume);
    if (!tickAt || !(price > 0) || !(size >= 0)) {
      blockers.push(`INVALID_TICK_${index}`);
      continue;
    }
    if (Date.parse(tickAt) > Date.parse(capturedAt)) throw new Error("MarketSpeed tick is in the future relative to capturedAt");
    ticks.push({ timestamp: tickAt, price, size, sourceIndex: index });
  }
  ticks.sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp) || left.sourceIndex - right.sourceIndex);

  const midpoint = bestBid > 0 && bestAsk > 0 ? (bestBid + bestAsk) / 2 : null;
  const referenceSpread = bestBid > 0 && bestAsk > 0 ? bestAsk - bestBid : null;
  const sourceSnapshotHash = sha256(row);
  const event = {
    schemaVersion: 1,
    version: PHASE57_MSII_SHADOW_VERSION,
    type: "MSII_NORMALIZED_MARKET_EVENT",
    eventId: `MSII_MARKET|${sessionDate}|${capturedAt}|${symbol}|${sourceSnapshotHash.slice(0, 16)}`,
    symbol,
    sessionDate,
    capturedAt,
    quoteObservedAt: capturedAt,
    bestBid,
    bestAsk,
    bidSize,
    askSize,
    midpoint,
    referenceSpread,
    lastPrice: ticks.at(-1)?.price ?? null,
    ticks,
    marketSizeUnit,
    tickSizeUnit,
    quoteSourceReady: bestBid > 0 && bestAsk > 0 && bidSize >= 0 && askSize >= 0 && marketSizeUnit === "SHARES",
    tickSourceReady: ticks.length > 0 && tickSizeUnit === "SHARES",
    blockers: [...new Set(blockers)],
    sourceSnapshotHash,
    sourceMode: PHASE57_MSII_SOURCE_MODE,
    sourceFunctions: functions.length ? functions : ["RssMarket", "RssTickList"],
    phase57SnapshotHash: sha256(row.phase57Snapshot),
    selectorDirection,
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  return deepFreeze({ ...event, normalizedEventSha256: sha256(event) });
}

function strategyParts(strategyId) {
  const id = requiredText(strategyId, "strategyId");
  if (!STRATEGY_IDS.includes(id)) throw new Error(`strategyId is outside frozen 28-way identity: ${id}`);
  const [matrixCell, allocationProfile] = id.split("__");
  if (!MATRIX_CELLS.includes(matrixCell) || !ALLOCATION_PROFILES.includes(allocationProfile)) throw new Error(`invalid frozen strategy lineage: ${id}`);
  return { strategyId: id, matrixCell, allocationProfile };
}

function assertNormalizedEvent(event) {
  if (event?.type !== "MSII_NORMALIZED_MARKET_EVENT" || event?.sourceMode !== PHASE57_MSII_SOURCE_MODE) throw new Error("normalized MarketSpeed event required");
  assertSafetyMap(event.safety, "normalized event safety");
  if (event.futureOutcomeUsed !== false || event.transmitted !== false || event.executable !== false) throw new Error("normalized event is not Shadow-only");
  const { normalizedEventSha256, ...core } = event;
  if (normalizedEventSha256 !== sha256(core)) throw new Error("normalized MarketSpeed event hash mismatch");
}

export function createShadowOrderIntent({
  strategyId,
  symbol,
  side,
  intentKind = "ENTRY",
  decisionAt,
  decisionSequence,
  requestedQuantity,
  referencePrice,
  referenceEvent,
  orderStyleResearchLabel,
  ttlMs,
  decisionLatencyMs,
  selectorVersion,
  entryVersion,
  exitVersion,
  allocationVersion,
  futureOutcomeUsed = false,
} = {}) {
  assertModuleSafety();
  const parts = strategyParts(strategyId);
  assertNormalizedEvent(referenceEvent);
  const normalizedSymbol = normalizeSymbol(symbol);
  if (normalizedSymbol !== referenceEvent.symbol) throw new Error("intent symbol does not match source snapshot");
  const direction = requiredText(side, "side").toUpperCase();
  if (!['BUY', 'SELL'].includes(direction)) throw new Error("side must be BUY or SELL");
  const kind = requiredText(intentKind, "intentKind").toUpperCase();
  if (!['ENTRY', 'EXIT'].includes(kind)) throw new Error("intentKind must be ENTRY or EXIT");
  const at = timestamp(decisionAt, "decisionAt");
  if (Date.parse(referenceEvent.capturedAt) > Date.parse(at)) throw new Error("intent cannot use a future MarketSpeed snapshot");
  if (jstSessionDate(at) !== referenceEvent.sessionDate) throw new Error("intent/source snapshot session mismatch");
  const sequence = Number(decisionSequence);
  if (!Number.isInteger(sequence) || sequence < 0) throw new Error("decisionSequence must be a non-negative integer");
  const quantity = Number(requestedQuantity);
  if (!Number.isInteger(quantity) || quantity <= 0 || quantity % LOT_SIZE !== 0) throw new Error(`requestedQuantity must be a positive ${LOT_SIZE}-share lot multiple`);
  const price = Number(referencePrice);
  if (!Number.isFinite(price) || price <= 0) throw new Error("referencePrice must be positive");
  const ttl = Number(ttlMs);
  const latency = Number(decisionLatencyMs);
  if (!Number.isFinite(ttl) || ttl <= 0) throw new Error("ttlMs must be positive and explicitly predeclared");
  if (!Number.isFinite(latency) || latency < 0 || latency >= ttl) throw new Error("decisionLatencyMs must be non-negative and below ttlMs");
  const style = requiredText(orderStyleResearchLabel, "orderStyleResearchLabel");
  if (!Object.values(PHASE57_MSII_ORDER_STYLE).includes(style)) throw new Error(`unsupported Shadow order style: ${style}`);
  if (futureOutcomeUsed !== false) throw new Error("ShadowOrderIntent futureOutcomeUsed must remain false");

  const intentId = `MSII_INTENT|${referenceEvent.sessionDate}|${sequence}|${parts.strategyId}|${kind}|${normalizedSymbol}`;
  const intent = {
    schemaVersion: 1,
    version: PHASE57_MSII_SHADOW_VERSION,
    type: "SHADOW_ORDER_INTENT",
    intentId,
    strategyId: parts.strategyId,
    matrixCell: parts.matrixCell,
    allocationProfile: parts.allocationProfile,
    symbol: normalizedSymbol,
    side: direction,
    intentKind: kind,
    decisionAt: at,
    decisionSequence: sequence,
    requestedQuantity: quantity,
    requestedNotional: quantity * price,
    referencePrice: price,
    referenceBid: referenceEvent.bestBid,
    referenceAsk: referenceEvent.bestAsk,
    referenceSpread: referenceEvent.referenceSpread,
    orderStyleResearchLabel: style,
    ttl,
    ttlMs: ttl,
    expiresAt: new Date(Date.parse(at) + ttl).toISOString(),
    decisionLatencyMs: latency,
    fillEligibleAt: new Date(Date.parse(at) + latency).toISOString(),
    selectorVersion: requiredText(selectorVersion, "selectorVersion"),
    entryVersion: requiredText(entryVersion, "entryVersion"),
    exitVersion: requiredText(exitVersion, "exitVersion"),
    allocationVersion: requiredText(allocationVersion, "allocationVersion"),
    sourceEventId: referenceEvent.eventId,
    sourceSnapshotHash: referenceEvent.sourceSnapshotHash,
    sourceNormalizedEventSha256: referenceEvent.normalizedEventSha256,
    sourceSnapshotAt: referenceEvent.capturedAt,
    sourceReadyAtDecision: referenceEvent.quoteSourceReady,
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  return deepFreeze({ ...intent, intentSha256: sha256(intent) });
}

function eventForSymbol(source, symbol) {
  if (source instanceof Map) return source.get(symbol) ?? source.get(symbol.replace(/\.T$/, "")) ?? null;
  return source?.[symbol] ?? source?.[symbol.replace(/\.T$/, "")] ?? null;
}

/** Adapt already-frozen Phase57 allocation decisions; this never changes Lane Y state. */
export function buildEntryShadowOrderIntentsFromPhase57({
  phase57State,
  allocationResult,
  marketEventsBySymbol,
  decisionAt = allocationResult?.at,
  decisionSequenceStart = 0,
  orderStyleResearchLabel,
  ttlMs,
  decisionLatencyMs,
  versions = {},
} = {}) {
  if (!phase57State?.strategies || !allocationResult?.decisions) throw new Error("Phase57 state and allocation result are required");
  if (allocationResult.strategyCount !== STRATEGY_IDS.length) throw new Error("Lane M adapter requires all 28 Phase57 strategy identities");
  const accepted = allocationResult.decisions.filter((row) => row.status === "ACCEPTED")
    .sort((left, right) => String(left.strategyId).localeCompare(String(right.strategyId)) || String(left.symbol).localeCompare(String(right.symbol)));
  return Object.freeze(accepted.map((decision, index) => {
    const strategy = phase57State.strategies[decision.strategyId];
    const rawSymbol = String(decision.symbol);
    const position = strategy?.positions?.[rawSymbol] ?? strategy?.positions?.[normalizeSymbol(rawSymbol)];
    if (!position) throw new Error(`allocator-approved Shadow position missing for ${decision.strategyId}/${rawSymbol}`);
    const event = eventForSymbol(marketEventsBySymbol, normalizeSymbol(rawSymbol));
    if (!event) throw new Error(`MarketSpeed source snapshot missing for ${rawSymbol}`);
    return createShadowOrderIntent({
      strategyId: decision.strategyId,
      symbol: rawSymbol,
      side: Number(position.signalDirection) === 1 ? "BUY" : "SELL",
      intentKind: "ENTRY",
      decisionAt,
      decisionSequence: Number(decisionSequenceStart) + index,
      requestedQuantity: decision.quantity,
      referencePrice: position.entryReferencePrice,
      referenceEvent: event,
      orderStyleResearchLabel,
      ttlMs,
      decisionLatencyMs,
      selectorVersion: versions.selectorVersion,
      entryVersion: versions.entryVersion,
      exitVersion: String(decision.strategyId).split("__")[0].endsWith("_V4") ? versions.exitV4Version : versions.exitV3Version,
      allocationVersion: versions.allocationVersion,
      futureOutcomeUsed: false,
    });
  }));
}

function assertIntent(intent) {
  if (intent?.type !== "SHADOW_ORDER_INTENT" || !STRATEGY_IDS.includes(intent?.strategyId)) throw new Error("valid frozen 28-way ShadowOrderIntent required");
  assertSafetyMap(intent.safety, "intent safety");
  if (intent.futureOutcomeUsed !== false || intent.transmitted !== false || intent.executable !== false) throw new Error("intent is not Shadow-only");
  const { intentSha256, ...core } = intent;
  if (intentSha256 !== sha256(core)) throw new Error("ShadowOrderIntent hash mismatch");
}

function fillResult(intent, {
  status,
  reason,
  evaluatedAt,
  filledQuantity = 0,
  fillPrice = null,
  firstFillAt = null,
  lastFillAt = null,
  evidence = [],
}) {
  const quantity = Number(filledQuantity);
  const price = fillPrice === null ? null : Number(fillPrice);
  const mid = finite(intent.referenceBid) && finite(intent.referenceAsk) ? (Number(intent.referenceBid) + Number(intent.referenceAsk)) / 2 : null;
  const sideSign = intent.side === "BUY" ? 1 : -1;
  const referenceSide = intent.side === "BUY" ? numberOrNull(intent.referenceAsk) : numberOrNull(intent.referenceBid);
  const spreadCostJpy = quantity > 0 && mid !== null && referenceSide !== null ? Math.abs(referenceSide - mid) * quantity : 0;
  const slippageJpy = quantity > 0 && price !== null && referenceSide !== null ? sideSign * (price - referenceSide) * quantity : 0;
  const fill = {
    schemaVersion: 1,
    version: PHASE57_MSII_SHADOW_VERSION,
    type: "SHADOW_FILL",
    fillId: `MSII_FILL|${intent.intentId}|${timestamp(evaluatedAt, "evaluatedAt")}`,
    intentId: intent.intentId,
    intentSha256: intent.intentSha256,
    strategyId: intent.strategyId,
    symbol: intent.symbol,
    side: intent.side,
    intentKind: intent.intentKind,
    status,
    reason,
    evaluatedAt: timestamp(evaluatedAt, "evaluatedAt"),
    sourceObservationCutoff: timestamp(evaluatedAt, "evaluatedAt"),
    requestedQuantity: intent.requestedQuantity,
    filledQuantity: quantity,
    remainingQuantity: intent.requestedQuantity - quantity,
    fillPrice: price,
    filledNotional: price === null ? 0 : price * quantity,
    firstFillAt,
    lastFillAt,
    decisionToFirstFillLatencyMs: firstFillAt ? Date.parse(firstFillAt) - Date.parse(intent.decisionAt) : null,
    referenceSpread: intent.referenceSpread,
    spreadCostJpy,
    slippageJpy,
    adverseSlippageJpy: Math.max(0, slippageJpy),
    priceImprovementJpy: Math.max(0, -slippageJpy),
    evidence,
    sourceSnapshotHash: intent.sourceSnapshotHash,
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  return deepFreeze({ ...fill, fillSha256: sha256(fill) });
}

function causalEvents(intent, events, evaluatedAt) {
  const asOfMs = Date.parse(evaluatedAt);
  const decisionMs = Date.parse(intent.decisionAt);
  const expiresMs = Date.parse(intent.expiresAt);
  return [...(events ?? [])].map((event) => {
    assertNormalizedEvent(event);
    return event;
  }).filter((event) => event.symbol === intent.symbol
    && event.sessionDate === jstSessionDate(intent.decisionAt)
    && Date.parse(event.capturedAt) > decisionMs
    && Date.parse(event.capturedAt) <= asOfMs
    && Date.parse(event.capturedAt) <= expiresMs)
    .sort((left, right) => Date.parse(left.capturedAt) - Date.parse(right.capturedAt) || left.eventId.localeCompare(right.eventId));
}

/** Evaluate only observations visible by asOf; later rows in events are ignored. */
export function evaluateShadowFill(intent, events = [], { asOf } = {}) {
  assertModuleSafety();
  assertIntent(intent);
  const evaluatedAt = timestamp(asOf, "asOf");
  if (Date.parse(evaluatedAt) < Date.parse(intent.decisionAt)) throw new Error("fill evaluation cannot precede decisionAt");
  const visible = causalEvents(intent, events, evaluatedAt);
  const eligibleMs = Date.parse(intent.fillEligibleAt);
  const expiresMs = Date.parse(intent.expiresAt);
  const terminal = Date.parse(evaluatedAt) >= expiresMs;
  const eligible = visible.filter((event) => Date.parse(event.capturedAt) >= eligibleMs);
  if (!eligible.length) {
    return fillResult(intent, {
      status: PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY,
      reason: terminal ? "NO_CAUSAL_SOURCE_EVIDENCE_WITHIN_TTL" : "CAUSAL_SOURCE_EVIDENCE_NOT_READY",
      evaluatedAt,
    });
  }

  if (intent.orderStyleResearchLabel === PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE) {
    const first = eligible.find((event) => event.quoteSourceReady);
    if (!first) {
      return fillResult(intent, {
        status: PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY,
        reason: eligible.flatMap((event) => event.blockers)[0] ?? "TOP_OF_BOOK_NOT_READY",
        evaluatedAt,
        evidence: eligible.map((event) => ({ eventId: event.eventId, observedAt: event.capturedAt })),
      });
    }
    const quotePrice = intent.side === "BUY" ? first.bestAsk : first.bestBid;
    const quoteSize = intent.side === "BUY" ? first.askSize : first.bidSize;
    const filledQuantity = Math.floor(Math.min(intent.requestedQuantity, quoteSize) / LOT_SIZE) * LOT_SIZE;
    if (filledQuantity < LOT_SIZE) {
      return fillResult(intent, {
        status: terminal ? PHASE57_MSII_FILL_STATUS.EXPIRED : PHASE57_MSII_FILL_STATUS.NO_FILL,
        reason: "OBSERVED_TOP_OF_BOOK_BELOW_ONE_FROZEN_LOT",
        evaluatedAt,
        evidence: [{ eventId: first.eventId, observedAt: first.capturedAt, price: quotePrice, size: quoteSize }],
      });
    }
    return fillResult(intent, {
      status: filledQuantity === intent.requestedQuantity ? PHASE57_MSII_FILL_STATUS.FILLED : PHASE57_MSII_FILL_STATUS.PARTIAL,
      reason: "FIRST_CAUSAL_MARKETABLE_QUOTE",
      evaluatedAt,
      filledQuantity,
      fillPrice: quotePrice,
      firstFillAt: first.capturedAt,
      lastFillAt: first.capturedAt,
      evidence: [{ eventId: first.eventId, observedAt: first.capturedAt, price: quotePrice, size: quoteSize }],
    });
  }

  const tickEvents = eligible.filter((event) => event.tickSourceReady);
  if (!tickEvents.length) {
    return fillResult(intent, {
      status: PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY,
      reason: "CAUSAL_TICK_SOURCE_NOT_READY",
      evaluatedAt,
      evidence: eligible.map((event) => ({ eventId: event.eventId, observedAt: event.capturedAt })),
    });
  }
  const uniqueTicks = new Map();
  for (const event of tickEvents) {
    for (const tick of event.ticks) {
      const tickMs = Date.parse(tick.timestamp);
      if (tickMs <= Date.parse(intent.decisionAt) || tickMs < eligibleMs || tickMs > expiresMs || tickMs > Date.parse(evaluatedAt)) continue;
      const key = `${tick.timestamp}|${tick.price}|${tick.size}`;
      if (!uniqueTicks.has(key)) uniqueTicks.set(key, { ...tick, eventId: event.eventId });
    }
  }
  const qualifying = [...uniqueTicks.values()].filter((tick) => intent.side === "BUY"
    ? tick.price <= intent.referencePrice
    : tick.price >= intent.referencePrice)
    .sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp) || left.eventId.localeCompare(right.eventId));
  if (!qualifying.length) {
    return fillResult(intent, {
      status: terminal ? PHASE57_MSII_FILL_STATUS.EXPIRED : PHASE57_MSII_FILL_STATUS.NO_FILL,
      reason: terminal ? "PASSIVE_TTL_EXPIRED_WITHOUT_OBSERVED_CROSS" : "NO_OBSERVED_PASSIVE_CROSS_YET",
      evaluatedAt,
      evidence: tickEvents.map((event) => ({ eventId: event.eventId, observedAt: event.capturedAt })),
    });
  }
  let remaining = intent.requestedQuantity;
  let filledQuantity = 0;
  let notional = 0;
  const used = [];
  for (const tick of qualifying) {
    const available = Math.floor(Number(tick.size) / LOT_SIZE) * LOT_SIZE;
    const take = Math.min(remaining, available);
    if (take <= 0) continue;
    filledQuantity += take;
    remaining -= take;
    notional += take * Number(tick.price);
    used.push({ eventId: tick.eventId, observedAt: tick.timestamp, price: tick.price, size: tick.size, usedQuantity: take });
    if (remaining === 0) break;
  }
  if (filledQuantity < LOT_SIZE) {
    return fillResult(intent, {
      status: terminal ? PHASE57_MSII_FILL_STATUS.EXPIRED : PHASE57_MSII_FILL_STATUS.NO_FILL,
      reason: "OBSERVED_PASSIVE_VOLUME_BELOW_ONE_FROZEN_LOT",
      evaluatedAt,
      evidence: used,
    });
  }
  return fillResult(intent, {
    status: filledQuantity === intent.requestedQuantity ? PHASE57_MSII_FILL_STATUS.FILLED : PHASE57_MSII_FILL_STATUS.PARTIAL,
    reason: "OBSERVED_POST_DECISION_PASSIVE_TICKS",
    evaluatedAt,
    filledQuantity,
    fillPrice: notional / filledQuantity,
    firstFillAt: used[0].observedAt,
    lastFillAt: used.at(-1).observedAt,
    evidence: used,
  });
}

export function classifyMsiiSession({ predeclaredStartAt, actualStartAt, missingCaptureCount = 0, backfillUsed = false } = {}) {
  if (!actualStartAt) return PHASE57_MSII_SESSION_QUALITY.SOURCE_NOT_READY;
  const declared = timestamp(predeclaredStartAt, "predeclaredStartAt");
  const actual = timestamp(actualStartAt, "actualStartAt");
  return Date.parse(actual) === Date.parse(declared) && Number(missingCaptureCount) === 0 && backfillUsed === false
    ? PHASE57_MSII_SESSION_QUALITY.FULL_FRESH_MSII
    : PHASE57_MSII_SESSION_QUALITY.PARTIAL_INCOMPLETE_MSII;
}

export function createMsiiShadowExecutionState({
  sessionDate,
  predeclaredStartAt,
  actualStartAt = null,
  missingCaptureCount = 0,
  backfillUsed = false,
  initialCapital = 1_000_000,
} = {}) {
  assertModuleSafety();
  const date = requiredText(sessionDate, "sessionDate");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error("sessionDate must be YYYY-MM-DD");
  const capital = Number(initialCapital);
  if (!Number.isFinite(capital) || capital <= 0) throw new Error("initialCapital must be positive");
  const quality = classifyMsiiSession({ predeclaredStartAt, actualStartAt, missingCaptureCount, backfillUsed });
  return {
    version: PHASE57_MSII_SHADOW_VERSION,
    sessionDate: date,
    sessionQuality: quality,
    predeclaredStartAt: timestamp(predeclaredStartAt, "predeclaredStartAt"),
    actualStartAt: actualStartAt ? timestamp(actualStartAt, "actualStartAt") : null,
    missingCaptureCount: Math.max(0, Number(missingCaptureCount) || 0),
    backfillUsed: backfillUsed === true,
    initialCapital: capital,
    strategyIds: STRATEGY_IDS,
    ledger: [],
    ledgerHeadHash: GENESIS_HASH,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
}

export function appendMsiiShadowLedgerEvent(state, event) {
  assertModuleSafety();
  if (!state?.ledger || state.safety !== PHASE57_MSII_SHADOW_SAFETY) throw new Error("Lane M Shadow state required");
  const eventId = requiredText(event?.eventId, "eventId");
  const eventType = requiredText(event?.eventType, "eventType");
  const eventAt = timestamp(event?.eventAt, "eventAt");
  if (jstSessionDate(eventAt) !== state.sessionDate) throw new Error("ledger event is outside Lane M sessionDate");
  const payload = {
    ...event,
    eventId,
    eventType,
    eventAt,
    sessionDate: state.sessionDate,
    sessionQuality: state.sessionQuality,
    initialCapital: state.initialCapital,
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  const eventFingerprint = sha256(payload);
  const prior = state.ledger.find((row) => row.eventId === eventId);
  if (prior) {
    if (prior.eventFingerprint !== eventFingerprint) throw new Error(`Lane M ledger EVENT_ID_CONFLICT:${eventId}`);
    return prior;
  }
  const previous = state.ledger.at(-1);
  if (previous && Date.parse(eventAt) < Date.parse(previous.eventAt)) throw new Error("Lane M ledger timestamp cannot move backward");
  const core = {
    ...payload,
    eventFingerprint,
    sequence: state.ledger.length,
    previousHash: previous?.eventHash ?? GENESIS_HASH,
  };
  const committed = deepFreeze({ ...core, eventHash: sha256(core) });
  state.ledger.push(committed);
  state.ledgerHeadHash = committed.eventHash;
  return committed;
}

/** Anchor each read-only observation before it can support an intent or fill. */
export function commitNormalizedMarketEvent(state, marketEvent) {
  assertNormalizedEvent(marketEvent);
  if (marketEvent.sessionDate !== state.sessionDate) throw new Error("MarketSpeed event session mismatch");
  return appendMsiiShadowLedgerEvent(state, {
    eventId: `MARKET_COMMIT|${marketEvent.sessionDate}|${marketEvent.capturedAt}|${marketEvent.symbol}`,
    eventType: "MSII_MARKET_EVENT_COMMITTED",
    eventAt: marketEvent.capturedAt,
    marketEvent,
  });
}

export function commitShadowOrderIntent(state, intent) {
  assertIntent(intent);
  if (jstSessionDate(intent.decisionAt) !== state.sessionDate) throw new Error("intent session mismatch");
  const sourceEvent = state.ledger.find((row) => row.eventType === "MSII_MARKET_EVENT_COMMITTED"
    && row.marketEvent?.eventId === intent.sourceEventId);
  if (!sourceEvent || sourceEvent.marketEvent.normalizedEventSha256 !== intent.sourceNormalizedEventSha256
    || sourceEvent.marketEvent.sourceSnapshotHash !== intent.sourceSnapshotHash) {
    throw new Error("ShadowOrderIntent source observation is not committed to the Lane M ledger");
  }
  return appendMsiiShadowLedgerEvent(state, {
    eventId: `INTENT_COMMIT|${intent.intentId}`,
    eventType: "SHADOW_ORDER_INTENT_COMMITTED",
    eventAt: intent.decisionAt,
    intent,
  });
}

function assertFill(fill) {
  if (fill?.type !== "SHADOW_FILL" || !Object.values(PHASE57_MSII_FILL_STATUS).includes(fill?.status)) throw new Error("valid ShadowFill required");
  assertSafetyMap(fill.safety, "fill safety");
  if (fill.futureOutcomeUsed !== false || fill.transmitted !== false || fill.executable !== false) throw new Error("fill is not Shadow-only");
  const { fillSha256, ...core } = fill;
  if (fillSha256 !== sha256(core)) throw new Error("ShadowFill hash mismatch");
}

export function commitShadowFill(state, fill) {
  assertFill(fill);
  const intentEvent = state.ledger.find((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED" && row.intent?.intentId === fill.intentId);
  if (!intentEvent) throw new Error("ShadowFill references an uncommitted intent");
  for (const evidence of fill.evidence) {
    const sourceEvent = state.ledger.find((row) => row.eventType === "MSII_MARKET_EVENT_COMMITTED"
      && row.marketEvent?.eventId === evidence.eventId);
    if (!sourceEvent) throw new Error(`ShadowFill evidence is not committed to the Lane M ledger: ${evidence.eventId}`);
    if (Date.parse(sourceEvent.eventAt) <= Date.parse(intentEvent.intent.decisionAt)
      || Date.parse(sourceEvent.eventAt) > Date.parse(fill.sourceObservationCutoff)) {
      throw new Error("ShadowFill evidence violates its causal observation window");
    }
  }
  return appendMsiiShadowLedgerEvent(state, {
    eventId: `FILL_COMMIT|${fill.fillId}`,
    eventType: "SHADOW_FILL_COMMITTED",
    eventAt: fill.evaluatedAt,
    fill,
  });
}

export function buildExecutionAwareClosedTrade({ entryIntent, entryFill, exitIntent, exitFill, transactionCostJpy = 0 } = {}) {
  assertIntent(entryIntent);
  assertIntent(exitIntent);
  assertFill(entryFill);
  assertFill(exitFill);
  if (entryIntent.intentKind !== "ENTRY" || exitIntent.intentKind !== "EXIT") throw new Error("execution trade requires ENTRY then EXIT intents");
  if (entryIntent.strategyId !== exitIntent.strategyId || entryIntent.symbol !== exitIntent.symbol) throw new Error("execution trade lineage mismatch");
  if (entryIntent.side === exitIntent.side) throw new Error("execution trade EXIT side must oppose ENTRY side");
  if (entryFill.intentId !== entryIntent.intentId || exitFill.intentId !== exitIntent.intentId) throw new Error("execution trade fill/intent lineage mismatch");
  if (Date.parse(exitIntent.decisionAt) <= Date.parse(entryIntent.decisionAt)) throw new Error("execution trade EXIT decision must follow ENTRY decision");
  if (Date.parse(exitFill.lastFillAt) <= Date.parse(entryFill.firstFillAt)) throw new Error("execution trade EXIT fill must follow ENTRY fill");
  const quantity = Math.min(Number(entryFill.filledQuantity), Number(exitFill.filledQuantity));
  if (!(quantity > 0) || !finite(entryFill.fillPrice) || !finite(exitFill.fillPrice)) throw new Error("execution trade requires observed filled quantity and prices");
  const fees = Number(transactionCostJpy);
  if (!Number.isFinite(fees) || fees < 0) throw new Error("transactionCostJpy must be non-negative");
  const direction = entryIntent.side === "BUY" ? 1 : -1;
  const referenceGrossPnlJpy = direction * (Number(exitIntent.referencePrice) - Number(entryIntent.referencePrice)) * quantity;
  const executionGrossPnlJpy = direction * (Number(exitFill.fillPrice) - Number(entryFill.fillPrice)) * quantity;
  const trade = {
    schemaVersion: 1,
    version: PHASE57_MSII_SHADOW_VERSION,
    type: "SHADOW_EXECUTION_CLOSED_TRADE",
    tradeId: `MSII_TRADE|${entryIntent.strategyId}|${entryIntent.symbol}|${entryIntent.intentId}|${exitIntent.intentId}`,
    strategyId: entryIntent.strategyId,
    matrixCell: entryIntent.matrixCell,
    allocationProfile: entryIntent.allocationProfile,
    symbol: entryIntent.symbol,
    direction,
    entryIntentId: entryIntent.intentId,
    exitIntentId: exitIntent.intentId,
    entryFillId: entryFill.fillId,
    exitFillId: exitFill.fillId,
    entryAt: entryFill.firstFillAt,
    exitAt: exitFill.lastFillAt,
    quantity,
    entryReferencePrice: entryIntent.referencePrice,
    exitReferencePrice: exitIntent.referencePrice,
    entryFillPrice: entryFill.fillPrice,
    exitFillPrice: exitFill.fillPrice,
    referenceGrossPnlJpy,
    executionGrossPnlJpy,
    transactionCostJpy: fees,
    netPnlJpy: executionGrossPnlJpy - fees,
    spreadCostJpy: Number(entryFill.spreadCostJpy) + Number(exitFill.spreadCostJpy),
    slippageJpy: Number(entryFill.slippageJpy) + Number(exitFill.slippageJpy),
    futureOutcomeUsed: false,
    transmitted: false,
    executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  return deepFreeze({ ...trade, tradeSha256: sha256(trade) });
}

export function commitExecutionAwareClosedTrade(state, trade) {
  if (trade?.type !== "SHADOW_EXECUTION_CLOSED_TRADE") throw new Error("valid execution-aware closed trade required");
  const { tradeSha256, ...core } = trade;
  if (tradeSha256 !== sha256(core)) throw new Error("execution-aware trade hash mismatch");
  const exitFillEvent = state.ledger.find((row) => row.eventType === "SHADOW_FILL_COMMITTED" && row.fill?.fillId === trade.exitFillId);
  if (!exitFillEvent) throw new Error("execution-aware trade references an uncommitted EXIT fill");
  return appendMsiiShadowLedgerEvent(state, {
    eventId: `TRADE_COMMIT|${trade.tradeId}`,
    eventType: "SHADOW_EXECUTION_TRADE_CLOSED",
    eventAt: exitFillEvent.eventAt,
    trade,
  });
}

export function verifyMsiiShadowLedger(ledger, { sessionDate = null } = {}) {
  assertModuleSafety();
  if (!Array.isArray(ledger)) throw new Error("Lane M ledger must be an array");
  const ids = new Set();
  let previousHash = GENESIS_HASH;
  let previousAt = null;
  for (let index = 0; index < ledger.length; index += 1) {
    const row = ledger[index];
    if (row.sequence !== index) throw new Error(`Lane M ledger sequence mismatch at ${index}`);
    if (ids.has(row.eventId)) throw new Error(`Lane M ledger duplicate eventId at ${index}`);
    ids.add(row.eventId);
    if (sessionDate && row.sessionDate !== sessionDate) throw new Error(`Lane M ledger session mismatch at ${index}`);
    if (previousAt && Date.parse(row.eventAt) < Date.parse(previousAt)) throw new Error(`Lane M ledger timestamp moved backward at ${index}`);
    if (row.previousHash !== previousHash) throw new Error(`Lane M ledger previousHash mismatch at ${index}`);
    assertSafetyMap(row.safety, `ledger[${index}].safety`);
    if (row.futureOutcomeUsed !== false || row.transmitted !== false || row.executable !== false) throw new Error(`Lane M ledger safety payload mismatch at ${index}`);
    const { eventHash, ...core } = row;
    if (eventHash !== sha256(core)) throw new Error(`Lane M ledger eventHash mismatch at ${index}`);
    const { eventFingerprint, sequence, previousHash: ignoredPreviousHash, ...payload } = core;
    void sequence;
    void ignoredPreviousHash;
    if (eventFingerprint !== sha256(payload)) throw new Error(`Lane M ledger eventFingerprint mismatch at ${index}`);
    previousHash = eventHash;
    previousAt = row.eventAt;
  }
  return Object.freeze({ valid: true, eventCount: ledger.length, headHash: previousHash });
}

function latestFills(ledger) {
  const byIntent = new Map();
  for (const event of ledger.filter((row) => row.eventType === "SHADOW_FILL_COMMITTED")) {
    const prior = byIntent.get(event.fill.intentId);
    if (!prior || event.sequence > prior.sequence) byIntent.set(event.fill.intentId, event);
  }
  return byIntent;
}

function strategyExecutionSnapshot(strategyId, intents, fillsByIntent, trades, initialCapital) {
  const strategyIntents = intents.filter((intent) => intent.strategyId === strategyId);
  const latest = strategyIntents.map((intent) => fillsByIntent.get(intent.intentId)?.fill).filter(Boolean);
  const strategyTrades = trades.filter((trade) => trade.strategyId === strategyId);
  const pnl = strategyTrades.map((trade) => Number(trade.netPnlJpy));
  const grossProfit = pnl.filter((value) => value > 0).reduce((sum, value) => sum + value, 0);
  const grossLoss = -pnl.filter((value) => value < 0).reduce((sum, value) => sum + value, 0);
  let equity = initialCapital;
  let peak = initialCapital;
  let maxDrawdownPercent = 0;
  for (const value of pnl) {
    equity += value;
    peak = Math.max(peak, equity);
    if (peak > 0) maxDrawdownPercent = Math.max(maxDrawdownPercent, ((peak - equity) / peak) * 100);
  }
  const openBySymbol = new Map();
  for (const intent of strategyIntents.slice().sort((left, right) => left.decisionSequence - right.decisionSequence)) {
    const fill = fillsByIntent.get(intent.intentId)?.fill;
    if (!fill || !(fill.filledQuantity > 0)) continue;
    const delta = intent.intentKind === "ENTRY" ? fill.filledQuantity : -fill.filledQuantity;
    openBySymbol.set(intent.symbol, Math.max(0, (openBySymbol.get(intent.symbol) ?? 0) + delta));
  }
  const statusCount = Object.fromEntries(Object.values(PHASE57_MSII_FILL_STATUS).map((status) => [status, latest.filter((fill) => fill.status === status).length]));
  return Object.freeze({
    strategyId,
    intentCount: strategyIntents.length,
    ...statusCount,
    fillRatePercent: strategyIntents.length ? ((statusCount.FILLED + statusCount.PARTIAL) / strategyIntents.length) * 100 : null,
    partialFillRatePercent: strategyIntents.length ? (statusCount.PARTIAL / strategyIntents.length) * 100 : null,
    noFillRatePercent: strategyIntents.length ? (statusCount.NO_FILL / strategyIntents.length) * 100 : null,
    closedTrades: strategyTrades.length,
    wins: pnl.filter((value) => value > 0).length,
    winRate: pnl.length ? (pnl.filter((value) => value > 0).length / pnl.length) * 100 : null,
    realizedPnl: pnl.reduce((sum, value) => sum + value, 0),
    netPercent: ((equity / initialCapital) - 1) * 100,
    equity,
    grossProfit,
    grossLoss,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : (grossProfit > 0 ? Infinity : null),
    peakEquity: peak,
    maxDrawdownPercent,
    openPositions: [...openBySymbol.values()].filter((quantity) => quantity > 0).length,
  });
}

/** Ledger-read-only scoring. It never recreates Selection, Entry, EXIT, or Allocation decisions. */
export function scoreMsiiShadowExecutionLedger(ledger, { sessionDate = null } = {}) {
  const verified = verifyMsiiShadowLedger(ledger, { sessionDate });
  const intents = ledger.filter((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED").map((row) => row.intent);
  const fillsByIntent = latestFills(ledger);
  const fills = [...fillsByIntent.values()].map((row) => row.fill);
  const trades = ledger.filter((row) => row.eventType === "SHADOW_EXECUTION_TRADE_CLOSED").map((row) => row.trade);
  const initialCapital = Number(ledger[0]?.initialCapital ?? 1_000_000);
  const statuses = Object.fromEntries(Object.values(PHASE57_MSII_FILL_STATUS).map((status) => [status, fills.filter((fill) => fill.status === status).length]));
  const filled = fills.filter((fill) => fill.filledQuantity > 0);
  const latencies = filled.map((fill) => fill.decisionToFirstFillLatencyMs).filter(finite).map(Number);
  const strategies = Object.freeze(STRATEGY_IDS.map((strategyId) => strategyExecutionSnapshot(strategyId, intents, fillsByIntent, trades, initialCapital)));
  const totalNetPnl = trades.reduce((sum, trade) => sum + Number(trade.netPnlJpy), 0);
  return deepFreeze({
    schemaVersion: 1,
    version: PHASE57_MSII_SHADOW_VERSION,
    status: "PHASE57_MSII_SHADOW_EXECUTION_SCORED",
    sessionDate: sessionDate ?? ledger.at(-1)?.sessionDate ?? null,
    sessionQuality: ledger.at(-1)?.sessionQuality ?? PHASE57_MSII_SESSION_QUALITY.SOURCE_NOT_READY,
    ledgerEventCount: verified.eventCount,
    ledgerHeadHash: verified.headHash,
    strategyCount: STRATEGY_IDS.length,
    decisionCount: intents.length,
    intentCount: intents.length,
    fillAssessmentCount: fills.length,
    statusCounts: statuses,
    fillRatePercent: intents.length ? ((statuses.FILLED + statuses.PARTIAL) / intents.length) * 100 : null,
    noFillRatePercent: intents.length ? (statuses.NO_FILL / intents.length) * 100 : null,
    partialFillRatePercent: intents.length ? (statuses.PARTIAL / intents.length) * 100 : null,
    expiredRatePercent: intents.length ? (statuses.EXPIRED / intents.length) * 100 : null,
    sourceNotReadyRatePercent: intents.length ? (statuses.SOURCE_NOT_READY / intents.length) * 100 : null,
    averageDecisionToFillLatencyMs: latencies.length ? latencies.reduce((sum, value) => sum + value, 0) / latencies.length : null,
    spreadCostJpy: filled.reduce((sum, fill) => sum + Number(fill.spreadCostJpy), 0),
    slippageJpy: filled.reduce((sum, fill) => sum + Number(fill.slippageJpy), 0),
    closedTrades: trades.length,
    grossExecutionPnlJpy: trades.reduce((sum, trade) => sum + Number(trade.executionGrossPnlJpy), 0),
    netPnlJpy: totalNetPnl,
    netReturnPercent: initialCapital > 0 ? (totalNetPnl / (initialCapital * STRATEGY_IDS.length)) * 100 : null,
    strategies,
    postCloseDecisionRecomputationAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  });
}

function pairedKey(row) {
  return [row.strategyId, normalizeSymbol(row.symbol), timestamp(row.decisionAt ?? row.at, "paired decisionAt"), String(row.intentKind ?? "ENTRY").toUpperCase()].join("|");
}

export function compareLaneYWithMsii({ laneYDecisions = [], msiiLedger = [] } = {}) {
  verifyMsiiShadowLedger(msiiLedger);
  const intentEvents = msiiLedger.filter((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED");
  const fillByIntent = latestFills(msiiLedger);
  const laneMByKey = new Map(intentEvents.map((event) => [pairedKey(event.intent), event.intent]));
  const pairs = [];
  const unmatchedLaneY = [];
  for (const row of laneYDecisions) {
    const key = pairedKey(row);
    const intent = laneMByKey.get(key);
    if (!intent) {
      unmatchedLaneY.push(key);
      continue;
    }
    const fill = fillByIntent.get(intent.intentId)?.fill ?? null;
    pairs.push(Object.freeze({
      key,
      strategyId: intent.strategyId,
      symbol: intent.symbol,
      decisionAt: intent.decisionAt,
      intentKind: intent.intentKind,
      laneYReferencePrice: numberOrNull(row.referencePrice ?? row.entryPrice ?? row.exitPrice),
      laneMReferencePrice: intent.referencePrice,
      laneMFillStatus: fill?.status ?? PHASE57_MSII_FILL_STATUS.SOURCE_NOT_READY,
      laneMFillPrice: fill?.fillPrice ?? null,
      decisionToFillLatencyMs: fill?.decisionToFirstFillLatencyMs ?? null,
    }));
    laneMByKey.delete(key);
  }
  return deepFreeze({
    status: "LANE_Y_MSII_PAIRED_COMPARISON_READY",
    exactIdentityTimestampJoin: true,
    pairCount: pairs.length,
    unmatchedLaneYCount: unmatchedLaneY.length,
    unmatchedLaneMCount: laneMByKey.size,
    pairs,
    unmatchedLaneY,
    futureOutcomeUsed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  });
}

export default {
  normalizeMarketSpeedReadOnlyEvent,
  createShadowOrderIntent,
  buildEntryShadowOrderIntentsFromPhase57,
  evaluateShadowFill,
  classifyMsiiSession,
  createMsiiShadowExecutionState,
  appendMsiiShadowLedgerEvent,
  commitNormalizedMarketEvent,
  commitShadowOrderIntent,
  commitShadowFill,
  buildExecutionAwareClosedTrade,
  commitExecutionAwareClosedTrade,
  verifyMsiiShadowLedger,
  scoreMsiiShadowExecutionLedger,
  compareLaneYWithMsii,
};
