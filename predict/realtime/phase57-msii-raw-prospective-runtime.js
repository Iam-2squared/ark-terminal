import { createHash } from "node:crypto";
import {
  PHASE57_MSII_FILL_STATUS,
  PHASE57_MSII_ORDER_STYLE,
  PHASE57_MSII_SHADOW_SAFETY,
  buildEntryShadowOrderIntentsFromPhase57,
  buildExecutionAwareClosedTrade,
  commitExecutionAwareClosedTrade,
  commitNormalizedMarketEvent,
  commitShadowFill,
  commitShadowOrderIntent,
  compareLaneYWithMsii,
  createMsiiShadowExecutionState,
  evaluateShadowFill,
  scoreMsiiShadowExecutionLedger,
  verifyMsiiShadowLedger,
} from "./phase57-msii-shadow-execution.js";
import { buildExitShadowOrderIntentsFromPhase57 } from "./phase57-msii-shadow-runtime.js";

export const PHASE57_MSII_RAW_RUNTIME_VERSION = "phase57-msii-raw-prospective-runtime-r1";
const FALSE_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);
const FORBIDDEN = Object.freeze([
  "RSSSTOCKORDER", "RSSMARGINOPENORDER", "RSSMARGINCLOSEORDER", "RSSMODIFYORDER", "RSSCANCELORDER",
  "RSSFUTUREORDER", "RSSOPTIONORDER", "RSSFOP",
]);

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
}
function sha256(value) { return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex"); }
function ms(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a valid absolute timestamp`);
  return parsed;
}
function iso(value, label = "timestamp") { return new Date(ms(value, label)).toISOString(); }
function jstSessionDate(value) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" })
    .formatToParts(new Date(iso(value)));
  const fields = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${fields.year}-${fields.month}-${fields.day}`;
}
function normalizeSymbol(value) {
  const raw = String(value ?? "").trim().toUpperCase();
  if (!raw) throw new Error("symbol required");
  if (/^\d+(?:\.0+)?$/.test(raw)) return `${String(Math.trunc(Number(raw)))}.T`;
  return raw;
}
function finite(value) { return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value)); }
function numberOrNull(value) { return finite(value) ? Number(value) : null; }
function assertSafety(value, label) {
  if (!value || typeof value !== "object") throw new Error(`${label} safety contract required`);
  for (const key of FALSE_KEYS) if (value[key] !== false) throw new Error(`${label}.${key} must remain false`);
  if (value.transmitted !== undefined && value.transmitted !== false) throw new Error(`${label}.transmitted must remain false`);
}
function normalizeTickTime(value, sessionDate, capturedAt) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  if (/^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?$/.test(raw)) {
    const [clock, fraction = ""] = raw.split(".");
    const [hour, minute, second] = clock.split(":").map(Number);
    if (hour > 23 || minute > 59 || second > 59) return null;
    const hms = `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}${fraction ? `.${fraction}` : ""}`;
    const out = iso(`${sessionDate}T${hms}+09:00`, "tick time");
    return ms(out) <= ms(capturedAt) ? out : null;
  }
  const out = iso(raw, "tick time");
  return jstSessionDate(out) === sessionDate && ms(out) <= ms(capturedAt) ? out : null;
}

/** Convert a raw, prospectively captured multi-symbol RSS row into the same immutable market-event contract used by Lane M.
 * No Phase57 decision fields are attached to pre-decision evidence; the decision lineage remains solely in the later intent.
 */
export function normalizeRawProspectiveMsiiEvent(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error("raw MarketSpeed capture row required");
  if (row.schemaVersion !== 1 || row.phase !== "58.p31.multi-symbol-capture") throw new Error("raw Lane M capture must be Phase58 p31 schemaVersion 1");
  if (row.sourceMode !== "MARKETSPEED_II_RSS_READ_ONLY") throw new Error("raw Lane M sourceMode must be MARKETSPEED_II_RSS_READ_ONLY");
  assertSafety(row.safety, "capture.safety");
  if (row.methodology?.pointInTimeOnly !== true || row.methodology?.futureOutcomeUsed !== false) throw new Error("raw Lane M capture must be prospective and outcome-free");
  if (row.methodology?.excelFormulaWritePerformed !== false || row.methodology?.symbolSwitchWritePerformed !== false) throw new Error("raw Lane M capture must come from preconfigured read-only sheets");
  if (row.marketSizeUnit !== "SHARES" || row.tickSizeUnit !== "SHARES") throw new Error("raw Lane M size units must be explicitly SHARES");
  const functions = Array.isArray(row.sourceFunctions) ? row.sourceFunctions.map((v) => String(v).trim()).filter(Boolean) : [];
  const forbidden = functions.find((name) => FORBIDDEN.some((token) => name.toUpperCase().includes(token)));
  if (forbidden) throw new Error(`forbidden RSS order function in raw capture provenance: ${forbidden}`);

  const capturedAt = iso(row.capturedAt, "capturedAt");
  const sessionDate = jstSessionDate(capturedAt);
  const symbol = normalizeSymbol(row.symbol);
  const market = row.market && typeof row.market === "object" ? row.market : {};
  const bestBid = numberOrNull(market.bestBid ?? market.bid);
  const bestAsk = numberOrNull(market.bestAsk ?? market.ask);
  const bidSize = numberOrNull(market.bestBidSize ?? market.bidSize ?? market.bidSize1);
  const askSize = numberOrNull(market.bestAskSize ?? market.askSize ?? market.askSize1);
  if (bestBid !== null && bestAsk !== null && bestAsk < bestBid) throw new Error("crossed raw MarketSpeed quote rejected");
  const blockers = [];
  if (!(bestBid > 0) || !(bestAsk > 0)) blockers.push("TOP_OF_BOOK_NOT_READY");
  if (!(bidSize >= 0) || !(askSize >= 0)) blockers.push("TOP_OF_BOOK_SIZE_NOT_READY");
  const ticks = [];
  for (let index = 0; index < (Array.isArray(row.ticks) ? row.ticks.length : 0); index += 1) {
    const raw = row.ticks[index] ?? {};
    const timestamp = normalizeTickTime(raw.timestamp ?? raw.time, sessionDate, capturedAt);
    const price = numberOrNull(raw.price ?? raw.executionPrice);
    const size = numberOrNull(raw.size ?? raw.volume);
    if (!timestamp || !(price > 0) || !(size >= 0)) { blockers.push(`INVALID_TICK_${index}`); continue; }
    ticks.push({ timestamp, price, size, sourceIndex: index });
  }
  ticks.sort((a, b) => ms(a.timestamp) - ms(b.timestamp) || a.sourceIndex - b.sourceIndex);
  const sourceSnapshotHash = sha256(row);
  const midpoint = bestBid > 0 && bestAsk > 0 ? (bestBid + bestAsk) / 2 : null;
  const event = {
    schemaVersion: 1,
    version: PHASE57_MSII_RAW_RUNTIME_VERSION,
    type: "MSII_NORMALIZED_MARKET_EVENT",
    eventId: `MSII_RAW_MARKET|${sessionDate}|${capturedAt}|${symbol}|${sourceSnapshotHash.slice(0, 16)}`,
    symbol, sessionDate, capturedAt, quoteObservedAt: capturedAt,
    bestBid, bestAsk, bidSize, askSize, midpoint,
    referenceSpread: midpoint === null ? null : bestAsk - bestBid,
    lastPrice: ticks.at(-1)?.price ?? null,
    ticks,
    marketSizeUnit: "SHARES", tickSizeUnit: "SHARES",
    quoteSourceReady: bestBid > 0 && bestAsk > 0 && bidSize >= 0 && askSize >= 0,
    tickSourceReady: ticks.length > 0,
    blockers: [...new Set(blockers)],
    sourceSnapshotHash,
    sourceMode: "MARKETSPEED_II_RSS_READ_ONLY",
    sourceFunctions: functions.length ? functions : ["RssMarket", "RssTickList"],
    phase57SnapshotHash: null,
    selectorDirection: null,
    rawProspectiveCapture: true,
    futureOutcomeUsed: false, transmitted: false, executable: false,
    safety: PHASE57_MSII_SHADOW_SAFETY,
  };
  return Object.freeze({ ...event, normalizedEventSha256: sha256(event) });
}

function committedMarketEvents(ledger) { return ledger.filter((row) => row.eventType === "MSII_MARKET_EVENT_COMMITTED").map((row) => row.marketEvent); }
function committedIntents(ledger) { return ledger.filter((row) => row.eventType === "SHADOW_ORDER_INTENT_COMMITTED").map((row) => row.intent).sort((a,b)=>a.decisionSequence-b.decisionSequence||a.intentId.localeCompare(b.intentId)); }
function latestFills(ledger) {
  const out = new Map();
  for (const row of ledger.filter((x) => x.eventType === "SHADOW_FILL_COMMITTED")) {
    const prior = out.get(row.fill.intentId); if (!prior || row.sequence > prior.sequence) out.set(row.fill.intentId, row.fill);
  }
  return out;
}
function nextSequence(ledger) { return committedIntents(ledger).reduce((m, x) => Math.max(m, Number(x.decisionSequence) || 0), -1) + 1; }
function latestReferences(events, decisionAt, maxAgeMs) {
  const cutoff = ms(decisionAt); const out = new Map();
  for (const event of events) {
    const t = ms(event.capturedAt); if (t > cutoff || cutoff - t > maxAgeMs) continue;
    const prior = out.get(event.symbol); if (!prior || t > ms(prior.capturedAt)) out.set(event.symbol, event);
  }
  return out;
}
function inventory(ledger) {
  const fills = latestFills(ledger); const out = new Map();
  for (const intent of committedIntents(ledger)) {
    const qty = Number(fills.get(intent.intentId)?.filledQuantity ?? 0); if (!(qty > 0)) continue;
    const key = `${intent.strategyId}|${normalizeSymbol(intent.symbol)}`; const prior = Number(out.get(key) ?? 0);
    out.set(key, intent.intentKind === "ENTRY" ? prior + qty : Math.max(0, prior - qty));
  }
  return out;
}
function capClosed(ledger, closed = []) {
  const open = inventory(ledger);
  return closed.map((position) => {
    const available = Number(open.get(`${position.strategyId}|${normalizeSymbol(position.symbol)}`) ?? 0);
    const quantity = Math.min(available, Number(position.quantity ?? 0));
    return quantity > 0 ? Object.freeze({ ...position, quantity }) : null;
  }).filter(Boolean);
}
function appendNewMarketEvents(state, events, predicate) {
  const seen = new Set(committedMarketEvents(state.ledger).map((x) => x.eventId));
  const rows = events.filter((x) => !seen.has(x.eventId) && predicate(x)).sort((a,b)=>ms(a.capturedAt)-ms(b.capturedAt)||a.symbol.localeCompare(b.symbol)||a.eventId.localeCompare(b.eventId));
  for (const row of rows) commitNormalizedMarketEvent(state, row);
}
function commitTrades(state, transactionCostJpy) {
  const fills = latestFills(state.ledger);
  const prior = state.ledger.filter((x)=>x.eventType==="SHADOW_EXECUTION_TRADE_CLOSED").map((x)=>x.trade);
  const usedExit = new Set(prior.map((x)=>x.exitIntentId)); const usedEntry = new Set(prior.map((x)=>x.entryIntentId));
  let count = 0;
  for (const exitIntent of committedIntents(state.ledger).filter((x)=>x.intentKind==="EXIT")) {
    if (usedExit.has(exitIntent.intentId)) continue;
    const exitFill = fills.get(exitIntent.intentId); if (!(Number(exitFill?.filledQuantity)>0)) continue;
    const entryIntent = committedIntents(state.ledger).filter((x)=>x.intentKind==="ENTRY"&&x.strategyId===exitIntent.strategyId&&x.symbol===exitIntent.symbol&&ms(x.decisionAt)<ms(exitIntent.decisionAt)&&Number(fills.get(x.intentId)?.filledQuantity??0)>0&&!usedEntry.has(x.intentId)).sort((a,b)=>ms(b.decisionAt)-ms(a.decisionAt))[0];
    if (!entryIntent) continue;
    const trade = buildExecutionAwareClosedTrade({ entryIntent, entryFill: fills.get(entryIntent.intentId), exitIntent, exitFill, transactionCostJpy });
    commitExecutionAwareClosedTrade(state, trade); usedExit.add(exitIntent.intentId); usedEntry.add(entryIntent.intentId); count += 1;
  }
  return count;
}

export function processRawProspectiveMsiiPoint({
  sessionDate, predeclaredStartAt, actualStartAt, missingCaptureCount = 0, initialCapital = 1_000_000,
  priorLedger = [], captureRows = [], phase57State, pointResult, versions,
  orderStyleResearchLabel = PHASE57_MSII_ORDER_STYLE.MARKETABLE_QUOTE,
  ttlMs = 5_000, decisionLatencyMs = 100, referenceMaxAgeMs = 5_000, transactionCostJpy = 0,
  laneYDecisions = [],
} = {}) {
  assertSafety(PHASE57_MSII_SHADOW_SAFETY, "Lane M module");
  if (!phase57State?.strategies || !pointResult?.allocation || !pointResult?.exitEvaluation) throw new Error("frozen Phase57 point/state required");
  if (!Array.isArray(captureRows) || !captureRows.length) throw new Error("raw prospective captureRows required");
  const decisionAt = iso(pointResult.at, "pointResult.at");
  if (jstSessionDate(decisionAt) !== sessionDate) throw new Error("Lane M sessionDate mismatch");
  const maxAge = Number(referenceMaxAgeMs); if (!Number.isFinite(maxAge) || maxAge < 0) throw new Error("referenceMaxAgeMs must be non-negative");
  const state = createMsiiShadowExecutionState({ sessionDate, predeclaredStartAt, actualStartAt, missingCaptureCount, backfillUsed: false, initialCapital });
  if (priorLedger.length) {
    verifyMsiiShadowLedger(priorLedger, { sessionDate }); state.ledger = structuredClone(priorLedger); state.ledgerHeadHash = state.ledger.at(-1).eventHash;
  }
  const normalized = captureRows.map(normalizeRawProspectiveMsiiEvent).sort((a,b)=>ms(a.capturedAt)-ms(b.capturedAt)||a.symbol.localeCompare(b.symbol)||a.eventId.localeCompare(b.eventId));
  const references = latestReferences([...committedMarketEvents(state.ledger), ...normalized], decisionAt, maxAge);
  const accepted = new Set(pointResult.allocation.decisions.filter((x)=>x.status==="ACCEPTED").map((x)=>normalizeSymbol(x.symbol)));
  const laneMClosed = capClosed(state.ledger, pointResult.exitEvaluation.closed ?? []);
  const required = [...new Set([...accepted, ...laneMClosed.map((x)=>normalizeSymbol(x.symbol))])].sort();
  const missing = required.filter((symbol)=>!references.has(symbol));
  if (missing.length) return Object.freeze({ complete:false, status:"BLOCKED_MSII_RAW_REFERENCE_MISSING_OR_STALE", decisionAt, missingReferenceSymbols:Object.freeze(missing), ledger:Object.freeze(state.ledger), score:scoreMsiiShadowExecutionLedger(state.ledger,{sessionDate}), pair:compareLaneYWithMsii({laneYDecisions,msiiLedger:state.ledger}), safety:PHASE57_MSII_SHADOW_SAFETY });

  appendNewMarketEvents(state, normalized, (event)=>ms(event.capturedAt)<=ms(decisionAt));
  const start = nextSequence(state.ledger);
  const entries = buildEntryShadowOrderIntentsFromPhase57({ phase57State, allocationResult:pointResult.allocation, marketEventsBySymbol:references, decisionAt, decisionSequenceStart:start, orderStyleResearchLabel, ttlMs, decisionLatencyMs, versions });
  const exits = buildExitShadowOrderIntentsFromPhase57({ exitEvaluation:{...pointResult.exitEvaluation,closed:laneMClosed}, marketEventsBySymbol:references, decisionAt, decisionSequenceStart:start+entries.length, orderStyleResearchLabel, ttlMs, decisionLatencyMs, versions });
  const intents = [...entries,...exits].sort((a,b)=>a.decisionSequence-b.decisionSequence||a.intentId.localeCompare(b.intentId));
  for (const intent of intents) commitShadowOrderIntent(state,intent);
  appendNewMarketEvents(state, normalized, (event)=>ms(event.capturedAt)>ms(decisionAt));
  const available = committedMarketEvents(state.ledger);
  const cutoff = available.reduce((latest,event)=>ms(event.capturedAt)>ms(latest)?event.capturedAt:latest,decisionAt);
  for (const intent of intents) commitShadowFill(state, evaluateShadowFill(intent, available, { asOf:cutoff }));
  const closedTradesCommitted = commitTrades(state, transactionCostJpy);
  verifyMsiiShadowLedger(state.ledger,{sessionDate});
  return Object.freeze({ complete:true, status:"PHASE57_MSII_RAW_PROSPECTIVE_POINT_COMMITTED", version:PHASE57_MSII_RAW_RUNTIME_VERSION, decisionAt, entryIntentCount:entries.length, exitIntentCount:exits.length, closedTradesCommitted, ledger:Object.freeze(state.ledger), score:scoreMsiiShadowExecutionLedger(state.ledger,{sessionDate}), pair:compareLaneYWithMsii({laneYDecisions,msiiLedger:state.ledger}), safety:PHASE57_MSII_SHADOW_SAFETY });
}
