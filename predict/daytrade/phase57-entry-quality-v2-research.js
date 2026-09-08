export const PHASE57_ENTRY_QUALITY_V2_SAFETY = Object.freeze({
  mode: 'PHASE57_ENTRY_QUALITY_V2_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

export const PHASE57_ENTRY_QUALITY_V2_POLICY = Object.freeze({
  baseline: 'PHASE57_P21_FROZEN_ENTRY',
  integrationMode: 'ISOLATED_RESEARCH_ONLY',
  selectorChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
  futureBarsAllowed: false,
  resultBasedRetuningAllowed: false,
  dailyRetentionTargetBars: 250,
  dailyFeatureWindows: Object.freeze([5, 20, 50, 100]),
  intradayBarMinutes: 5,
  qualityTargets: Object.freeze([
    'RETURN_PATH',
    'MFE',
    'MAE',
    'TIME_TO_MFE',
    'TIME_TO_MAE',
  ]),
});

const avg = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
const pct = (a, b) => Number.isFinite(a) && Number.isFinite(b) && b !== 0 ? (a / b - 1) * 100 : 0;
const stdev = xs => {
  if (xs.length < 2) return 0;
  const m = avg(xs);
  return Math.sqrt(avg(xs.map(x => (x - m) ** 2)));
};

function normalizeBars(bars = []) {
  return bars
    .map(bar => ({
      timestamp: new Date(bar.timestamp).toISOString(),
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
      volume: Number(bar.volume ?? 0),
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close, bar.volume].every(Number.isFinite))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function assertPointInTime(bars, asOf) {
  const cutoff = new Date(asOf).getTime();
  if (!Number.isFinite(cutoff)) throw new Error('ENTRY_V2_INVALID_AS_OF');
  const future = bars.find(bar => new Date(bar.timestamp).getTime() > cutoff);
  if (future) throw new Error('ENTRY_V2_FUTURE_BAR_REJECTED');
}

function movingAverage(closes, window) {
  return avg(closes.slice(-window));
}

function slopePct(closes, window) {
  if (closes.length < 2) return 0;
  const current = movingAverage(closes, window);
  const priorSeries = closes.slice(0, -1);
  const prior = movingAverage(priorSeries, window);
  return pct(current, prior);
}

function trueRanges(bars) {
  return bars.map((bar, index) => {
    if (index === 0) return bar.high - bar.low;
    const previousClose = bars[index - 1].close;
    return Math.max(
      bar.high - bar.low,
      Math.abs(bar.high - previousClose),
      Math.abs(bar.low - previousClose),
    );
  });
}

function rangePosition(bars, window) {
  const sample = bars.slice(-window);
  if (!sample.length) return 0.5;
  const high = Math.max(...sample.map(bar => bar.high));
  const low = Math.min(...sample.map(bar => bar.low));
  const close = sample.at(-1).close;
  return high > low ? (close - low) / (high - low) : 0.5;
}

export function buildEntryV2DailyContext({ dailyBars = [], asOf }) {
  const bars = normalizeBars(dailyBars);
  assertPointInTime(bars, asOf);
  if (!bars.length) throw new Error('ENTRY_V2_DAILY_BARS_REQUIRED');

  const closes = bars.map(bar => bar.close);
  const volumes = bars.map(bar => bar.volume);
  const current = bars.at(-1);
  const previous = bars.at(-2) ?? current;
  const ma20 = movingAverage(closes, 20);
  const ma50 = movingAverage(closes, 50);
  const ma100 = movingAverage(closes, 100);
  const tr20 = avg(trueRanges(bars).slice(-20));
  const volume20 = avg(volumes.slice(-20));
  const priorVolume20 = avg(volumes.slice(-21, -1));

  return Object.freeze({
    source: 'ENTRY_V2_DAILY_CONTEXT',
    asOf: new Date(asOf).toISOString(),
    latestBarTimestamp: current.timestamp,
    availableBars: bars.length,
    retentionTargetBars: PHASE57_ENTRY_QUALITY_V2_POLICY.dailyRetentionTargetBars,
    return1dPct: pct(current.close, previous.close),
    return5dPct: closes.length >= 6 ? pct(current.close, closes.at(-6)) : 0,
    return20dPct: closes.length >= 21 ? pct(current.close, closes.at(-21)) : 0,
    ma20DistancePct: pct(current.close, ma20),
    ma50DistancePct: pct(current.close, ma50),
    ma100DistancePct: pct(current.close, ma100),
    ma20SlopePct: slopePct(closes, 20),
    ma50SlopePct: slopePct(closes, 50),
    ma100SlopePct: slopePct(closes, 100),
    range20Position: rangePosition(bars, 20),
    range50Position: rangePosition(bars, 50),
    atr20Pct: current.close ? tr20 / current.close * 100 : 0,
    dailyVolatility20Pct: stdev(closes.slice(-20).map((close, index, xs) => index ? pct(close, xs[index - 1]) : 0).slice(1)),
    volume20Ratio: priorVolume20 > 0 ? current.volume / priorVolume20 : 1,
    averageVolume20: volume20,
    // At an intraday decision, the latest retained daily bar is the preceding
    // completed session, so its close is the point-in-time prior close.
    priorClose: current.close,
  });
}

export function buildEntryV2IntradayContext({ intradayBars = [], asOf }) {
  const bars = normalizeBars(intradayBars);
  assertPointInTime(bars, asOf);
  if (!bars.length) throw new Error('ENTRY_V2_INTRADAY_BARS_REQUIRED');

  const current = bars.at(-1);
  const previous = bars.at(-2) ?? current;
  const typical = bars.map(bar => (bar.high + bar.low + bar.close) / 3);
  const volumeSum = bars.reduce((sum, bar) => sum + bar.volume, 0);
  const vwap = volumeSum
    ? bars.reduce((sum, bar, index) => sum + typical[index] * bar.volume, 0) / volumeSum
    : current.close;
  const priorVolumes = bars.slice(-6, -1).map(bar => bar.volume);
  const short3 = bars.length >= 4 ? pct(current.close, bars.at(-4).close) : pct(current.close, previous.close);
  const short6 = bars.length >= 7 ? pct(current.close, bars.at(-7).close) : short3;

  return Object.freeze({
    source: 'ENTRY_V2_INTRADAY_CONTEXT',
    asOf: new Date(asOf).toISOString(),
    latestBarTimestamp: current.timestamp,
    availableBars: bars.length,
    returnFromOpenPct: pct(current.close, bars[0].open),
    oneBarMomentumPct: pct(current.close, previous.close),
    threeBarMomentumPct: short3,
    sixBarMomentumPct: short6,
    momentumAccelerationPct: short3 - short6,
    vwapDistancePct: pct(current.close, vwap),
    relativeVolume5: avg(priorVolumes) > 0 ? current.volume / avg(priorVolumes) : 1,
    intradayRangePosition: rangePosition(bars, bars.length),
    currentClose: current.close,
    currentVolume: current.volume,
  });
}

export function buildEntryV2UniverseDiagnostics({ price, tickSize = null, averageTurnover = null, spreadProxy = null }) {
  const p = Number(price);
  const tick = tickSize == null ? null : Number(tickSize);
  const turnover = averageTurnover == null ? null : Number(averageTurnover);
  const spread = spreadProxy == null ? null : Number(spreadProxy);

  if (!(p > 0)) throw new Error('ENTRY_V2_INVALID_PRICE');

  return Object.freeze({
    source: 'ENTRY_V2_UNIVERSE_DIAGNOSTICS',
    price: p,
    tickSize: Number.isFinite(tick) && tick > 0 ? tick : null,
    tickToPricePct: Number.isFinite(tick) && tick > 0 ? tick / p * 100 : null,
    averageTurnover: Number.isFinite(turnover) && turnover >= 0 ? turnover : null,
    spreadProxy: Number.isFinite(spread) && spread >= 0 ? spread : null,
    hardEligibilityApplied: false,
    note: 'Diagnostic only. No post-hoc low-price cutoff is applied in Entry v2 research foundation.',
  });
}

export function buildEntryV2MarketContext(input = {}) {
  const optionalFinite = value => {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };
  const topixReturnPct = optionalFinite(input.topixReturnPct);
  const nikkeiReturnPct = optionalFinite(input.nikkeiReturnPct);
  const breadthUpRatio = optionalFinite(input.breadthUpRatio);
  const marketVolatility = optionalFinite(input.marketVolatility);
  const sectorRelativeStrengthPct = optionalFinite(input.sectorRelativeStrengthPct);
  const fields = { topixReturnPct, nikkeiReturnPct, breadthUpRatio, marketVolatility, sectorRelativeStrengthPct };

  return Object.freeze({
    source: 'ENTRY_V2_MARKET_CONTEXT',
    ...fields,
    availableFields: Object.freeze(Object.keys(fields).filter(key => fields[key] !== null)),
    missingFields: Object.freeze(Object.keys(fields).filter(key => fields[key] === null)),
    complete: Object.values(fields).every(value => value !== null),
    missingValuesFabricated: false,
  });
}

export function buildEntryV2Novelty({ previous = null, current }) {
  if (!current) throw new Error('ENTRY_V2_CURRENT_CONTEXT_REQUIRED');
  if (!previous) {
    return Object.freeze({
      source: 'ENTRY_V2_NOVELTY',
      hasPreviousState: false,
      vwapDistanceChangePct: 0,
      momentumChangePct: 0,
      relativeVolumeChange: 0,
      rangePositionChange: 0,
    });
  }

  return Object.freeze({
    source: 'ENTRY_V2_NOVELTY',
    hasPreviousState: true,
    vwapDistanceChangePct: Number(current.vwapDistancePct ?? 0) - Number(previous.vwapDistancePct ?? 0),
    momentumChangePct: Number(current.threeBarMomentumPct ?? 0) - Number(previous.threeBarMomentumPct ?? 0),
    relativeVolumeChange: Number(current.relativeVolume5 ?? 1) - Number(previous.relativeVolume5 ?? 1),
    rangePositionChange: Number(current.intradayRangePosition ?? 0.5) - Number(previous.intradayRangePosition ?? 0.5),
  });
}

export function buildEntryQualityV2ResearchVector({
  symbol,
  asOf,
  dailyBars,
  intradayBars,
  market = {},
  universe = {},
  previousIntradayContext = null,
}) {
  const daily = buildEntryV2DailyContext({ dailyBars, asOf });
  const intraday = buildEntryV2IntradayContext({ intradayBars, asOf });
  const marketContext = buildEntryV2MarketContext(market);
  const universeDiagnostics = buildEntryV2UniverseDiagnostics({
    price: intraday.currentClose,
    ...universe,
  });
  const novelty = buildEntryV2Novelty({ previous: previousIntradayContext, current: intraday });

  return Object.freeze({
    policy: PHASE57_ENTRY_QUALITY_V2_POLICY,
    safety: PHASE57_ENTRY_QUALITY_V2_SAFETY,
    symbol: String(symbol ?? '').trim().toUpperCase(),
    asOf: new Date(asOf).toISOString(),
    daily,
    intraday,
    market: marketContext,
    universe: universeDiagnostics,
    novelty,
    signalEligible: null,
    direction: null,
    longQuality: null,
    shortQuality: null,
    status: 'FEATURE_VECTOR_ONLY_NO_SIGNAL',
  });
}

export default {
  PHASE57_ENTRY_QUALITY_V2_SAFETY,
  PHASE57_ENTRY_QUALITY_V2_POLICY,
  buildEntryV2DailyContext,
  buildEntryV2IntradayContext,
  buildEntryV2UniverseDiagnostics,
  buildEntryV2MarketContext,
  buildEntryV2Novelty,
  buildEntryQualityV2ResearchVector,
};
