import { createHash } from "node:crypto";
import {
  P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
  decideP25ExitV3DualGate,
} from "../daytrade/phase57-p25-exit-v3-dual-gate.js";
import {
  P25_EXIT_V4_POLICY_SHA256,
  decideP25ExitV4,
} from "../daytrade/phase57-p25-exit-v4-structural-risk.js";
import { scoreP25ExitV2StateConditioned } from "../daytrade/phase57-p25-exit-v2-state-conditioned.js";
import {
  PHASE57_P25_LANE_C_POLICY,
} from "../portfolio/phase57-p25-lane-c-portfolio-simulator.js";
import {
  SAFETY,
  STRATEGY_IDS,
  appendLedgerEvent,
  updateStrategyMark,
} from "./phase57-stateful-contract.js";
import { POSITION_STATUS } from "./phase57-realtime-entry-position.js";

export const REALTIME_EXIT_MODELS = Object.freeze(["V3", "V4"]);
export const PHASE57_REALTIME_EXIT_SAFETY = SAFETY;

export const REALTIME_EXIT_POLICY = Object.freeze({
  V3: Object.freeze({ policySha256: P25_EXIT_V3_DUAL_GATE_POLICY_SHA256 }),
  V4: Object.freeze({ policySha256: P25_EXIT_V4_POLICY_SHA256 }),
  roundTripCostPct: PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps: PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
  finalizedFiveMinuteBarsOnly: true,
  futureBarsVisible: false,
  closedPositionMayReopen: false,
  resultBasedRetuning: false,
});

const FALSE_SAFETY_KEYS = Object.freeze([
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
]);

function assertSafety() {
  for (const key of FALSE_SAFETY_KEYS) {
    if (PHASE57_REALTIME_EXIT_SAFETY[key] !== false) throw new Error(`realtime EXIT safety ${key} must remain false`);
  }
}

function ms(value, label = "timestamp") {
  const parsed = Date.parse(String(value ?? ""));
  if (!Number.isFinite(parsed)) throw new Error(`${label} must be a valid timestamp`);
  return parsed;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  return value;
}

function sha256(value) {
  return createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");
}

function normalizeBar(bar) {
  const parsed = ms(bar?.timestamp ?? bar?.time ?? bar?.at, "finalized bar timestamp");
  const normalized = Object.freeze({
    timestamp: new Date(parsed).toISOString(),
    open: Number(bar?.open),
    high: Number(bar?.high),
    low: Number(bar?.low),
    close: Number(bar?.close),
    volume: Number(bar?.volume ?? 0),
  });
  if (![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)) throw new Error("finalized EXIT bar must contain finite OHLCV");
  if (normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.high < Math.max(normalized.open, normalized.close) || normalized.low > Math.min(normalized.open, normalized.close) || normalized.volume < 0) {
    throw new Error("invalid finalized EXIT bar");
  }
  return normalized;
}

function barFor(source, symbol) {
  if (source instanceof Map) return source.get(symbol) ?? source.get(symbol.replace(/\.T$/, "")) ?? null;
  return source?.[symbol] ?? source?.[symbol.replace(/\.T$/, "")] ?? null;
}

function signOf(direction) {
  return direction === 1 || direction === "LONG" || direction === "UP" ? 1 : -1;
}

function directionalReturn(entryPrice, price, sign) {
  return (Number(price) / Number(entryPrice) - 1) * 100 * sign;
}

function exitModelForStrategy(strategyId) {
  const cell = String(strategyId).split("__")[0];
  if (cell.endsWith("_V3")) return "V3";
  if (cell.endsWith("_V4")) return "V4";
  throw new Error(`strategy ${strategyId} has no EXIT v3/v4 lineage`);
}

function contextAdverseScale(contextBars = []) {
  const ranges = contextBars.map(normalizeBar).slice(-6)
    .map((bar) => (bar.high - bar.low) / bar.close * 100)
    .filter(Number.isFinite);
  return ranges.length ? ranges.reduce((sum, value) => sum + value, 0) / ranges.length : null;
}

function initialExitState(position, model) {
  return Object.freeze({
    model,
    policySha256: REALTIME_EXIT_POLICY[model].policySha256,
    observedBars: Object.freeze([]),
    managementDecisions: Object.freeze([]),
    winnerExitStreak: 0,
    neutralLossStreak: 0,
    downsideHistory: Object.freeze([]),
    adverseExcursionScalePct: model === "V4" ? contextAdverseScale(position.contextBars ?? []) : null,
    mfePct: 0,
    maePct: 0,
    lastDecisionTime: null,
  });
}

function advanceExitState({ position, model, bar, analogPool }) {
  const previous = position.exitState ?? initialExitState(position, model);
  if (previous.model !== model || previous.policySha256 !== REALTIME_EXIT_POLICY[model].policySha256) throw new Error("EXIT state policy lineage mismatch");
  if (previous.lastDecisionTime && ms(bar.timestamp) <= ms(previous.lastDecisionTime)) throw new Error("EXIT bar timestamp must be strictly causal per position");

  const sign = signOf(position.signalDirection);
  const direction = sign === 1 ? "LONG" : "SHORT";
  const observedBars = Object.freeze([...previous.observedBars, bar]);
  const baseScore = scoreP25ExitV2StateConditioned({
    entryPrice: position.entryReferencePrice,
    direction,
    observedBars,
    timestamp: bar.timestamp,
    sessionDate: position.sessionDate,
    analogPool,
  });
  const currentReturnPct = directionalReturn(position.entryReferencePrice, bar.close, sign);
  const barMfe = directionalReturn(position.entryReferencePrice, sign === 1 ? bar.high : bar.low, sign);
  const barMae = directionalReturn(position.entryReferencePrice, sign === 1 ? bar.low : bar.high, sign);
  const mfePct = Math.max(previous.mfePct, barMfe, 0);
  const maePct = Math.min(previous.maePct, barMae, 0);
  const captureRatio = mfePct > 0 ? currentReturnPct / mfePct : null;

  let gate;
  let downsideHistory = previous.downsideHistory;
  if (model === "V3") {
    gate = decideP25ExitV3DualGate({ baseScore, winnerExitStreak: previous.winnerExitStreak });
  } else {
    const horizon1 = (baseScore?.horizonScores ?? []).find((row) => Number(row?.horizonBars) === 1);
    const nextDownsideHistory = Number.isFinite(Number(horizon1?.downsideProbability))
      ? [...previous.downsideHistory, Number(horizon1.downsideProbability)]
      : [...previous.downsideHistory];
    gate = decideP25ExitV4({
      baseScore,
      currentReturnPct,
      mfePct,
      captureRatio,
      downsideHistory: previous.downsideHistory,
      neutralLossStreak: previous.neutralLossStreak,
      winnerExitStreak: previous.winnerExitStreak,
      adverseExcursionScalePct: previous.adverseExcursionScalePct,
    });
    downsideHistory = Object.freeze(nextDownsideHistory);
  }

  const managementDecision = Object.freeze({
    timestamp: bar.timestamp,
    baseScore,
    gate,
    ...(model === "V4" ? { currentReturnPct, mfePct, captureRatio } : {}),
  });
  const next = Object.freeze({
    ...previous,
    observedBars,
    managementDecisions: Object.freeze([...previous.managementDecisions, managementDecision]),
    winnerExitStreak: Number(gate.winnerExitStreak ?? 0),
    neutralLossStreak: Number(gate.neutralLossStreak ?? 0),
    downsideHistory,
    mfePct,
    maePct,
    lastDecisionTime: bar.timestamp,
  });
  return { state: next, baseScore, gate, currentReturnPct, captureRatio };
}

function executionPrice(referencePrice, direction, side, slippageBps) {
  const rate = Number(slippageBps) / 10_000;
  const sign = side === "ENTRY" ? direction : -direction;
  return referencePrice * (1 + sign * rate);
}

function closePosition(sessionState, strategy, position, { at, bar, reason, roundTripCostPct, slippageBps }) {
  const direction = signOf(position.signalDirection);
  const exitReferencePrice = Number(bar.close);
  const exitExecutionPrice = executionPrice(exitReferencePrice, direction, "EXIT", slippageBps);
  const halfCostRate = Number(roundTripCostPct) / 200;
  const exitCostJpy = position.referenceNotional * halfCostRate;
  const executionGrossPnlJpy = direction * (exitExecutionPrice - position.entryExecutionPrice) * position.quantity;
  const referenceGrossPnlJpy = direction * (exitReferencePrice - position.entryReferencePrice) * position.quantity;
  const exitSlippageCostJpy = direction * (exitReferencePrice - exitExecutionPrice) * position.quantity;
  const cashReleasedJpy = direction === 1
    ? exitExecutionPrice * position.quantity - exitCostJpy
    : position.collateralJpy + executionGrossPnlJpy - exitCostJpy;
  const realizedPnlJpy = executionGrossPnlJpy - position.entryCostJpy - exitCostJpy;
  const grossReturnPct = directionalReturn(position.entryReferencePrice, exitReferencePrice, direction);
  const netReturnPct = grossReturnPct - Number(roundTripCostPct);
  const mfePct = position.exitState.mfePct;
  const maePct = position.exitState.maePct;

  strategy.cash += cashReleasedJpy;
  strategy.realizedPnl += executionGrossPnlJpy - exitCostJpy;
  strategy.transactionCosts = Number(strategy.transactionCosts ?? 0) + exitCostJpy;
  strategy.slippageCosts = Number(strategy.slippageCosts ?? 0) + exitSlippageCostJpy;
  strategy.turnoverNotional = Number(strategy.turnoverNotional ?? 0) + exitExecutionPrice * position.quantity;
  strategy.closedTrades += 1;
  if (realizedPnlJpy > 0) strategy.wins += 1;
  if (realizedPnlJpy > 0) strategy.grossProfit += realizedPnlJpy;
  if (realizedPnlJpy < 0) strategy.grossLoss += -realizedPnlJpy;
  strategy.closedTradeRecords ??= [];

  const closed = Object.freeze({
    ...position,
    status: POSITION_STATUS.CLOSED,
    exitDecisionTimestamp: at,
    exitTimestamp: bar.timestamp,
    exitReferencePrice,
    exitExecutionPrice,
    exitReason: reason,
    exitCostJpy,
    exitSlippageCostJpy,
    cashReleasedJpy,
    referenceGrossPnlJpy,
    executionGrossPnlJpy,
    realizedPnlJpy,
    grossReturnPct,
    netReturnPct,
    mfePct,
    maePct,
    givebackPct: Math.max(0, mfePct - grossReturnPct),
    captureRatio: mfePct > 0 ? grossReturnPct / mfePct : null,
    barsHeld: position.exitState.observedBars.length,
    lastEventTime: at,
    lastMarkPrice: exitReferencePrice,
    unrealizedPnl: 0,
    closedInShadowOnly: true,
  });
  strategy.closedTradeRecords.push(closed);
  delete strategy.positions[position.symbol];
  strategy.positionStates[position.symbol] = closed;

  appendLedgerEvent(sessionState, {
    eventId: `${sessionState.sessionDate}:${at}:POSITION_EXIT:${strategy.strategyId}:${position.symbol}`,
    at,
    type: "SHADOW_POSITION_CLOSED",
    strategyId: strategy.strategyId,
    symbol: position.symbol,
    positionId: position.positionId,
    exitModel: position.exitState.model,
    exitPolicySha256: position.exitState.policySha256,
    exitTimestamp: bar.timestamp,
    exitPrice: exitReferencePrice,
    exitReason: reason,
    realizedPnlJpy,
    executable: false,
  });
  return closed;
}

function markStrategy(strategy) {
  let marketValue = 0;
  let unrealizedPnl = 0;
  for (const position of Object.values(strategy.positions)) {
    const direction = signOf(position.signalDirection);
    const mark = Number(position.lastMarkPrice ?? position.entryReferencePrice);
    const pricePnl = direction * (mark - position.entryExecutionPrice) * position.quantity;
    marketValue += direction === 1 ? position.quantity * mark : position.collateralJpy + pricePnl;
    unrealizedPnl += pricePnl;
  }
  updateStrategyMark(strategy, { marketValue, unrealizedPnl });
}

export function ensureRealtimeExitState(sessionState) {
  if (!sessionState?.strategies || !sessionState?.ledger) throw new Error("realtime session state required");
  sessionState.exit ??= { lastEvaluationTime: null, history: [] };
  sessionState.exit.lastEvaluationTime ??= null;
  sessionState.exit.history ??= [];
  return sessionState.exit;
}

/** Evaluate every OPEN strategy position on one finalized five-minute market point. */
export function applyRealtimeExitBar(sessionState, {
  at,
  barsBySymbol = {},
  analogPool = [],
  sessionEnd = false,
  roundTripCostPct = REALTIME_EXIT_POLICY.roundTripCostPct,
  slippageBps = REALTIME_EXIT_POLICY.slippageBps,
} = {}) {
  assertSafety();
  const atMs = ms(at, "EXIT evaluation timestamp");
  if (!Number.isFinite(Number(roundTripCostPct)) || Number(roundTripCostPct) < 0) throw new Error("roundTripCostPct must be non-negative");
  if (!Number.isFinite(Number(slippageBps)) || Number(slippageBps) < 0) throw new Error("slippageBps must be non-negative");
  const exitState = ensureRealtimeExitState(sessionState);
  if (exitState.lastEvaluationTime) {
    const previousMs = ms(exitState.lastEvaluationTime, "last EXIT evaluation timestamp");
    if (atMs < previousMs) throw new Error("EXIT evaluation timestamp cannot move backward");
  }

  const normalizedBars = Object.fromEntries(Object.entries(barsBySymbol instanceof Map ? Object.fromEntries(barsBySymbol) : barsBySymbol)
    .map(([symbol, bar]) => [String(symbol).trim().toUpperCase(), normalizeBar(bar)]));
  for (const [symbol, bar] of Object.entries(normalizedBars)) {
    if (ms(bar.timestamp) !== atMs) throw new Error(`finalized bar timestamp mismatch for ${symbol}`);
  }
  const requestSha256 = sha256({ at, barsBySymbol: normalizedBars, sessionEnd, roundTripCostPct, slippageBps });
  if (exitState.lastEvaluationTime && atMs === ms(exitState.lastEvaluationTime)) {
    const previous = exitState.history.at(-1);
    if (previous?.requestSha256 !== requestSha256) throw new Error("conflicting duplicate EXIT evaluation timestamp");
    return previous;
  }

  const openAtStart = [];
  for (const strategyId of STRATEGY_IDS) {
    const strategy = sessionState.strategies[strategyId];
    for (const symbol of Object.keys(strategy.positions).sort()) openAtStart.push({ strategyId, symbol });
  }
  const evaluated = [];
  const closed = [];
  for (const { strategyId, symbol } of openAtStart) {
    const strategy = sessionState.strategies[strategyId];
    const position = strategy.positions[symbol];
    if (!position || position.status !== POSITION_STATUS.OPEN) continue;
    if (atMs <= ms(position.entryTimestamp, "position Entry timestamp")) continue;
    const source = barFor(normalizedBars, symbol);
    if (!source) throw new Error(`missing finalized EXIT bar for open position ${strategyId}/${symbol}`);
    const bar = normalizeBar(source);
    const model = exitModelForStrategy(strategyId);
    const advanced = advanceExitState({ position, model, bar, analogPool });
    const pricePnl = signOf(position.signalDirection) * (bar.close - position.entryExecutionPrice) * position.quantity;
    const updated = Object.freeze({
      ...position,
      exitState: advanced.state,
      lastEventTime: at,
      lastMarkPrice: bar.close,
      unrealizedPnl: pricePnl,
    });
    strategy.positions[symbol] = updated;
    strategy.positionStates[symbol] = updated;
    const shouldClose = advanced.gate.decision === "EXIT" || sessionEnd === true;
    const reason = advanced.gate.decision === "EXIT"
      ? advanced.gate.reason
      : (sessionEnd === true ? "SESSION_END" : advanced.gate.reason);
    evaluated.push(Object.freeze({ strategyId, symbol, model, decision: shouldClose ? "EXIT" : "HOLD", reason, policySha256: advanced.state.policySha256 }));
    if (shouldClose) {
      closed.push(closePosition(sessionState, strategy, updated, {
        at,
        bar,
        reason,
        roundTripCostPct: Number(roundTripCostPct),
        slippageBps: Number(slippageBps),
      }));
    }
  }

  for (const strategyId of STRATEGY_IDS) markStrategy(sessionState.strategies[strategyId]);
  const result = Object.freeze({
    at,
    requestSha256,
    evaluated: Object.freeze(evaluated),
    closed: Object.freeze(closed),
    sessionEnd: sessionEnd === true,
    safety: SAFETY,
  });
  exitState.lastEvaluationTime = at;
  exitState.history.push(result);
  appendLedgerEvent(sessionState, {
    eventId: `${sessionState.sessionDate}:${at}:EXIT_EVALUATION`,
    at,
    type: "REALTIME_EXIT_EVALUATION_COMMITTED",
    requestSha256,
    evaluatedPositionCount: evaluated.length,
    closedPositionIds: closed.map((position) => position.positionId),
  });
  return result;
}

export default {
  REALTIME_EXIT_MODELS,
  REALTIME_EXIT_POLICY,
  PHASE57_REALTIME_EXIT_SAFETY,
  ensureRealtimeExitState,
  applyRealtimeExitBar,
};
