import { createHash } from "node:crypto";

export const PHASE57_REALTIME_VERSION = "phase57-realtime-stateful-r7";

export const SAFETY = Object.freeze({
  mode: "SHADOW_ONLY",
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

export const MATRIX_CELLS = Object.freeze(["V1_V3", "V1_V4", "V2_V3", "V2_V4"]);
export const ALLOCATION_PROFILES = Object.freeze([
  "MAX_10", "MAX_4", "MAX_3", "MAX_2",
  "ADAPTIVE_EQUAL", "ADAPTIVE_RANK", "ADAPTIVE_SCORE",
]);
export const STRATEGY_IDS = Object.freeze(
  MATRIX_CELLS.flatMap((cell) => ALLOCATION_PROFILES.map((profile) => `${cell}__${profile}`)),
);

const GENESIS_HASH = "0".repeat(64);
const canonical = (value) => {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
};
const hash = (value) => createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
const validTime = (value) => Number.isFinite(Date.parse(String(value ?? "")));

export function createRealtimeSessionState({ sessionDate, initialCapital = 1_000_000 } = {}) {
  if (!sessionDate) throw new Error("sessionDate required");
  const strategies = Object.fromEntries(STRATEGY_IDS.map((id) => [id, {
    strategyId: id,
    initialCapital,
    cash: initialCapital,
    equity: initialCapital,
    realizedPnl: 0,
    unrealizedPnl: 0,
    netPercent: 0,
    peakEquity: initialCapital,
    maxDrawdownPercent: 0,
    positions: {},
    closedTrades: 0,
    wins: 0,
    grossProfit: 0,
    grossLoss: 0,
  }]));
  return {
    version: PHASE57_REALTIME_VERSION,
    sessionDate,
    lastBarTime: null,
    symbols: {},
    selection: { V1: [], V2: [] },
    strategies,
    ledger: [],
    ledgerHeadHash: GENESIS_HASH,
    safety: SAFETY,
  };
}

export function appendLedgerEvent(state, event) {
  if (!event?.eventId || !event?.at || !event?.type) throw new Error("ledger event requires eventId/at/type");
  if (!validTime(event.at)) throw new Error("ledger event at must be a valid timestamp");
  if (state.ledger.some((x) => x.eventId === event.eventId)) throw new Error(`duplicate eventId ${event.eventId}`);
  const previous = state.ledger.at(-1);
  if (previous && Date.parse(event.at) < Date.parse(previous.at)) throw new Error("non-causal ledger ordering");
  if (state.lastBarTime && Date.parse(event.at) < Date.parse(state.lastBarTime)) throw new Error("non-causal event ordering");
  const sequence = state.ledger.length;
  const previousHash = previous?.eventHash ?? GENESIS_HASH;
  const core = {
    ...event,
    sessionDate: event.sessionDate ?? state.sessionDate,
    sequence,
    previousHash,
    executable: false,
  };
  const committed = Object.freeze({ ...core, eventHash: hash(core) });
  state.ledger.push(committed);
  state.ledgerHeadHash = committed.eventHash;
  return state;
}

export function verifyRealtimeLedger(ledger, { sessionDate = null } = {}) {
  if (!Array.isArray(ledger)) throw new Error("ledger must be an array");
  const ids = new Set();
  let previousHash = GENESIS_HASH;
  let previousAt = null;
  for (let i = 0; i < ledger.length; i++) {
    const row = ledger[i];
    if (!row?.eventId || !row?.type || !validTime(row?.at)) throw new Error(`invalid ledger event at sequence ${i}`);
    if (row.sequence !== i) throw new Error(`ledger sequence mismatch at ${i}`);
    if (ids.has(row.eventId)) throw new Error(`duplicate eventId ${row.eventId}`);
    ids.add(row.eventId);
    if (sessionDate && row.sessionDate !== sessionDate) throw new Error(`ledger sessionDate mismatch at ${i}`);
    if (previousAt && Date.parse(row.at) < Date.parse(previousAt)) throw new Error(`ledger timestamp moved backward at ${i}`);
    if (row.previousHash !== previousHash) throw new Error(`ledger previousHash mismatch at ${i}`);
    const { eventHash, ...core } = row;
    const expected = hash(core);
    if (eventHash !== expected) throw new Error(`ledger eventHash mismatch at ${i}`);
    previousHash = eventHash;
    previousAt = row.at;
  }
  return Object.freeze({ valid: true, eventCount: ledger.length, headHash: previousHash });
}

export function createRealtimeCheckpoint(state, { at = state.lastBarTime } = {}) {
  const verified = verifyRealtimeLedger(state.ledger, { sessionDate: state.sessionDate });
  const checkpoint = {
    schemaVersion: 1,
    version: state.version,
    sessionDate: state.sessionDate,
    at,
    ledgerEventCount: verified.eventCount,
    ledgerHeadHash: verified.headHash,
    state: {
      lastBarTime: state.lastBarTime,
      symbols: state.symbols,
      selection: state.selection,
      strategies: state.strategies,
      entry: state.entry ?? null,
      exit: state.exit ?? null,
      allocation: state.allocation ?? null,
    },
    safety: SAFETY,
  };
  return Object.freeze({ ...checkpoint, checkpointHash: hash(checkpoint) });
}

export function verifyRealtimeCheckpoint(checkpoint, ledger) {
  if (!checkpoint?.checkpointHash) throw new Error("checkpointHash required");
  const { checkpointHash, ...core } = checkpoint;
  if (checkpointHash !== hash(core)) throw new Error("checkpoint hash mismatch");
  const verified = verifyRealtimeLedger(ledger, { sessionDate: checkpoint.sessionDate });
  if (verified.eventCount < checkpoint.ledgerEventCount) throw new Error("ledger shorter than checkpoint");
  const anchored = checkpoint.ledgerEventCount ? ledger[checkpoint.ledgerEventCount - 1]?.eventHash : GENESIS_HASH;
  if (anchored !== checkpoint.ledgerHeadHash) throw new Error("checkpoint ledger anchor mismatch");
  return Object.freeze({ valid: true, checkpointHash, ledgerHeadHash: verified.headHash });
}

export function updateStrategyMark(strategy, { marketValue = 0, unrealizedPnl = 0 } = {}) {
  strategy.unrealizedPnl = unrealizedPnl;
  strategy.equity = strategy.cash + marketValue;
  strategy.netPercent = ((strategy.equity / strategy.initialCapital) - 1) * 100;
  strategy.peakEquity = Math.max(strategy.peakEquity, strategy.equity);
  const dd = strategy.peakEquity > 0 ? ((strategy.peakEquity - strategy.equity) / strategy.peakEquity) * 100 : 0;
  strategy.maxDrawdownPercent = Math.max(strategy.maxDrawdownPercent, dd);
  return strategy;
}

export function strategySnapshot(strategy, at) {
  const winRate = strategy.closedTrades ? (strategy.wins / strategy.closedTrades) * 100 : null;
  const profitFactor = strategy.grossLoss > 0 ? strategy.grossProfit / strategy.grossLoss : (strategy.grossProfit > 0 ? Infinity : null);
  return Object.freeze({
    at,
    strategyId: strategy.strategyId,
    equity: strategy.equity,
    netPercent: strategy.netPercent,
    realizedPnl: strategy.realizedPnl,
    unrealizedPnl: strategy.unrealizedPnl,
    openPositions: Object.keys(strategy.positions).length,
    closedTrades: strategy.closedTrades,
    winRate,
    profitFactor,
    maxDrawdownPercent: strategy.maxDrawdownPercent,
  });
}

export function dashboardSnapshot(state, at = state.lastBarTime) {
  return {
    version: PHASE57_REALTIME_VERSION,
    sessionDate: state.sessionDate,
    at,
    strategyCount: STRATEGY_IDS.length,
    ledgerEventCount: state.ledger.length,
    ledgerHeadHash: state.ledgerHeadHash ?? GENESIS_HASH,
    strategies: STRATEGY_IDS.map((id) => strategySnapshot(state.strategies[id], at)),
    safety: SAFETY,
  };
}
