import {
  DEFAULT_STATE_MACHINE_CONFIG,
  PHASE57_P23_4_SAFETY,
  TRADE_MANAGEMENT_STATES,
  deriveTradeManagementHealth,
  transitionTradeManagementState,
} from './phase57-trade-management-state-machine.js';

export const PHASE57_P23_8D_SAFETY = Object.freeze({
  ...PHASE57_P23_4_SAFETY,
  mode: 'PHASE57_P23_8D_FROZEN_ENTRY_RATCHET_EXIT_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  humanApprovalRequired: true,
});

// P23.8D intentionally uses ONE pre-registered exit design.  The outer frozen
// P23.8 outcomes may compare this design to the old exit, but may never choose
// among multiple V3 configs.  The goal is isolation, not another parameter race.
export const P23_8D_FROZEN_RATCHET_CONFIG = Object.freeze({
  ...DEFAULT_STATE_MACHINE_CONFIG,
  configId: 'STATE_MONOTONIC_RATCHET_V1',
  hardStopUsesEntryAtr: true,
  suppressProfitableSoftExitWhenStructureIntact: true,
  ratchetEnabled: true,
  ratchetActivationAtr: DEFAULT_STATE_MACHINE_CONFIG.profitProtectActivationAtr,
  ratchetGivebackAtrStrong: DEFAULT_STATE_MACHINE_CONFIG.profitProtectGivebackAtrStrong,
  ratchetGivebackAtrHold: DEFAULT_STATE_MACHINE_CONFIG.profitProtectGivebackAtrHold,
  ratchetGivebackAtrCaution: DEFAULT_STATE_MACHINE_CONFIG.profitProtectGivebackAtrCaution,
  roundTripCostPct: DEFAULT_STATE_MACHINE_CONFIG.roundTripCostPct,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

function normalizeBar(raw) {
  const timestamp = new Date(raw?.timestamp ?? raw?.time ?? raw?.datetime).toISOString();
  const bar = {
    timestamp,
    open: Number(raw?.open),
    high: Number(raw?.high),
    low: Number(raw?.low),
    close: Number(raw?.close),
    volume: finite(raw?.volume) ? Number(raw.volume) : 0,
  };
  if (![bar.open, bar.high, bar.low, bar.close].every(Number.isFinite)) throw new TypeError('bar OHLC must be finite');
  if (bar.high < Math.max(bar.open, bar.close, bar.low) || bar.low > Math.min(bar.open, bar.close, bar.high)) {
    throw new Error('invalid OHLC ordering');
  }
  return Object.freeze(bar);
}

function normalizeBars(rows = []) {
  const bars = (Array.isArray(rows) ? rows : []).map(normalizeBar).sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  for (let index = 1; index < bars.length; index += 1) {
    if (bars[index - 1].timestamp === bars[index].timestamp) throw new Error('duplicate bar timestamp is forbidden');
  }
  return bars;
}

function jstDate(timestamp) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function directionSign(direction) {
  if (direction === 1 || direction === 'LONG') return 1;
  if (direction === 0 || direction === -1 || direction === 'SHORT') return -1;
  throw new TypeError('signalDirection must be LONG/SHORT or 1/0');
}

function directionalReturnPct(entry, price, sign) {
  return (Number(price) / Number(entry) - 1) * 100 * sign;
}

function trueRange(bar, previousClose) {
  return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
}

function rollingAtr(history, period) {
  if (!history.length) return null;
  const ranges = history.map((bar, index) => trueRange(bar, index ? history[index - 1].close : bar.open));
  return mean(ranges.slice(-Math.max(2, period)));
}

function givebackAtrForState(state, config) {
  if (state === TRADE_MANAGEMENT_STATES.STRONG_HOLD) return Number(config.ratchetGivebackAtrStrong);
  if (state === TRADE_MANAGEMENT_STATES.CAUTION) return Number(config.ratchetGivebackAtrCaution);
  return Number(config.ratchetGivebackAtrHold);
}

function tighterStop(hardStop, ratchetStop, sign) {
  if (!finite(ratchetStop)) return Number(hardStop);
  return sign === 1 ? Math.max(Number(hardStop), Number(ratchetStop)) : Math.min(Number(hardStop), Number(ratchetStop));
}

function stopFill(bar, stopPrice, sign) {
  if (sign === 1) {
    if (bar.open <= stopPrice) return bar.open;
    if (bar.low <= stopPrice) return stopPrice;
  } else {
    if (bar.open >= stopPrice) return bar.open;
    if (bar.high >= stopPrice) return stopPrice;
  }
  return null;
}

function advanceRatchet({ currentRatchetStop, bestPrice, entryPrice, sign, priorAtr, state, config }) {
  if (config.ratchetEnabled !== true || !finite(priorAtr) || Number(priorAtr) <= 0) {
    return Object.freeze({ stop: currentRatchetStop, activated: finite(currentRatchetStop), candidate: null, improved: false });
  }
  const bestReturnPct = Math.max(0, directionalReturnPct(entryPrice, bestPrice, sign));
  const atrPct = Number(priorAtr) / Number(entryPrice) * 100;
  const activationPct = atrPct * Number(config.ratchetActivationAtr);
  if (bestReturnPct < activationPct) {
    return Object.freeze({ stop: currentRatchetStop, activated: finite(currentRatchetStop), candidate: null, improved: false });
  }
  const givebackAtr = givebackAtrForState(state, config);
  const candidate = sign === 1
    ? Number(bestPrice) - Number(priorAtr) * givebackAtr
    : Number(bestPrice) + Number(priorAtr) * givebackAtr;
  const next = !finite(currentRatchetStop)
    ? candidate
    : (sign === 1 ? Math.max(Number(currentRatchetStop), candidate) : Math.min(Number(currentRatchetStop), candidate));
  const improved = !finite(currentRatchetStop) || (sign === 1 ? next > Number(currentRatchetStop) : next < Number(currentRatchetStop));
  return Object.freeze({ stop: next, activated: true, candidate, improved });
}

function summarizeExit({
  entryPrice, sign, observed, excursionBars = observed, exitPrice, exitReason, exitTimestamp,
  roundTripCostPct, decisions, stateVisitCounts, ratchetHistory, intrabarExit = false,
}) {
  const grossReturnPct = directionalReturnPct(entryPrice, exitPrice, sign);
  const netReturnPct = grossReturnPct - Number(roundTripCostPct || 0);
  const favorablePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.high : bar.low)];
  const adversePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.low : bar.high)];
  const favorable = sign === 1 ? Math.max(...favorablePrices) : Math.min(...favorablePrices);
  const adverse = sign === 1 ? Math.min(...adversePrices) : Math.max(...adversePrices);
  const mfePct = Math.max(0, directionalReturnPct(entryPrice, favorable, sign));
  const maePct = Math.min(0, directionalReturnPct(entryPrice, adverse, sign));
  const profitGivebackPctPoints = Math.max(0, mfePct - grossReturnPct);
  const activeRatchets = ratchetHistory.filter(item => finite(item.stop));
  const ratchetNeverLoosened = activeRatchets.every((item, index) => {
    if (!index) return true;
    return sign === 1
      ? Number(item.stop) >= Number(activeRatchets[index - 1].stop)
      : Number(item.stop) <= Number(activeRatchets[index - 1].stop);
  });
  return Object.freeze({
    phase: '57.p23.8d-ratchet-exit',
    status: 'FROZEN_ENTRY_RATCHET_EXIT_EVALUATED',
    direction: sign === 1 ? 'LONG' : 'SHORT',
    entryPrice,
    exitPrice,
    exitReason,
    outcomeAt: exitTimestamp,
    barsHeld: observed.length,
    grossReturnPct,
    netReturnPct,
    mfePct,
    maePct,
    profitGivebackPctPoints,
    captureRatio: mfePct > 0 ? clamp(grossReturnPct / mfePct, -5, 5) : null,
    decisions: Object.freeze(decisions),
    stateVisitCounts: Object.freeze({ ...stateVisitCounts }),
    ratchetHistory: Object.freeze(ratchetHistory),
    ratchetNeverLoosened,
    ratchetActivated: activeRatchets.length > 0,
    fixedTimeExitPrimary: false,
    maxHoldOnlySafetyGuard: true,
    chartAware: true,
    stateful: true,
    pointInTimeSequential: true,
    preBarStopsUseCompletedBarsOnly: true,
    currentBarCloseUsedForStateTransition: true,
    futureBarsUsedBeforeDecision: false,
    futureExtremaUsedForDecision: false,
    frozenEntryRequired: true,
    outerOutcomeConfigSelectionAllowed: false,
    intrabarExit,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_8D_SAFETY,
  });
}

export function simulateFrozenRatchetExit(row = {}, options = {}) {
  const config = Object.freeze({ ...P23_8D_FROZEN_RATCHET_CONFIG, ...(options?.config ?? options) });
  const entryPrice = Number(row?.entryPrice);
  if (!finite(entryPrice) || entryPrice <= 0) return null;
  const sign = directionSign(row?.signalDirection ?? row?.direction);
  const contextBars = normalizeBars(row?.contextBars ?? row?.historyBars ?? []);
  const futureBars = normalizeBars(row?.futureBars ?? row?.path ?? []);
  if (!futureBars.length) return null;
  if (contextBars.length && contextBars.at(-1).timestamp >= futureBars[0].timestamp) {
    throw new Error('context bars must be strictly earlier than managed future bars');
  }
  const sessionDate = row?.sessionDate == null ? null : String(row.sessionDate);
  if (sessionDate && futureBars.some(bar => jstDate(bar.timestamp) !== sessionDate)) {
    throw new Error('frozen ratchet exit forbids cross-session future bars');
  }
  if (row?.frozenEntry === false) throw new Error('P23.8D requires a frozen entry');

  const entryAtrRaw = rollingAtr(contextBars, Math.max(2, Number(config.atrBars)));
  const entryAtr = finite(entryAtrRaw) && Number(entryAtrRaw) > 0 ? Number(entryAtrRaw) : entryPrice * 0.005;
  const hardStop = sign === 1
    ? entryPrice - entryAtr * Number(config.hardStopAtr)
    : entryPrice + entryAtr * Number(config.hardStopAtr);
  const maxHoldBars = Math.max(1, Number(config.maxHoldBars) || futureBars.length);
  const roundTripCostPct = Math.max(0, Number(config.roundTripCostPct) || 0);
  const decisions = [];
  const observed = [];
  const stateVisitCounts = {
    [TRADE_MANAGEMENT_STATES.STRONG_HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.CAUTION]: 0,
  };
  const ratchetHistory = [];
  let state = TRADE_MANAGEMENT_STATES.HOLD;
  let priorBest = entryPrice;
  let warningStreak = 0;
  let severeStreak = 0;
  let recoveryStreak = 0;
  let barsInCaution = 0;
  let ratchetStop = null;

  for (let index = 0; index < Math.min(futureBars.length, maxHoldBars); index += 1) {
    const bar = futureBars[index];
    const activeStop = tighterStop(hardStop, ratchetStop, sign);
    const fill = stopFill(bar, activeStop, sign);
    if (finite(fill)) {
      observed.push(bar);
      decisions.push(Object.freeze({
        index,
        timestamp: bar.timestamp,
        priorState: state,
        nextState: TRADE_MANAGEMENT_STATES.EXIT,
        action: 'EXIT',
        reason: finite(ratchetStop) && activeStop === ratchetStop ? 'MONOTONIC_RATCHET_STOP' : 'ENTRY_ATR_HARD_STOP',
        stopPrice: activeStop,
        hardStopPrice: hardStop,
        ratchetStop,
        stopWasFixedBeforeCurrentBar: true,
      }));
      return summarizeExit({
        entryPrice, sign, observed, excursionBars: observed.slice(0, -1), exitPrice: Number(fill),
        exitReason: finite(ratchetStop) && activeStop === ratchetStop ? 'MONOTONIC_RATCHET_STOP' : 'ENTRY_ATR_HARD_STOP',
        exitTimestamp: bar.timestamp, roundTripCostPct, decisions, stateVisitCounts, ratchetHistory, intrabarExit: true,
      });
    }

    observed.push(bar);
    const priorHistory = [...contextBars, ...observed.slice(0, -1)];
    const priorAtrRaw = rollingAtr(priorHistory, Math.max(2, Number(config.atrBars)));
    const priorAtr = finite(priorAtrRaw) && Number(priorAtrRaw) > 0 ? Number(priorAtrRaw) : entryAtr;
    const history = [...contextBars, ...observed];
    const health = deriveTradeManagementHealth({ history, entryPrice, sign, priorBest, priorAtr, config });
    let transition = transitionTradeManagementState({
      priorState: state,
      damageVotes: health.damageVotes,
      healthyVotes: health.healthyVotes,
      structureBroken: health.structureBroken,
      barsHeld: index + 1,
      warningStreak,
      severeStreak,
      recoveryStreak,
      barsInCaution,
    }, config);

    const closeReturnPct = directionalReturnPct(entryPrice, bar.close, sign);
    const profitableStructureIntact = closeReturnPct > 0 && !health.structureBroken;
    const severeDamage = Number(health.damageVotes) >= Number(config.severeBreakdownDamageVotes);
    if (transition.exit
      && config.suppressProfitableSoftExitWhenStructureIntact === true
      && profitableStructureIntact
      && !severeDamage) {
      transition = Object.freeze({
        ...transition,
        nextState: TRADE_MANAGEMENT_STATES.CAUTION,
        exit: false,
        reason: 'PROFITABLE_STRUCTURE_INTACT_RATCHET_GOVERNS',
        barsInCaution: Math.max(1, Number(transition.barsInCaution || 0)),
      });
    }

    warningStreak = transition.warningStreak;
    severeStreak = transition.severeStreak;
    recoveryStreak = transition.recoveryStreak;
    barsInCaution = transition.barsInCaution;

    decisions.push(Object.freeze({
      index,
      timestamp: bar.timestamp,
      priorState: state,
      nextState: transition.nextState,
      action: transition.exit ? 'EXIT' : 'HOLD',
      reason: transition.reason,
      closeReturnPct,
      health,
      transition,
      ratchetStopBeforeBar: ratchetStop,
    }));

    if (transition.exit) {
      return summarizeExit({
        entryPrice, sign, observed, exitPrice: bar.close, exitReason: transition.reason,
        exitTimestamp: bar.timestamp, roundTripCostPct, decisions, stateVisitCounts, ratchetHistory,
      });
    }

    state = transition.nextState;
    stateVisitCounts[state] += 1;
    const favorableNow = sign === 1 ? bar.high : bar.low;
    if ((sign === 1 && favorableNow > priorBest) || (sign === -1 && favorableNow < priorBest)) priorBest = favorableNow;

    const ratchet = advanceRatchet({
      currentRatchetStop: ratchetStop,
      bestPrice: priorBest,
      entryPrice,
      sign,
      priorAtr,
      state,
      config,
    });
    ratchetStop = ratchet.stop;
    ratchetHistory.push(Object.freeze({
      index,
      timestamp: bar.timestamp,
      state,
      bestPrice: priorBest,
      priorAtr,
      candidate: ratchet.candidate,
      stop: ratchetStop,
      activated: ratchet.activated,
      improved: ratchet.improved,
      becomesActiveNextBar: true,
    }));

    if (index === futureBars.length - 1) {
      return summarizeExit({
        entryPrice, sign, observed, exitPrice: bar.close, exitReason: 'SESSION_OR_DATA_END',
        exitTimestamp: bar.timestamp, roundTripCostPct, decisions, stateVisitCounts, ratchetHistory,
      });
    }
  }

  const last = observed.at(-1);
  if (!last) return null;
  return summarizeExit({
    entryPrice, sign, observed, exitPrice: last.close, exitReason: 'MAX_HOLD_SAFETY_GUARD',
    exitTimestamp: last.timestamp, roundTripCostPct, decisions, stateVisitCounts, ratchetHistory,
  });
}

export function summarizeFrozenRatchetOutcomes(outcomes = []) {
  const rows = Array.isArray(outcomes) ? outcomes : [];
  const n = rows.length;
  const positive = rows.filter(row => Number(row.netReturnPct) > 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const negative = -rows.filter(row => Number(row.netReturnPct) < 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  return Object.freeze({
    signalCount: n,
    hitRate: n ? rows.filter(row => Number(row.netReturnPct) > 0).length / n : null,
    netAverageReturnPct: n ? mean(rows.map(row => Number(row.netReturnPct))) : null,
    grossAverageReturnPct: n ? mean(rows.map(row => Number(row.grossReturnPct))) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: n ? mean(rows.map(row => Number(row.barsHeld))) : null,
    averageMfePct: n ? mean(rows.map(row => Number(row.mfePct))) : null,
    averageMaePct: n ? mean(rows.map(row => Number(row.maePct))) : null,
    averageProfitGivebackPctPoints: n ? mean(rows.map(row => Number(row.profitGivebackPctPoints))) : null,
    ratchetActivationRate: n ? rows.filter(row => row.ratchetActivated === true).length / n : null,
    ratchetNeverLoosenedForAllTrades: rows.every(row => row.ratchetNeverLoosened === true),
  });
}

export default {
  P23_8D_FROZEN_RATCHET_CONFIG,
  simulateFrozenRatchetExit,
  summarizeFrozenRatchetOutcomes,
};
