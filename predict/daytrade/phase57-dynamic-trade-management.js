export const PHASE57_P23_2_SAFETY = Object.freeze({
  mode: 'PHASE57_DYNAMIC_TRADE_MANAGEMENT_READ_ONLY_RESEARCH',
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

export const DEFAULT_DYNAMIC_EXIT_CONFIG = Object.freeze({
  fastBars: 3,
  slowBars: 8,
  momentumBars: 3,
  swingBars: 3,
  atrBars: 8,
  hardStopAtr: 1.5,
  profitProtectActivationAtr: 1.5,
  profitProtectGivebackAtr: 1.0,
  minBreakdownVotes: 2,
  minBarsBeforeSoftExit: 2,
  maxHoldBars: 60,
  roundTripCostPct: 0.05,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const avg = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
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
  if (bar.high < Math.max(bar.open, bar.close, bar.low) || bar.low > Math.min(bar.open, bar.close, bar.high)) throw new Error('invalid OHLC ordering');
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

function trueRange(bar, previousClose) {
  return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
}

function directionSign(direction) {
  if (direction === 1 || direction === 'LONG') return 1;
  if (direction === 0 || direction === -1 || direction === 'SHORT') return -1;
  throw new TypeError('signalDirection must be LONG/SHORT or 1/0');
}

function directionalReturnPct(entry, price, sign) {
  return (Number(price) / Number(entry) - 1) * 100 * sign;
}

function rollingAtr(history, period) {
  if (!history.length) return null;
  const trs = history.map((bar, index) => trueRange(bar, index ? history[index - 1].close : bar.open));
  return avg(trs.slice(-period));
}

function rollingVwap(history) {
  const volume = history.reduce((sum, bar) => sum + Math.max(0, Number(bar.volume || 0)), 0);
  if (volume <= 0) return history.at(-1)?.close ?? null;
  return history.reduce((sum, bar) => sum + ((bar.high + bar.low + bar.close) / 3) * Math.max(0, Number(bar.volume || 0)), 0) / volume;
}

function chartState(history, sign, config) {
  const closes = history.map(bar => bar.close);
  const current = history.at(-1);
  const fast = avg(closes.slice(-Math.max(1, config.fastBars)));
  const slow = avg(closes.slice(-Math.max(2, config.slowBars)));
  const momentumLookback = Math.min(Math.max(1, config.momentumBars), Math.max(1, closes.length - 1));
  const momentumReference = closes[Math.max(0, closes.length - 1 - momentumLookback)];
  const momentumPct = directionalReturnPct(momentumReference, current.close, sign);
  const vwap = rollingVwap(history);
  const atr = rollingAtr(history, Math.max(2, config.atrBars));
  const prior = history.slice(0, -1);
  const swingWindow = prior.slice(-Math.max(1, config.swingBars));
  const swingSupport = swingWindow.length ? (sign === 1 ? Math.min(...swingWindow.map(bar => bar.low)) : Math.max(...swingWindow.map(bar => bar.high))) : null;
  const structureBroken = finite(swingSupport) ? (sign === 1 ? current.close < swingSupport : current.close > swingSupport) : false;
  const fastTrendHealthy = finite(fast) && finite(slow) ? (sign === 1 ? fast >= slow : fast <= slow) : true;
  const closeVsFastHealthy = finite(fast) ? (sign === 1 ? current.close >= fast : current.close <= fast) : true;
  const vwapHealthy = finite(vwap) ? (sign === 1 ? current.close >= vwap : current.close <= vwap) : true;
  const momentumHealthy = momentumPct > 0;
  return Object.freeze({
    close: current.close,
    fast,
    slow,
    vwap,
    atr,
    momentumPct,
    swingSupport,
    structureBroken,
    fastTrendHealthy,
    closeVsFastHealthy,
    vwapHealthy,
    momentumHealthy,
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

function activePreBarStop({ entryPrice, sign, priorAtr, priorBest, priorBestReturnPct, config }) {
  const hardStopPrice = sign === 1
    ? entryPrice - priorAtr * Number(config.hardStopAtr)
    : entryPrice + priorAtr * Number(config.hardStopAtr);
  const priorAtrPct = priorAtr / entryPrice * 100;
  const protectionActive = priorBestReturnPct >= priorAtrPct * Number(config.profitProtectActivationAtr);
  const protectionStop = protectionActive
    ? (sign === 1
      ? priorBest - priorAtr * Number(config.profitProtectGivebackAtr)
      : priorBest + priorAtr * Number(config.profitProtectGivebackAtr))
    : null;

  if (!finite(protectionStop)) return Object.freeze({ stopPrice: hardStopPrice, reason: 'ATR_HARD_STOP', hardStopPrice, protectionStop: null, protectionActive: false });
  const protectionIsTighter = sign === 1 ? protectionStop > hardStopPrice : protectionStop < hardStopPrice;
  return Object.freeze({
    stopPrice: protectionIsTighter ? protectionStop : hardStopPrice,
    reason: protectionIsTighter ? 'PRIOR_PEAK_PROFIT_PROTECTION' : 'ATR_HARD_STOP',
    hardStopPrice,
    protectionStop,
    protectionActive: true,
  });
}

function summarizeExit({
  entryPrice,
  sign,
  observed,
  excursionBars = observed,
  exitPrice,
  exitReason,
  exitTimestamp,
  roundTripCostPct,
  decisions,
  intrabarExit = false,
}) {
  const grossReturnPct = directionalReturnPct(entryPrice, exitPrice, sign);
  const netReturnPct = grossReturnPct - Number(roundTripCostPct || 0);
  const favorablePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.high : bar.low)];
  const adversePrices = [entryPrice, exitPrice, ...excursionBars.map(bar => sign === 1 ? bar.low : bar.high)];
  const favorable = sign === 1 ? Math.max(...favorablePrices) : Math.min(...favorablePrices);
  const adverse = sign === 1 ? Math.min(...adversePrices) : Math.max(...adversePrices);
  const mfePct = Math.max(0, directionalReturnPct(entryPrice, favorable, sign));
  const maePct = Math.min(0, directionalReturnPct(entryPrice, adverse, sign));
  return Object.freeze({
    phase: '57.p23.2',
    status: 'DYNAMIC_CHART_EXIT_EVALUATED',
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
    timeExitIsPrimary: false,
    chartAware: true,
    pointInTimeSequential: true,
    currentBarCloseUsedForSoftExit: true,
    preBarStopsUseCompletedBarsOnly: true,
    intrabarExit,
    intrabarExcursionUsesCompletedBarsOnly: intrabarExit,
    futureBarsUsedBeforeDecision: false,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_2_SAFETY,
  });
}

export function simulateDynamicTradeManagement(row = {}, options = {}) {
  const config = Object.freeze({ ...DEFAULT_DYNAMIC_EXIT_CONFIG, ...(options?.config ?? options) });
  const entryPrice = Number(row?.entryPrice);
  if (!finite(entryPrice) || entryPrice <= 0) return null;
  const sign = directionSign(row?.signalDirection);
  const contextBars = normalizeBars(row?.contextBars ?? row?.historyBars ?? []);
  const futureBars = normalizeBars(row?.futureBars ?? row?.path ?? []);
  if (!futureBars.length) return null;
  if (contextBars.length && contextBars.at(-1).timestamp >= futureBars[0].timestamp) throw new Error('context bars must be strictly earlier than managed future bars');

  const sessionDate = row?.sessionDate == null ? null : String(row.sessionDate);
  if (sessionDate && futureBars.some(bar => jstDate(bar.timestamp) !== sessionDate)) throw new Error('dynamic trade management forbids cross-session future bars');

  const maxHoldBars = Math.max(1, Number(config.maxHoldBars) || futureBars.length);
  const roundTripCostPct = Math.max(0, Number(config.roundTripCostPct) || 0);
  const decisions = [];
  const observed = [];
  let priorBest = entryPrice;
  let priorBestReturnPct = 0;

  for (let index = 0; index < Math.min(futureBars.length, maxHoldBars); index += 1) {
    const bar = futureBars[index];
    const priorHistory = [...contextBars, ...observed];
    const priorAtrRaw = rollingAtr(priorHistory, Math.max(2, config.atrBars));
    const priorAtr = finite(priorAtrRaw) && priorAtrRaw > 0 ? priorAtrRaw : entryPrice * 0.005;
    const activeStop = activePreBarStop({ entryPrice, sign, priorAtr, priorBest, priorBestReturnPct, config });
    const preBarStopFill = stopFill(bar, activeStop.stopPrice, sign);

    if (finite(preBarStopFill)) {
      observed.push(bar);
      decisions.push(Object.freeze({
        index,
        timestamp: bar.timestamp,
        action: 'EXIT',
        reason: activeStop.reason,
        preBarAtr: priorAtr,
        priorBest,
        hardStopPrice: activeStop.hardStopPrice,
        protectionStop: activeStop.protectionStop,
        stopPrice: activeStop.stopPrice,
        stopWasFixedBeforeCurrentBar: true,
      }));
      return summarizeExit({
        entryPrice,
        sign,
        observed,
        excursionBars: observed.slice(0, -1),
        exitPrice: Number(preBarStopFill),
        exitReason: activeStop.reason,
        exitTimestamp: bar.timestamp,
        roundTripCostPct,
        decisions,
        intrabarExit: true,
      });
    }

    // The whole current 5m bar has now completed without hitting a pre-existing stop. Only at this
    // point may its close/high/low update chart state and the favorable extreme for later bars.
    observed.push(bar);
    const history = [...contextBars, ...observed];
    const state = chartState(history, sign, config);
    const breakdownVotes = [
      state.structureBroken,
      !state.fastTrendHealthy,
      !state.closeVsFastHealthy,
      !state.vwapHealthy,
      !state.momentumHealthy,
    ].filter(Boolean).length;

    if (index + 1 >= Number(config.minBarsBeforeSoftExit) && breakdownVotes >= Number(config.minBreakdownVotes)) {
      let reason = 'CHART_BREAKDOWN';
      if (state.structureBroken) reason = 'STRUCTURE_BREAK';
      else if (!state.vwapHealthy && !state.momentumHealthy) reason = 'VWAP_MOMENTUM_LOSS';
      else if (!state.fastTrendHealthy && !state.closeVsFastHealthy) reason = 'TREND_DECAY';
      decisions.push(Object.freeze({ index, timestamp: bar.timestamp, action: 'EXIT', reason, breakdownVotes, state }));
      return summarizeExit({ entryPrice, sign, observed, exitPrice: bar.close, exitReason: reason, exitTimestamp: bar.timestamp, roundTripCostPct, decisions });
    }

    decisions.push(Object.freeze({ index, timestamp: bar.timestamp, action: 'HOLD', reason: 'CHART_STRUCTURE_INTACT', breakdownVotes, state }));
    const favorableNow = sign === 1 ? bar.high : bar.low;
    if ((sign === 1 && favorableNow > priorBest) || (sign === -1 && favorableNow < priorBest)) priorBest = favorableNow;
    priorBestReturnPct = Math.max(priorBestReturnPct, directionalReturnPct(entryPrice, priorBest, sign));

    const isLastAvailableBar = index === futureBars.length - 1;
    if (isLastAvailableBar) {
      decisions.push(Object.freeze({ index, timestamp: bar.timestamp, action: 'EXIT', reason: 'SESSION_OR_DATA_END', state }));
      return summarizeExit({ entryPrice, sign, observed, exitPrice: bar.close, exitReason: 'SESSION_OR_DATA_END', exitTimestamp: bar.timestamp, roundTripCostPct, decisions });
    }
  }

  const last = observed.at(-1);
  if (!last) return null;
  decisions.push(Object.freeze({ index: observed.length - 1, timestamp: last.timestamp, action: 'EXIT', reason: 'MAX_HOLD_SAFETY_GUARD' }));
  return summarizeExit({ entryPrice, sign, observed, exitPrice: last.close, exitReason: 'MAX_HOLD_SAFETY_GUARD', exitTimestamp: last.timestamp, roundTripCostPct, decisions });
}

export function evaluateDynamicTradeManagement(rows = [], options = {}) {
  const outcomes = (Array.isArray(rows) ? rows : []).map(row => simulateDynamicTradeManagement(row, options)).filter(Boolean);
  const n = outcomes.length;
  const positive = outcomes.filter(row => row.netReturnPct > 0).reduce((sum, row) => sum + row.netReturnPct, 0);
  const negative = -outcomes.filter(row => row.netReturnPct < 0).reduce((sum, row) => sum + row.netReturnPct, 0);
  const exitReasonCounts = {};
  for (const outcome of outcomes) exitReasonCounts[outcome.exitReason] = (exitReasonCounts[outcome.exitReason] || 0) + 1;
  const captureRatios = outcomes.map(row => row.captureRatio).filter(finite);
  return Object.freeze({
    phase: '57.p23.2',
    status: n ? 'DYNAMIC_TRADE_MANAGEMENT_RESEARCH_READY' : 'NO_DYNAMIC_EXIT_OUTCOMES',
    signalCount: n,
    hitRate: n ? outcomes.filter(row => row.netReturnPct > 0).length / n : null,
    netAverageReturnPct: n ? avg(outcomes.map(row => row.netReturnPct)) : null,
    grossAverageReturnPct: n ? avg(outcomes.map(row => row.grossReturnPct)) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: n ? avg(outcomes.map(row => row.barsHeld)) : null,
    averageMfePct: n ? avg(outcomes.map(row => row.mfePct)) : null,
    averageMaePct: n ? avg(outcomes.map(row => row.maePct)) : null,
    averageCaptureRatio: captureRatios.length ? avg(captureRatios) : null,
    exitReasonCounts: Object.freeze(exitReasonCounts),
    outcomes: Object.freeze(outcomes),
    fixedTimeExitPrimary: false,
    maxHoldOnlySafetyGuard: true,
    chartAware: true,
    pointInTimeSequential: true,
    preBarStopsUseCompletedBarsOnly: true,
    sameSessionOnly: true,
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_2_SAFETY,
  });
}

export default { DEFAULT_DYNAMIC_EXIT_CONFIG, simulateDynamicTradeManagement, evaluateDynamicTradeManagement };
