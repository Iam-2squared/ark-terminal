import {
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
} from "../portfolio/phase57-p25-lane-c-portfolio-simulator.js";
import {
  PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY,
  scoreP25AdaptiveAllocationCandidate,
} from "../portfolio/phase57-p25-adaptive-allocation-v2.js";
import {
  ALLOCATION_PROFILES,
  SAFETY,
  STRATEGY_IDS,
  appendLedgerEvent,
  updateStrategyMark,
} from "./phase57-stateful-contract.js";
import { commitShadowPositionEntry } from "./phase57-realtime-entry-position.js";

const LOT = PHASE57_P25_LANE_C_POLICY.lotSize;
const HALF_COST_RATE = PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct / 200;
const FALSE_KEYS = [
  "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
  "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
];

function assertSafety() {
  for (const key of FALSE_KEYS) if (SAFETY[key] !== false) throw new Error(`unsafe realtime allocation ${key}`);
}
function finite(v) { return v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v)); }
function strategyParts(strategyId) {
  const [cell, profileId] = String(strategyId).split("__");
  if (!cell || !ALLOCATION_PROFILES.includes(profileId)) throw new Error(`invalid strategyId ${strategyId}`);
  return { cell, profileId };
}
function markOf(marksBySymbol, symbol, fallback) {
  const raw = marksBySymbol instanceof Map ? marksBySymbol.get(symbol) : marksBySymbol?.[symbol];
  const price = Number(raw?.close ?? raw?.price ?? raw ?? fallback);
  return Number.isFinite(price) && price > 0 ? price : Number(fallback);
}
function positionValue(position, mark) {
  if (position.signalDirection === 1) return position.quantity * mark;
  return position.collateralJpy + (position.entryExecutionPrice - mark) * position.quantity;
}
function strategyValuation(strategy, marksBySymbol = {}) {
  let marketValue = 0, unrealizedPnl = 0, grossExposure = 0;
  for (const position of Object.values(strategy.positions ?? {})) {
    const mark = markOf(marksBySymbol, position.symbol, position.lastMarkPrice ?? position.entryReferencePrice);
    marketValue += positionValue(position, mark);
    unrealizedPnl += position.signalDirection * (mark - position.entryExecutionPrice) * position.quantity;
    grossExposure += Math.abs(position.quantity * mark);
  }
  return { marketValue, unrealizedPnl, grossExposure, equity: strategy.cash + marketValue };
}
function accountingForQuantity(entry, quantity) {
  const ref = Number(entry.entryPrice);
  const entryExecutionPrice = ref;
  const referenceNotional = quantity * ref;
  const entryExecutionNotional = referenceNotional;
  const entryCostJpy = referenceNotional * HALF_COST_RATE;
  return Object.freeze({
    quantity,
    entryExecutionPrice,
    referenceNotional,
    entryExecutionNotional,
    entryCostJpy,
    entrySlippageCostJpy: 0,
    collateralJpy: entryExecutionNotional,
    cashRequiredJpy: entryExecutionNotional + entryCostJpy,
  });
}
function maxAffordableQty(cash, refPrice, budget) {
  const perShareCash = refPrice * (1 + HALF_COST_RATE);
  const maxByBudget = Math.floor(budget / refPrice / LOT) * LOT;
  const maxByCash = Math.floor(cash / perShareCash / LOT) * LOT;
  return Math.max(0, Math.min(maxByBudget, maxByCash));
}
function profileWeight(row, profileId) {
  if (profileId === "ADAPTIVE_EQUAL") return 1;
  if (profileId === "ADAPTIVE_RANK") return PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.rankWeights[row.quality.rank];
  return Math.max(1e-6, row.quality.score);
}
function adaptiveTarget(rows) {
  if (!rows.length) return 0;
  const order = ["S", "A", "B", "C"];
  const best = rows.map((x) => x.quality.rank).sort((a, b) => order.indexOf(a) - order.indexOf(b))[0];
  const d = PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.deployment;
  return Math.min(d.maximumTargetUtilization, d.singleRankTarget[best] + Math.max(0, rows.length - 1) * d.breadthBonusPerAdditionalCandidate);
}
function eligibleEntries(entries, cell) {
  return [...(entries ?? [])]
    .filter((entry) => entry?.strategyLineage?.cells?.includes(cell) && entry.entryAccepted === true)
    .sort((a, b) => String(a.entryTimestamp).localeCompare(String(b.entryTimestamp)) || String(a.symbol).localeCompare(String(b.symbol)));
}

export function ensureRealtimeAllocationState(sessionState) {
  if (!sessionState?.strategies || !sessionState?.ledger) throw new Error("realtime session state required");
  sessionState.allocation ??= { lastEvaluationTime: null, history: [] };
  sessionState.allocation.history ??= [];
  return sessionState.allocation;
}

function legacyAllocate(sessionState, strategyId, entries, marksBySymbol, at, profileId) {
  const strategy = sessionState.strategies[strategyId];
  const profile = PHASE57_P25_LANE_C_ALLOCATION_PROFILES.find((x) => x.id === profileId);
  if (!profile) throw new Error(`missing frozen legacy profile ${profileId}`);
  const decisions = [];
  for (const entry of entries) {
    const valuation = strategyValuation(strategy, marksBySymbol);
    const budget = valuation.equity / profile.maxPositions;
    if (Object.keys(strategy.positions).length >= profile.maxPositions) {
      decisions.push({ strategyId, symbol: entry.symbol, status: "REJECTED", reason: "MAX_CONCURRENT_POSITIONS" });
      continue;
    }
    if (strategy.positions[entry.symbol]) {
      decisions.push({ strategyId, symbol: entry.symbol, status: "REJECTED", reason: "SYMBOL_ALREADY_OPEN" });
      continue;
    }
    const quantity = maxAffordableQty(strategy.cash, Number(entry.entryPrice), budget);
    if (quantity < LOT) {
      decisions.push({ strategyId, symbol: entry.symbol, status: "REJECTED", reason: "LOT_OR_CASH_CONSTRAINT" });
      continue;
    }
    const accounting = accountingForQuantity(entry, quantity);
    commitShadowPositionEntry(sessionState, { strategyId, entry, accounting });
    strategy.allocationOpenMeta ??= {};
    strategy.allocationOpenMeta[entry.symbol] = Object.freeze({ profileId, weighting: "EQUITY_DIVIDED_BY_MAX_POSITIONS", at });
    decisions.push({ strategyId, symbol: entry.symbol, status: "ACCEPTED", quantity, targetBudgetJpy: budget });
  }
  return decisions;
}

function adaptiveAllocate(sessionState, strategyId, entries, marksBySymbol, at, profileId) {
  const strategy = sessionState.strategies[strategyId];
  strategy.allocationOpenMeta ??= {};
  const valuation = strategyValuation(strategy, marksBySymbol);
  const candidates = entries
    .filter((entry) => !strategy.positions[entry.symbol])
    .map((entry) => ({ entry, quality: scoreP25AdaptiveAllocationCandidate({
      confidence: entry.confidence,
      probability: entry.probability,
      selectionOpportunityScore: entry.selectionLineage?.opportunityScore,
      selectionV2Score: entry.selectionLineage?.v2Score,
    }) }))
    .sort((a, b) => b.quality.score - a.quality.score || String(a.entry.symbol).localeCompare(String(b.entry.symbol)));
  const policy = PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY;
  const slots = Math.max(0, policy.maximumConcurrentPositions - Object.keys(strategy.positions).length);
  const accepted = candidates.slice(0, slots);
  const decisions = candidates.slice(slots).map((x) => ({ strategyId, symbol: x.entry.symbol, status: "REJECTED", reason: "MAX_CONCURRENT_POSITIONS", rank: x.quality.rank, score: x.quality.score }));
  if (!accepted.length) return decisions;

  const existingQualities = Object.values(strategy.allocationOpenMeta)
    .filter((x) => x?.quality)
    .map((x) => ({ quality: x.quality }));
  const target = adaptiveTarget(existingQualities.concat(accepted));
  const capacity = Math.max(0, valuation.equity * target - valuation.grossExposure);
  const available = Math.min(strategy.cash, capacity);
  const weights = accepted.map((x) => profileWeight(x, profileId));
  const weightSum = weights.reduce((a, b) => a + b, 0);

  for (let i = 0; i < accepted.length; i++) {
    const row = accepted[i];
    const desired = Math.min(valuation.equity * row.quality.equityCap, available * (weights[i] / weightSum));
    const quantity = maxAffordableQty(strategy.cash, Number(row.entry.entryPrice), desired);
    if (quantity < LOT) {
      decisions.push({ strategyId, symbol: row.entry.symbol, status: "REJECTED", reason: "LOT_OR_CASH_CONSTRAINT", rank: row.quality.rank, score: row.quality.score });
      continue;
    }
    const accounting = accountingForQuantity(row.entry, quantity);
    commitShadowPositionEntry(sessionState, { strategyId, entry: row.entry, accounting });
    strategy.allocationOpenMeta[row.entry.symbol] = Object.freeze({ profileId, weighting: profileId.replace("ADAPTIVE_", ""), at, quality: row.quality, targetUtilization: target });
    decisions.push({ strategyId, symbol: row.entry.symbol, status: "ACCEPTED", quantity, rank: row.quality.rank, score: row.quality.score, targetUtilization: target });
  }
  return decisions;
}

export function allocateRealtimeFrozenEntries(sessionState, { at, entries = sessionState?.entry?.latest ?? [], marksBySymbol = {} } = {}) {
  assertSafety();
  const allocation = ensureRealtimeAllocationState(sessionState);
  if (!at) throw new Error("allocation timestamp required");
  if (allocation.lastEvaluationTime && Date.parse(at) < Date.parse(allocation.lastEvaluationTime)) throw new Error("allocation timestamp cannot move backward");
  if (allocation.lastEvaluationTime === at) return allocation.history.at(-1);

  const decisions = [];
  for (const strategyId of STRATEGY_IDS) {
    const { cell, profileId } = strategyParts(strategyId);
    const candidates = eligibleEntries(entries, cell);
    if (profileId.startsWith("ADAPTIVE_")) decisions.push(...adaptiveAllocate(sessionState, strategyId, candidates, marksBySymbol, at, profileId));
    else decisions.push(...legacyAllocate(sessionState, strategyId, candidates, marksBySymbol, at, profileId));
  }
  markRealtimeStrategies(sessionState, { at, marksBySymbol });
  const result = Object.freeze({ at, strategyCount: STRATEGY_IDS.length, decisions: Object.freeze(decisions), safety: SAFETY });
  allocation.lastEvaluationTime = at;
  allocation.history.push(result);
  appendLedgerEvent(sessionState, {
    eventId: `${sessionState.sessionDate}:${at}:REALTIME_28WAY_ALLOCATION`,
    at,
    type: "REALTIME_28WAY_ALLOCATION_COMMITTED",
    strategyCount: STRATEGY_IDS.length,
    accepted: decisions.filter((x) => x.status === "ACCEPTED").length,
    rejected: decisions.filter((x) => x.status === "REJECTED").length,
    executable: false,
  });
  return result;
}

export function markRealtimeStrategies(sessionState, { at, marksBySymbol = {} } = {}) {
  assertSafety();
  for (const strategyId of STRATEGY_IDS) {
    const strategy = sessionState.strategies[strategyId];
    const valuation = strategyValuation(strategy, marksBySymbol);
    updateStrategyMark(strategy, { marketValue: valuation.marketValue, unrealizedPnl: valuation.unrealizedPnl });
  }
  return Object.freeze({ at, strategyCount: STRATEGY_IDS.length });
}

export const PHASE57_REALTIME_ALLOCATION_SAFETY = SAFETY;
