import { evaluateNestedIntradayModelFamily } from './phase57-intraday-model-family.js';

export const PHASE57_HISTORICAL_BASELINE_SAFETY = Object.freeze({
  mode: 'PHASE57_HISTORICAL_INTRADAY_RESEARCH_ONLY',
  source: 'RssChartPast_or_equivalent_historical_OHLCV',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));

function normalizeBar(bar) {
  const ts = bar?.timestamp ?? bar?.time ?? bar?.datetime;
  if (!ts || !finite(bar?.open) || !finite(bar?.high) || !finite(bar?.low) || !finite(bar?.close)) return null;
  return {
    timestamp: new Date(ts).toISOString(),
    open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
    volume: finite(bar.volume) ? Number(bar.volume) : 0,
  };
}

function makeRow(bars, i, { symbol, sessionDate, horizonBars, barrierBps }) {
  const current = bars[i];
  const history = bars.slice(0, i + 1);
  const future = bars.slice(i + 1, i + 1 + horizonBars);
  if (!future.length || i < 5) return null;
  const open0 = history[0].open;
  const prev = history[i - 1];
  const recent = history.slice(Math.max(0, history.length - 6));
  const avgVolume = recent.slice(0, -1).reduce((s,b)=>s+b.volume,0) / Math.max(1,recent.length-1);
  const typicalVwapDen = history.reduce((s,b)=>s+b.volume,0);
  const vwap = typicalVwapDen ? history.reduce((s,b)=>s+((b.high+b.low+b.close)/3)*b.volume,0)/typicalVwapDen : current.close;
  const upper = current.close * (1 + barrierBps / 10000);
  const lower = current.close * (1 - barrierBps / 10000);
  let label = null, outcomeAt = null;
  for (const b of future) {
    const up = b.high >= upper, down = b.low <= lower;
    if (up && down) return null;
    if (up || down) { label = up ? 1 : 0; outcomeAt = b.timestamp; break; }
  }
  if (label === null) return null;
  return {
    symbol, sessionDate, featureCutoff: current.timestamp, outcomeAt, label, barrierBps,
    pointInTimeValid: current.timestamp < outcomeAt,
    sourceMode: 'historical_intraday_ohlcv',
    features: {
      returnFromOpen: open0 ? (current.close/open0-1)*100 : 0,
      rangePosition: current.high > current.low ? (current.close-current.low)/(current.high-current.low) : 0.5,
      shortMomentum: prev.close ? (current.close/prev.close-1)*100 : 0,
      relativeVolume: avgVolume > 0 ? current.volume/avgVolume : 1,
      spreadBps: 0, bookImbalance: 0, depthImbalance: 0, aggressiveBuyRatio: 0.5, tradeIntensity: 0,
      vwapDistancePct: vwap ? (current.close/vwap-1)*100 : 0,
    },
    interactions: { vwapFlow: 0, rangeBookPressure: 0 },
  };
}

export function buildHistoricalIntradayRows({ symbol, sessionDate, bars = [], horizonBars = 5, barrierBps = 20 } = {}) {
  const normalized = bars.map(normalizeBar).filter(Boolean).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  return normalized.map((_,i)=>makeRow(normalized,i,{symbol,sessionDate,horizonBars,barrierBps})).filter(Boolean);
}

export function evaluateHistoricalIntradayBaseline(rows = [], options = {}) {
  const result = evaluateNestedIntradayModelFamily(rows, options);
  return Object.freeze({
    phase: '57.p19.1', status: 'HISTORICAL_INTRADAY_BASELINE_RESEARCH',
    limitation: 'Historical OHLCV cannot reconstruct unavailable historical order-book/tick-flow state; microstructure features are neutral placeholders and must be validated separately on newly captured READ-ONLY data.',
    result,
    edgeClaimAllowed: false, recommendationAllowed: false,
    ...PHASE57_HISTORICAL_BASELINE_SAFETY,
  });
}

export default { buildHistoricalIntradayRows, evaluateHistoricalIntradayBaseline };
