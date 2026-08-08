import {
  analyzeIntradayMarket,
  calculateIntradayVwapSeries,
  normalizeIntradayCandles,
} from './intraday-market.js';

export const PHASE54_TIMEFRAMES = Object.freeze([5, 15, 60]);

export const PHASE54_SAFETY = Object.freeze({
  mode: 'INTRADAY_INTELLIGENCE_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  humanApprovalRequired: true,
});

export const DEFAULT_PHASE54_POLICY = Object.freeze({
  openingRangeBars: Object.freeze({ 5: 6, 15: 2, 60: 1 }),
  timeframeWeights: Object.freeze({ 5: 0.25, 15: 0.35, 60: 0.4 }),
  marketPolicy: Object.freeze({
    5: Object.freeze({ minimumSessionBars: 6, minimumHistoryBars: 30, volumeLookback: 20, breakoutLookback: 20, atrPeriod: 14, maximumBarAgeSeconds: 12 * 60 }),
    15: Object.freeze({ minimumSessionBars: 4, minimumHistoryBars: 21, volumeLookback: 20, breakoutLookback: 20, atrPeriod: 14, maximumBarAgeSeconds: 25 * 60 }),
    60: Object.freeze({ minimumSessionBars: 2, minimumHistoryBars: 10, volumeLookback: 8, breakoutLookback: 8, atrPeriod: 5, maximumBarAgeSeconds: 80 * 60 }),
  }),
});

function finite(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function round(value, digits = 4) {
  if (!finite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function closed(candles = []) {
  return normalizeIntradayCandles(candles).filter((row) => row.isClosed !== false);
}

function sessionGroups(candles = []) {
  const groups = new Map();
  closed(candles).forEach((row) => {
    const key = row.sessionDate || 'unknown';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  return groups;
}

export function analyzeIntradaySessionStructure(candles = [], { openingRangeBars = 2 } = {}) {
  const groups = sessionGroups(candles);
  const dates = Array.from(groups.keys());
  const current = dates.length ? groups.get(dates.at(-1)) : [];
  const previous = dates.length > 1 ? groups.get(dates.at(-2)) : [];

  if (!current?.length) {
    return Object.freeze({ ready: false, reason: 'NO_CLOSED_SESSION', sessionDate: null });
  }

  const first = current[0];
  const latest = current.at(-1);
  const previousClose = previous?.length ? Number(previous.at(-1).close) : null;
  const count = Math.max(1, Math.min(current.length, Number(openingRangeBars) || 1));
  const openingRows = current.slice(0, count);
  const openingHigh = Math.max(...openingRows.map((row) => Number(row.high)));
  const openingLow = Math.min(...openingRows.map((row) => Number(row.low)));
  const sessionHigh = Math.max(...current.map((row) => Number(row.high)));
  const sessionLow = Math.min(...current.map((row) => Number(row.low)));
  const vwap = calculateIntradayVwapSeries(current).at(-1)?.vwap ?? null;
  const gapPercent = finite(previousClose) && previousClose > 0
    ? ((Number(first.open) / previousClose) - 1) * 100
    : null;
  const openingRangeBreakout = Number(latest.close) > openingHigh
    ? 'up'
    : Number(latest.close) < openingLow
      ? 'down'
      : 'inside';

  return Object.freeze({
    ready: true,
    sessionDate: latest.sessionDate,
    barCount: current.length,
    open: Number(first.open),
    currentPrice: Number(latest.close),
    previousClose,
    gapPercent: round(gapPercent),
    openingRangeBars: count,
    openingHigh: round(openingHigh),
    openingLow: round(openingLow),
    openingRangeBreakout,
    sessionHigh: round(sessionHigh),
    sessionLow: round(sessionLow),
    vwap: round(vwap),
    aboveVwap: finite(vwap) ? Number(latest.close) > Number(vwap) : null,
  });
}

function directionValue(direction) {
  if (direction === '強気') return 1;
  if (direction === '弱気') return -1;
  return 0;
}

export function analyzePhase54IntradayIntelligence(
  candlesByTimeframe = {},
  { nowSeconds = Math.floor(Date.now() / 1000), policy = {} } = {},
) {
  const weights = { ...DEFAULT_PHASE54_POLICY.timeframeWeights, ...(policy.timeframeWeights || {}) };
  const openingRangeBars = { ...DEFAULT_PHASE54_POLICY.openingRangeBars, ...(policy.openingRangeBars || {}) };
  const marketPolicy = { ...DEFAULT_PHASE54_POLICY.marketPolicy, ...(policy.marketPolicy || {}) };

  const timeframes = PHASE54_TIMEFRAMES.map((timeframe) => {
    const rows = candlesByTimeframe?.[timeframe] || candlesByTimeframe?.[String(timeframe)] || [];
    const market = analyzeIntradayMarket(rows, {
      nowSeconds,
      policy: marketPolicy[timeframe] || {},
    });
    const structure = analyzeIntradaySessionStructure(rows, {
      openingRangeBars: openingRangeBars[timeframe],
    });
    return Object.freeze({ timeframeMinutes: timeframe, market, structure });
  });

  const usable = timeframes.filter((item) => item.market?.ready && !item.market?.marketBlocked);
  const weightTotal = usable.reduce((sum, item) => sum + Number(weights[item.timeframeMinutes] || 0), 0);
  const alignmentScore = weightTotal > 0
    ? usable.reduce((sum, item) => sum + directionValue(item.market.direction) * Number(weights[item.timeframeMinutes] || 0), 0) / weightTotal
    : 0;
  const bullishFrames = usable.filter((item) => item.market.direction === '強気').map((item) => item.timeframeMinutes);
  const bearishFrames = usable.filter((item) => item.market.direction === '弱気').map((item) => item.timeframeMinutes);

  let bias = '中立';
  if (alignmentScore >= 0.35) bias = '強気';
  if (alignmentScore <= -0.35) bias = '弱気';

  const blockers = [];
  if (!usable.length) blockers.push('NO_READY_TIMEFRAME');
  if (usable.length < 2) blockers.push('INSUFFICIENT_TIMEFRAME_CONFIRMATION');
  if (bullishFrames.length && bearishFrames.length) blockers.push('TIMEFRAME_CONFLICT');

  return Object.freeze({
    phase: '54',
    status: usable.length >= 2 ? 'INTRADAY_INTELLIGENCE_READY' : 'OBSERVE',
    bias,
    alignmentScore: round(alignmentScore, 3),
    bullishFrames,
    bearishFrames,
    usableTimeframes: usable.map((item) => item.timeframeMinutes),
    blockers,
    timeframes,
    featureSet: Object.freeze([
      'multi_timeframe_5m_15m_60m',
      'session_vwap',
      'session_aware_volume',
      'opening_range',
      'overnight_gap',
      'breakout_reclaim_pullback',
      'atr',
      'freshness_and_data_quality',
    ]),
    reviewOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    humanApprovalRequired: true,
    transmitted: false,
    safety: PHASE54_SAFETY,
  });
}
