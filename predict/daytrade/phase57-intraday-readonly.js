import { buildReadonlyMicrostructureFeatures } from '../chart/phase56-microstructure-readonly.js';

export const PHASE57_INTRADAY_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const num = v => finite(v) ? Number(v) : null;
const mean = values => values.length ? values.reduce((s, v) => s + v, 0) / values.length : null;

function normalizeBars(bars = []) {
  return (Array.isArray(bars) ? bars : []).map(b => ({
    timestamp: b.timestamp ?? b.time ?? b.datetime ?? null,
    open: num(b.open), high: num(b.high), low: num(b.low), close: num(b.close), volume: num(b.volume) ?? 0,
  })).filter(b => [b.open,b.high,b.low,b.close].every(finite));
}

export function buildIntradayReadonlyFeatures({ bars = [], snapshot = {}, ticks = [], sessionOpen = null } = {}) {
  const normalizedBars = normalizeBars(bars);
  const last = normalizedBars.at(-1) ?? null;
  const first = normalizedBars[0] ?? null;
  const closes = normalizedBars.map(b => b.close);
  const volumes = normalizedBars.map(b => b.volume);
  const typical = normalizedBars.map(b => (b.high + b.low + b.close) / 3);
  const pv = normalizedBars.reduce((s,b,i) => s + typical[i] * volumes[i], 0);
  const totalVolume = volumes.reduce((s,v) => s + v, 0);
  const vwap = totalVolume > 0 ? pv / totalVolume : null;
  const openPrice = num(sessionOpen) ?? first?.open ?? null;
  const sessionHigh = normalizedBars.length ? Math.max(...normalizedBars.map(b => b.high)) : null;
  const sessionLow = normalizedBars.length ? Math.min(...normalizedBars.map(b => b.low)) : null;
  const retFromOpen = finite(last?.close) && finite(openPrice) && openPrice !== 0 ? last.close / openPrice - 1 : null;
  const vwapDistance = finite(last?.close) && finite(vwap) && vwap !== 0 ? last.close / vwap - 1 : null;
  const rangePosition = finite(last?.close) && finite(sessionHigh) && finite(sessionLow) && sessionHigh !== sessionLow ? (last.close - sessionLow) / (sessionHigh - sessionLow) : null;
  const momentum3 = closes.length >= 4 && closes.at(-4) !== 0 ? closes.at(-1) / closes.at(-4) - 1 : null;
  const averageBarVolume = mean(volumes);
  const lastBarRelativeVolume = finite(last?.volume) && finite(averageBarVolume) && averageBarVolume !== 0 ? last.volume / averageBarVolume : null;
  const micro = buildReadonlyMicrostructureFeatures({ snapshot, ticks });

  return Object.freeze({
    phase: '57.p1',
    status: normalizedBars.length >= 3 ? 'INTRADAY_FEATURES_READY' : 'PARTIAL_INTRADAY_FEATURES',
    features: Object.freeze({
      lastPrice: last?.close ?? null,
      retFromOpen,
      vwap,
      vwapDistance,
      sessionHigh,
      sessionLow,
      rangePosition,
      momentum3,
      totalVolume,
      lastBarRelativeVolume,
      spreadBps: micro.features.spreadBps,
      bookImbalance: micro.features.bookImbalance,
      depthImbalance: micro.features.depthImbalance,
      aggressiveBuyRatio: micro.features.aggressiveBuyRatio,
      tradeIntensity: micro.features.tradeIntensity,
    }),
    interactions: Object.freeze({
      vwapFlowAlignment: finite(vwapDistance) && finite(micro.features.aggressiveBuyRatio)
        ? (vwapDistance >= 0 && micro.features.aggressiveBuyRatio >= .55 ? 'ABOVE_VWAP_BUY_FLOW' : vwapDistance < 0 && micro.features.aggressiveBuyRatio <= .45 ? 'BELOW_VWAP_SELL_FLOW' : 'MIXED')
        : 'UNKNOWN',
      breakoutPressure: finite(rangePosition) && finite(micro.features.bookImbalance)
        ? (rangePosition >= .8 && micro.features.bookImbalance > .1 ? 'UPPER_RANGE_BID_PRESSURE' : rangePosition <= .2 && micro.features.bookImbalance < -.1 ? 'LOWER_RANGE_ASK_PRESSURE' : 'NONE')
        : 'UNKNOWN',
    }),
    source: Object.freeze({
      mode: 'READ_ONLY',
      expectedInputs: ['RssMarket', 'RssChart', 'RssChartPast', 'RssTickList', 'board/depth snapshot'],
      rssOrderFunctionsUsed: false,
    }),
    reviewOnly: true,
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_INTRADAY_SAFETY,
  });
}

export default buildIntradayReadonlyFeatures;
