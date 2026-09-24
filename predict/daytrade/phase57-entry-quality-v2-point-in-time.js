import { buildEntryQualityV2ResearchVector } from './phase57-entry-quality-v2-research.js';

export const ENTRY_V2_POINT_IN_TIME_POLICY = Object.freeze({
  mode: 'ENTRY_V2_STRICT_POINT_IN_TIME_RESEARCH_ONLY',
  intradayBarMinutes: 5,
  requirePriorSessionDailyBars: true,
  requireCompletedIntradayBars: true,
  rejectSameSessionDailyBar: true,
  automaticPromotionAllowed: false,
});

function parseTimestamp(value, label) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error(`${label}_INVALID_TIMESTAMP`);
  return ms;
}

function jstSessionDate(value) {
  const ms = parseTimestamp(value, 'ENTRY_V2_PIT');
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date(ms));
  const map = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day}`;
}

function normalizeBar(bar, label) {
  const timestamp = bar?.timestamp ?? bar?.time ?? bar?.at;
  const timestampMs = parseTimestamp(timestamp, label);
  const normalized = {
    ...bar,
    timestamp: new Date(timestampMs).toISOString(),
    open: Number(bar?.open),
    high: Number(bar?.high),
    low: Number(bar?.low),
    close: Number(bar?.close),
    volume: Number(bar?.volume ?? 0),
  };
  if (![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)) {
    throw new Error(`${label}_INVALID_OHLCV`);
  }
  if (normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.volume < 0) {
    throw new Error(`${label}_INVALID_OHLCV`);
  }
  return Object.freeze(normalized);
}

function assertStrictlyIncreasingUnique(bars, label) {
  for (let i = 1; i < bars.length; i += 1) {
    const previous = Date.parse(bars[i - 1].timestamp);
    const current = Date.parse(bars[i].timestamp);
    if (current === previous) throw new Error(`${label}_DUPLICATE_TIMESTAMP`);
    if (current < previous) throw new Error(`${label}_NON_MONOTONIC_TIMESTAMP`);
  }
}

export function prepareEntryV2PriorDailyBars({ dailyBars = [], asOf }) {
  const decisionSession = jstSessionDate(asOf);
  const normalized = dailyBars
    .map(bar => normalizeBar(bar, 'ENTRY_V2_DAILY'))
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  assertStrictlyIncreasingUnique(normalized, 'ENTRY_V2_DAILY');

  for (const bar of normalized) {
    if (jstSessionDate(bar.timestamp) >= decisionSession) {
      throw new Error('ENTRY_V2_DAILY_NOT_PRIOR_SESSION');
    }
  }
  return Object.freeze(normalized);
}

export function prepareEntryV2ClosedIntradayPrefix({ intradayBars = [], asOf, barMinutes = 5 }) {
  const asOfMs = parseTimestamp(asOf, 'ENTRY_V2_AS_OF');
  const decisionSession = jstSessionDate(asOf);
  const closeLagMs = Number(barMinutes) * 60_000;
  if (!(closeLagMs > 0)) throw new Error('ENTRY_V2_INVALID_BAR_MINUTES');

  const normalized = intradayBars
    .map(bar => normalizeBar(bar, 'ENTRY_V2_INTRADAY'))
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  assertStrictlyIncreasingUnique(normalized, 'ENTRY_V2_INTRADAY');

  for (const bar of normalized) {
    if (jstSessionDate(bar.timestamp) !== decisionSession) {
      throw new Error('ENTRY_V2_INTRADAY_CROSS_SESSION_BAR');
    }
    const barStartMs = Date.parse(bar.timestamp);
    if (barStartMs + closeLagMs > asOfMs) {
      throw new Error('ENTRY_V2_INTRADAY_BAR_NOT_CLOSED');
    }
  }
  return Object.freeze(normalized);
}

function assertPointInTimeMarketInput(market, asOf) {
  if (!market || Object.keys(market).length === 0) return Object.freeze({});
  const observedAt = market.observedAt ?? market.asOf ?? market.timestamp;
  if (!observedAt) throw new Error('ENTRY_V2_MARKET_LINEAGE_REQUIRED');
  const observedMs = parseTimestamp(observedAt, 'ENTRY_V2_MARKET');
  const asOfMs = parseTimestamp(asOf, 'ENTRY_V2_AS_OF');
  if (observedMs > asOfMs) throw new Error('ENTRY_V2_MARKET_FUTURE_OBSERVATION');
  return Object.freeze({ ...market });
}

export function buildStrictPointInTimeEntryV2ResearchVector({
  symbol,
  asOf,
  dailyBars = [],
  intradayBars = [],
  market = {},
  universe = {},
  previousIntradayContext = null,
} = {}) {
  const priorDailyBars = prepareEntryV2PriorDailyBars({ dailyBars, asOf });
  const closedIntradayBars = prepareEntryV2ClosedIntradayPrefix({ intradayBars, asOf });
  const marketPointInTime = assertPointInTimeMarketInput(market, asOf);
  const marketObservedAt = Object.keys(marketPointInTime).length > 0
    ? new Date(parseTimestamp(
      marketPointInTime.observedAt ?? marketPointInTime.asOf ?? marketPointInTime.timestamp,
      'ENTRY_V2_MARKET',
    )).toISOString()
    : null;

  if (!priorDailyBars.length) throw new Error('ENTRY_V2_PRIOR_DAILY_BARS_REQUIRED');
  if (!closedIntradayBars.length) throw new Error('ENTRY_V2_CLOSED_INTRADAY_BARS_REQUIRED');

  const vector = buildEntryQualityV2ResearchVector({
    symbol,
    asOf,
    dailyBars: priorDailyBars,
    intradayBars: closedIntradayBars,
    market: marketPointInTime,
    universe,
    previousIntradayContext,
  });

  return Object.freeze({
    ...vector,
    pointInTime: Object.freeze({
      strict: true,
      decisionSessionDate: jstSessionDate(asOf),
      dailyBarsArePriorSessionOnly: true,
      intradayBarsAreCompletedPrefixOnly: true,
      marketLineageChecked: Object.keys(marketPointInTime).length > 0,
      marketObservedAt,
      futureOutcomeUsed: false,
    }),
  });
}

export default {
  ENTRY_V2_POINT_IN_TIME_POLICY,
  prepareEntryV2PriorDailyBars,
  prepareEntryV2ClosedIntradayPrefix,
  buildStrictPointInTimeEntryV2ResearchVector,
};
