export const PHASE57_REALTIME_VERSION = "phase57-realtime-stateful-r1";

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
    safety: SAFETY,
  };
}

export function appendLedgerEvent(state, event) {
  if (!event?.eventId || !event?.at || !event?.type) throw new Error("ledger event requires eventId/at/type");
  if (state.ledger.some((x) => x.eventId === event.eventId)) throw new Error(`duplicate eventId ${event.eventId}`);
  if (state.lastBarTime && event.at < state.lastBarTime) throw new Error("non-causal event ordering");
  state.ledger.push(Object.freeze({ ...event }));
  return state;
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
    strategies: STRATEGY_IDS.map((id) => strategySnapshot(state.strategies[id], at)),
    safety: SAFETY,
  };
}
