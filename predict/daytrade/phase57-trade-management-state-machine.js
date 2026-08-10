export const PHASE57_P23_4_SAFETY = Object.freeze({
  mode: 'PHASE57_TRADE_MANAGEMENT_STATE_MACHINE_READ_ONLY_RESEARCH',
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

export const TRADE_MANAGEMENT_STATES = Object.freeze({
  STRONG_HOLD: 'STRONG_HOLD',
  HOLD: 'HOLD',
  CAUTION: 'CAUTION',
  EXIT: 'EXIT',
});

export const DEFAULT_STATE_MACHINE_CONFIG = Object.freeze({
  fastBars: 3,
  slowBars: 8,
  momentumBars: 3,
  swingBars: 4,
  atrBars: 8,
  hardStopAtr: 1.5,
  profitProtectActivationAtr: 1.75,
  profitProtectGivebackAtrStrong: 1.5,
  profitProtectGivebackAtrHold: 1.25,
  profitProtectGivebackAtrCaution: 0.9,
  healthyPullbackAtr: 1.5,
  strongHoldMinHealthyVotes: 5,
  cautionEnterDamageVotes: 2,
  cautionExitDamageVotes: 4,
  cautionConfirmBars: 2,
  severeBreakdownDamageVotes: 5,
  severeBreakdownConfirmBars: 2,
  recoveryHealthyVotes: 5,
  recoveryConfirmBars: 1,
  minBarsBeforeStateExit: 2,
  maxHoldBars: 1000,
  roundTripCostPct: 0.05,
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

function rollingVwap(history) {
  const totalVolume = history.reduce((sum, bar) => sum + Math.max(0, Number(bar.volume || 0)), 0);
  if (totalVolume <= 0) return history.at(-1)?.close ?? null;
  return history.reduce((sum, bar) => {
    const typical = (bar.high + bar.low + bar.close) / 3;
    return sum + typical * Math.max(0, Number(bar.volume || 0));
  }, 0) / totalVolume;
}

function stateGivebackAtr(state, config) {
  if (state === TRADE_MANAGEMENT_STATES.STRONG_HOLD) return Number(config.profitProtectGivebackAtrStrong);
  if (state === TRADE_MANAGEMENT_STATES.CAUTION) return Number(config.profitProtectGivebackAtrCaution);
  return Number(config.profitProtectGivebackAtrHold);
}

function preBarStop({ entryPrice, sign, priorAtr, priorBest, priorBestReturnPct, state, config }) {
  const hardStopPrice = sign === 1
    ? entryPrice - priorAtr * Number(config.hardStopAtr)
    : entryPrice + priorAtr * Number(config.hardStopAtr);
  const priorAtrPct = priorAtr / entryPrice * 100;
  const protectionActive = priorBestReturnPct >= priorAtrPct * Number(config.profitProtectActivationAtr);
  const givebackAtr = stateGivebackAtr(state, config);
  const protectionStop = protectionActive
    ? (sign === 1 ? priorBest - priorAtr * givebackAtr : priorBest + priorAtr * givebackAtr)
    : null;

  if (!finite(protectionStop)) {
    return Object.freeze({
      stopPrice: hardStopPrice,
      reason: 'ATR_HARD_STOP',
      hardStopPrice,
      protectionStop: null,
      protectionActive: false,
      stateAtStopCalculation: state,
    });
  }
  const protectionIsTighter = sign === 1 ? protectionStop > hardStopPrice : protectionStop < hardStopPrice;
  return Object.freeze({
    stopPrice: protectionIsTighter ? protectionStop : hardStopPrice,
    reason: protectionIsTighter ? 'STATE_AWARE_PROFIT_PROTECTION' : 'ATR_HARD_STOP',
    hardStopPrice,
    protectionStop,
    protectionActive: true,
    stateAtStopCalculation: state,
  });
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

export function deriveTradeManagementHealth({ history = [], entryPrice, sign, priorBest, priorAtr, config = DEFAULT_STATE_MACHINE_CONFIG }) {
  if (!history.length) throw new Error('history is required');
  const current = history.at(-1);
  const closes = history.map(bar => Number(bar.close));
  const fast = mean(closes.slice(-Math.max(1, Number(config.fastBars))));
  const slow = mean(closes.slice(-Math.max(2, Number(config.slowBars))));
  const momentumLookback = Math.min(Math.max(1, Number(config.momentumBars)), Math.max(1, closes.length - 1));
  const momentumReference = closes[Math.max(0, closes.length - 1 - momentumLookback)];
  const momentumPct = directionalReturnPct(momentumReference, current.close, sign);
  const vwap = rollingVwap(history);
  const prior = history.slice(0, -1);
  const swingWindow = prior.slice(-Math.max(1, Number(config.swingBars)));
  const swingReference = swingWindow.length
    ? (sign === 1 ? Math.min(...swingWindow.map(bar => bar.low)) : Math.max(...swingWindow.map(bar => bar.high)))
    : null;
  const structureBroken = finite(swingReference)
    ? (sign === 1 ? current.close < swingReference : current.close > swingReference)
    : false;
  const fastTrendHealthy = finite(fast) && finite(slow) ? (sign === 1 ? fast >= slow : fast <= slow) : true;
  const closeVsFastHealthy = finite(fast) ? (sign === 1 ? current.close >= fast : current.close <= fast) : true;
  const vwapHealthy = finite(vwap) ? (sign === 1 ? current.close >= vwap : current.close <= vwap) : true;
  const momentumHealthy = momentumPct > 0;
  const positiveFromEntry = directionalReturnPct(entryPrice, current.close, sign) >= 0;
  const pullbackDistance = sign === 1 ? Math.max(0, Number(priorBest) - current.close) : Math.max(0, current.close - Number(priorBest));
  const pullbackAtr = finite(priorAtr) && Number(priorAtr) > 0 ? pullbackDistance / Number(priorAtr) : 0;
  const pullbackHealthy = pullbackAtr <= Number(config.healthyPullbackAtr);

  const healthyFlags = Object.freeze({
    structureHealthy: !structureBroken,
    fastTrendHealthy,
    closeVsFastHealthy,
    vwapHealthy,
    momentumHealthy,
    pullbackHealthy,
    positiveFromEntry,
  });
  const healthyVotes = Object.values(healthyFlags).filter(Boolean).length;
  const damageVotes = [
    structureBroken ? 2 : 0,
    fastTrendHealthy ? 0 : 1,
    closeVsFastHealthy ? 0 : 1,
    vwapHealthy ? 0 : 1,
    momentumHealthy ? 0 : 1,
    pullbackHealthy ? 0 : 1,
  ].reduce((sum, value) => sum + value, 0);

  return Object.freeze({
    close: current.close,
    fast,
    slow,
    vwap,
    momentumPct,
    swingReference,
    pullbackAtr,
    structureBroken,
    fastTrendHealthy,
    closeVsFastHealthy,
    vwapHealthy,
    momentumHealthy,
    positiveFromEntry,
    pullbackHealthy,
    healthyVotes,
    damageVotes,
    healthyFlags,
  });
}

export function transitionTradeManagementState(input = {}, config = DEFAULT_STATE_MACHINE_CONFIG) {
  const priorState = input.priorState ?? TRADE_MANAGEMENT_STATES.HOLD;
  if (!Object.values(TRADE_MANAGEMENT_STATES).includes(priorState) || priorState === TRADE_MANAGEMENT_STATES.EXIT) {
    throw new Error('priorState must be STRONG_HOLD, HOLD, or CAUTION');
  }
  const damageVotes = Math.max(0, Number(input.damageVotes || 0));
  const healthyVotes = Math.max(0, Number(input.healthyVotes || 0));
  const structureBroken = input.structureBroken === true;
  const barsHeld = Math.max(0, Number(input.barsHeld || 0));
  const warningStreak = damageVotes >= Number(config.cautionEnterDamageVotes)
    ? Math.max(0, Number(input.warningStreak || 0)) + 1
    : 0;
  const severeNow = structureBroken || damageVotes >= Number(config.severeBreakdownDamageVotes);
  const severeStreak = severeNow ? Math.max(0, Number(input.severeStreak || 0)) + 1 : 0;
  const recoveryNow = !structureBroken && healthyVotes >= Number(config.recoveryHealthyVotes);
  const recoveryStreak = recoveryNow ? Math.max(0, Number(input.recoveryStreak || 0)) + 1 : 0;
  const priorCautionBars = priorState === TRADE_MANAGEMENT_STATES.CAUTION ? Math.max(0, Number(input.barsInCaution || 0)) : 0;
  const barsInCaution = priorState === TRADE_MANAGEMENT_STATES.CAUTION ? priorCautionBars + 1 : 0;
  const softExitEligible = barsHeld >= Number(config.minBarsBeforeStateExit);

  if (softExitEligible && severeStreak >= Number(config.severeBreakdownConfirmBars)) {
    return Object.freeze({
      nextState: TRADE_MANAGEMENT_STATES.EXIT,
      reason: structureBroken ? 'CONFIRMED_STRUCTURE_FAILURE' : 'CONFIRMED_SEVERE_BREAKDOWN',
      exit: true,
      warningStreak,
      severeStreak,
      recoveryStreak,
      barsInCaution,
    });
  }

  if (priorState === TRADE_MANAGEMENT_STATES.CAUTION) {
    if (recoveryStreak >= Number(config.recoveryConfirmBars)) {
      const nextState = healthyVotes >= Number(config.strongHoldMinHealthyVotes)
        ? TRADE_MANAGEMENT_STATES.STRONG_HOLD
        : TRADE_MANAGEMENT_STATES.HOLD;
      return Object.freeze({ nextState, reason: 'CAUTION_RECOVERED', exit: false, warningStreak, severeStreak, recoveryStreak, barsInCaution: 0 });
    }
    if (softExitEligible
      && damageVotes >= Number(config.cautionExitDamageVotes)
      && barsInCaution >= Number(config.cautionConfirmBars)) {
      return Object.freeze({
        nextState: TRADE_MANAGEMENT_STATES.EXIT,
        reason: 'PERSISTENT_CHART_BREAKDOWN',
        exit: true,
        warningStreak,
        severeStreak,
        recoveryStreak,
        barsInCaution,
      });
    }
    if (damageVotes < Number(config.cautionEnterDamageVotes)) {
      return Object.freeze({ nextState: TRADE_MANAGEMENT_STATES.HOLD, reason: 'CAUTION_EASED', exit: false, warningStreak, severeStreak, recoveryStreak, barsInCaution: 0 });
    }
    return Object.freeze({ nextState: TRADE_MANAGEMENT_STATES.CAUTION, reason: 'CAUTION_PERSISTS', exit: false, warningStreak, severeStreak, recoveryStreak, barsInCaution });
  }

  if (damageVotes >= Number(config.cautionEnterDamageVotes)) {
    return Object.freeze({
      nextState: TRADE_MANAGEMENT_STATES.CAUTION,
      reason: 'ENTER_CAUTION',
      exit: false,
      warningStreak,
      severeStreak,
      recoveryStreak,
      barsInCaution: 1,
    });
  }

  if (healthyVotes >= Number(config.strongHoldMinHealthyVotes)) {
    return Object.freeze({
      nextState: TRADE_MANAGEMENT_STATES.STRONG_HOLD,
      reason: 'TREND_HEALTHY',
      exit: false,
      warningStreak,
      severeStreak,
      recoveryStreak,
      barsInCaution: 0,
    });
  }

  return Object.freeze({
    nextState: TRADE_MANAGEMENT_STATES.HOLD,
    reason: 'HOLD_STRUCTURE_INTACT',
    exit: false,
    warningStreak,
    severeStreak,
    recoveryStreak,
    barsInCaution: 0,
  });
}

function summarizeExit({ entryPrice, sign, observed, excursionBars = observed, exitPrice, exitReason, exitTimestamp, roundTripCostPct, decisions, stateVisitCounts, intrabarExit = false }) {
  const grossReturnPct = directionalReturnPct(entryPrice, exitPrice, sign);
  const netReturnPct = grossReturnPct - Number(roundTripCostPct || 0);
  const favorablePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.high : bar.low)];
  const adversePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.low : bar.high)];
  const favorable = sign === 1 ? Math.max(...favorablePrices) : Math.min(...favorablePrices);
  const adverse = sign === 1 ? Math.min(...adversePrices) : Math.max(...adversePrices);
  const mfePct = Math.max(0, directionalReturnPct(entryPrice, favorable, sign));
  const maePct = Math.min(0, directionalReturnPct(entryPrice, adverse, sign));
  return Object.freeze({
    phase: '57.p23.4',
    status: 'TRADE_MANAGEMENT_STATE_MACHINE_EVALUATED',
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
    captureRatio: mfePct > 0 ? clamp(grossReturnPct / mfePct, -5, 5) : null,
    decisions: Object.freeze(decisions),
    stateVisitCounts: Object.freeze({ ...stateVisitCounts }),
    fixedTimeExitPrimary: false,
    maxHoldOnlySafetyGuard: true,
    chartAware: true,
    stateful: true,
    pointInTimeSequential: true,
    preBarStopsUseCompletedBarsOnly: true,
    currentBarCloseUsedForStateTransition: true,
    futureBarsUsedBeforeDecision: false,
    intrabarExit,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_4_SAFETY,
  });
}

export function simulateTradeManagementStateMachine(row = {}, options = {}) {
  const config = Object.freeze({ ...DEFAULT_STATE_MACHINE_CONFIG, ...(options?.config ?? options) });
  const entryPrice = Number(row?.entryPrice);
  if (!finite(entryPrice) || entryPrice <= 0) return null;
  const sign = directionSign(row?.signalDirection);
  const contextBars = normalizeBars(row?.contextBars ?? row?.historyBars ?? []);
  const futureBars = normalizeBars(row?.futureBars ?? row?.path ?? []);
  if (!futureBars.length) return null;
  if (contextBars.length && contextBars.at(-1).timestamp >= futureBars[0].timestamp) {
    throw new Error('context bars must be strictly earlier than managed future bars');
  }
  const sessionDate = row?.sessionDate == null ? null : String(row.sessionDate);
  if (sessionDate && futureBars.some(bar => jstDate(bar.timestamp) !== sessionDate)) {
    throw new Error('trade management state machine forbids cross-session future bars');
  }

  const maxHoldBars = Math.max(1, Number(config.maxHoldBars) || futureBars.length);
  const roundTripCostPct = Math.max(0, Number(config.roundTripCostPct) || 0);
  const decisions = [];
  const observed = [];
  const stateVisitCounts = {
    [TRADE_MANAGEMENT_STATES.STRONG_HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.CAUTION]: 0,
  };
  let state = TRADE_MANAGEMENT_STATES.HOLD;
  let priorBest = entryPrice;
  let priorBestReturnPct = 0;
  let warningStreak = 0;
  let severeStreak = 0;
  let recoveryStreak = 0;
  let barsInCaution = 0;

  for (let index = 0; index < Math.min(futureBars.length, maxHoldBars); index += 1) {
    const bar = futureBars[index];
    const priorHistory = [...contextBars, ...observed];
    const priorAtrRaw = rollingAtr(priorHistory, Math.max(2, Number(config.atrBars)));
    const priorAtr = finite(priorAtrRaw) && priorAtrRaw > 0 ? priorAtrRaw : entryPrice * 0.005;
    const activeStop = preBarStop({ entryPrice, sign, priorAtr, priorBest, priorBestReturnPct, state, config });
    const fill = stopFill(bar, activeStop.stopPrice, sign);

    if (finite(fill)) {
      observed.push(bar);
      decisions.push(Object.freeze({
        index,
        timestamp: bar.timestamp,
        priorState: state,
        nextState: TRADE_MANAGEMENT_STATES.EXIT,
        action: 'EXIT',
        reason: activeStop.reason,
        stopPrice: activeStop.stopPrice,
        hardStopPrice: activeStop.hardStopPrice,
        protectionStop: activeStop.protectionStop,
        stopWasFixedBeforeCurrentBar: true,
      }));
      return summarizeExit({
        entryPrice,
        sign,
        observed,
        excursionBars: observed.slice(0, -1),
        exitPrice: Number(fill),
        exitReason: activeStop.reason,
        exitTimestamp: bar.timestamp,
        roundTripCostPct,
        decisions,
        stateVisitCounts,
        intrabarExit: true,
      });
    }

    observed.push(bar);
    const history = [...contextBars, ...observed];
    const health = deriveTradeManagementHealth({ history, entryPrice, sign, priorBest, priorAtr, config });
    const transition = transitionTradeManagementState({
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
      health,
      transition,
    }));

    if (transition.exit) {
      return summarizeExit({
        entryPrice,
        sign,
        observed,
        exitPrice: bar.close,
        exitReason: transition.reason,
        exitTimestamp: bar.timestamp,
        roundTripCostPct,
        decisions,
        stateVisitCounts,
      });
    }

    state = transition.nextState;
    stateVisitCounts[state] += 1;
    const favorableNow = sign === 1 ? bar.high : bar.low;
    if ((sign === 1 && favorableNow > priorBest) || (sign === -1 && favorableNow < priorBest)) priorBest = favorableNow;
    priorBestReturnPct = Math.max(priorBestReturnPct, directionalReturnPct(entryPrice, priorBest, sign));

    if (index === futureBars.length - 1) {
      decisions.push(Object.freeze({
        index,
        timestamp: bar.timestamp,
        priorState: state,
        nextState: TRADE_MANAGEMENT_STATES.EXIT,
        action: 'EXIT',
        reason: 'SESSION_OR_DATA_END',
      }));
      return summarizeExit({
        entryPrice,
        sign,
        observed,
        exitPrice: bar.close,
        exitReason: 'SESSION_OR_DATA_END',
        exitTimestamp: bar.timestamp,
        roundTripCostPct,
        decisions,
        stateVisitCounts,
      });
    }
  }

  const last = observed.at(-1);
  if (!last) return null;
  decisions.push(Object.freeze({
    index: observed.length - 1,
    timestamp: last.timestamp,
    priorState: state,
    nextState: TRADE_MANAGEMENT_STATES.EXIT,
    action: 'EXIT',
    reason: 'MAX_HOLD_SAFETY_GUARD',
  }));
  return summarizeExit({
    entryPrice,
    sign,
    observed,
    exitPrice: last.close,
    exitReason: 'MAX_HOLD_SAFETY_GUARD',
    exitTimestamp: last.timestamp,
    roundTripCostPct,
    decisions,
    stateVisitCounts,
  });
}

export function evaluateTradeManagementStateMachine(rows = [], options = {}) {
  const outcomes = (Array.isArray(rows) ? rows : [])
    .map(row => simulateTradeManagementStateMachine(row, options))
    .filter(Boolean);
  const n = outcomes.length;
  const positive = outcomes.filter(row => row.netReturnPct > 0).reduce((sum, row) => sum + row.netReturnPct, 0);
  const negative = -outcomes.filter(row => row.netReturnPct < 0).reduce((sum, row) => sum + row.netReturnPct, 0);
  const exitReasonCounts = {};
  const stateVisitCounts = {
    [TRADE_MANAGEMENT_STATES.STRONG_HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.HOLD]: 0,
    [TRADE_MANAGEMENT_STATES.CAUTION]: 0,
  };
  for (const outcome of outcomes) {
    exitReasonCounts[outcome.exitReason] = (exitReasonCounts[outcome.exitReason] || 0) + 1;
    for (const [state, count] of Object.entries(outcome.stateVisitCounts)) stateVisitCounts[state] += Number(count || 0);
  }
  return Object.freeze({
    phase: '57.p23.4',
    status: n ? 'TRADE_MANAGEMENT_STATE_MACHINE_RESEARCH_READY' : 'NO_STATE_MACHINE_OUTCOMES',
    signalCount: n,
    hitRate: n ? outcomes.filter(row => row.netReturnPct > 0).length / n : null,
    netAverageReturnPct: n ? mean(outcomes.map(row => row.netReturnPct)) : null,
    grossAverageReturnPct: n ? mean(outcomes.map(row => row.grossReturnPct)) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: n ? mean(outcomes.map(row => row.barsHeld)) : null,
    averageMfePct: n ? mean(outcomes.map(row => row.mfePct)) : null,
    averageMaePct: n ? mean(outcomes.map(row => row.maePct)) : null,
    exitReasonCounts: Object.freeze(exitReasonCounts),
    stateVisitCounts: Object.freeze(stateVisitCounts),
    outcomes: Object.freeze(outcomes),
    fixedTimeExitPrimary: false,
    maxHoldOnlySafetyGuard: true,
    chartAware: true,
    stateful: true,
    pointInTimeSequential: true,
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_4_SAFETY,
  });
}

export default {
  TRADE_MANAGEMENT_STATES,
  DEFAULT_STATE_MACHINE_CONFIG,
  deriveTradeManagementHealth,
  transitionTradeManagementState,
  simulateTradeManagementStateMachine,
  evaluateTradeManagementStateMachine,
};
