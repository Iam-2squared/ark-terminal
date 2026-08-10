export const PHASE57_CHART_PERCEPTION_SAFETY = Object.freeze({
  mode: 'PHASE57_CHART_PERCEPTION_2_RESEARCH_ONLY',
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

const finite = value => Number.isFinite(Number(value));
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, Number(value)));
const mean = values => values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : 0;
const median = values => {
  if (!values.length) return null;
  const sorted = [...values].map(Number).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};
const pct = (a, b) => Number(b) ? (Number(a) / Number(b) - 1) * 100 : 0;

function normalizeBars(input = []) {
  return (Array.isArray(input) ? input : [])
    .map((bar, index) => ({
      index,
      timestamp: new Date(bar.timestamp ?? bar.time ?? index).toISOString(),
      open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
      volume: finite(bar.volume) ? Number(bar.volume) : 0,
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite) && bar.high >= bar.low)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export function resampleBars(input = [], barsPerBucket = 3) {
  const bars = normalizeBars(input);
  const size = Math.max(1, Math.floor(Number(barsPerBucket) || 1));
  const out = [];
  for (let start = 0; start + size <= bars.length; start += size) {
    const chunk = bars.slice(start, start + size);
    out.push(Object.freeze({
      timestamp: chunk.at(-1).timestamp,
      open: chunk[0].open,
      high: Math.max(...chunk.map(row => row.high)),
      low: Math.min(...chunk.map(row => row.low)),
      close: chunk.at(-1).close,
      volume: chunk.reduce((sum, row) => sum + row.volume, 0),
      completedSourceBars: size,
    }));
  }
  return Object.freeze(out);
}

function trueRanges(bars) {
  return bars.map((bar, index) => {
    const previous = index ? bars[index - 1].close : bar.open;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previous), Math.abs(bar.low - previous));
  });
}

function swingPoints(bars, radius = 2) {
  const highs = [], lows = [];
  for (let i = radius; i < bars.length - radius; i += 1) {
    const window = bars.slice(i - radius, i + radius + 1);
    const bar = bars[i];
    if (window.every((row, j) => j === radius || bar.high > row.high)) highs.push({ index: i, timestamp: bar.timestamp, price: bar.high });
    if (window.every((row, j) => j === radius || bar.low < row.low)) lows.push({ index: i, timestamp: bar.timestamp, price: bar.low });
  }
  return { highs, lows };
}

function classifyStructure(swings) {
  const highs = swings.highs.slice(-3);
  const lows = swings.lows.slice(-3);
  const highState = highs.length < 2 ? 'UNKNOWN' : highs.at(-1).price > highs.at(-2).price ? 'HIGHER_HIGH' : highs.at(-1).price < highs.at(-2).price ? 'LOWER_HIGH' : 'EQUAL_HIGH';
  const lowState = lows.length < 2 ? 'UNKNOWN' : lows.at(-1).price > lows.at(-2).price ? 'HIGHER_LOW' : lows.at(-1).price < lows.at(-2).price ? 'LOWER_LOW' : 'EQUAL_LOW';
  const regime = highState === 'HIGHER_HIGH' && lowState === 'HIGHER_LOW'
    ? 'UPTREND'
    : highState === 'LOWER_HIGH' && lowState === 'LOWER_LOW'
      ? 'DOWNTREND'
      : 'RANGE_OR_TRANSITION';
  return { regime, highState, lowState };
}

function candleShape(bar) {
  const range = Math.max(1e-12, bar.high - bar.low);
  const body = bar.close - bar.open;
  return {
    direction: body > 0 ? 'UP' : body < 0 ? 'DOWN' : 'FLAT',
    bodyStrength: Math.abs(body) / range,
    closeLocation: (bar.close - bar.low) / range,
    upperWickRatio: (bar.high - Math.max(bar.open, bar.close)) / range,
    lowerWickRatio: (Math.min(bar.open, bar.close) - bar.low) / range,
  };
}

function volumeContext(bars) {
  const current = bars.at(-1);
  const prior = bars.slice(-21, -1).map(row => row.volume).filter(value => value > 0);
  const baseline = median(prior) ?? mean(prior);
  const ratio = baseline > 0 ? current.volume / baseline : null;
  return {
    ratio,
    elevated: finite(ratio) ? ratio >= 1.5 : false,
    depleted: finite(ratio) ? ratio <= 0.65 : false,
  };
}

function volatilityContext(bars) {
  const tr = trueRanges(bars);
  const recent5 = mean(tr.slice(-5));
  const recent20 = mean(tr.slice(-20));
  const ratio = recent20 > 0 ? recent5 / recent20 : 1;
  return {
    compressionRatio: ratio,
    state: ratio <= 0.7 ? 'COMPRESSED' : ratio >= 1.35 ? 'EXPANDING' : 'NORMAL',
    atrPct: bars.at(-1).close ? mean(tr.slice(-14)) / bars.at(-1).close * 100 : 0,
  };
}

function deriveImpulsePullback(bars, structure, swings) {
  const close = bars.at(-1).close;
  const recentHigh = Math.max(...bars.slice(-20).map(row => row.high));
  const recentLow = Math.min(...bars.slice(-20).map(row => row.low));
  const range = Math.max(1e-12, recentHigh - recentLow);
  const position = clamp((close - recentLow) / range, 0, 1);
  const lastHigh = swings.highs.at(-1)?.price ?? recentHigh;
  const lastLow = swings.lows.at(-1)?.price ?? recentLow;
  const fromHighPct = pct(close, lastHigh);
  const fromLowPct = pct(close, lastLow);
  let phase = 'BALANCED';
  if (structure.regime === 'UPTREND') {
    phase = position >= 0.82 ? 'UPTREND_IMPULSE' : position >= 0.45 ? 'UPTREND_PULLBACK' : 'UPTREND_DEEP_PULLBACK';
  } else if (structure.regime === 'DOWNTREND') {
    phase = position <= 0.18 ? 'DOWNTREND_IMPULSE' : position <= 0.55 ? 'DOWNTREND_PULLBACK' : 'DOWNTREND_DEEP_PULLBACK';
  } else if (position >= 0.85) phase = 'RANGE_UPPER_EDGE';
  else if (position <= 0.15) phase = 'RANGE_LOWER_EDGE';
  return { phase, rangePosition20: position, fromLastSwingHighPct: fromHighPct, fromLastSwingLowPct: fromLowPct };
}

function detectBreakoutRetest(bars) {
  if (bars.length < 12) return { state: 'NONE', level: null };
  const current = bars.at(-1);
  const priorWindow = bars.slice(-12, -2);
  const priorHigh = Math.max(...priorWindow.map(row => row.high));
  const priorLow = Math.min(...priorWindow.map(row => row.low));
  const previous = bars.at(-2);
  if (current.close > priorHigh) return { state: 'BREAKOUT_UP', level: priorHigh, distancePct: pct(current.close, priorHigh) };
  if (current.close < priorLow) return { state: 'BREAKOUT_DOWN', level: priorLow, distancePct: pct(priorLow, current.close) };
  if (previous.close > priorHigh && current.low <= priorHigh && current.close >= priorHigh) return { state: 'RETEST_HOLD_UP', level: priorHigh, distancePct: pct(current.close, priorHigh) };
  if (previous.close < priorLow && current.high >= priorLow && current.close <= priorLow) return { state: 'RETEST_HOLD_DOWN', level: priorLow, distancePct: pct(priorLow, current.close) };
  if (previous.high > priorHigh && current.close < priorHigh) return { state: 'FAILED_BREAKOUT_UP', level: priorHigh, distancePct: pct(current.close, priorHigh) };
  if (previous.low < priorLow && current.close > priorLow) return { state: 'FAILED_BREAKOUT_DOWN', level: priorLow, distancePct: pct(priorLow, current.close) };
  return { state: 'NONE', level: null };
}

function deriveTrendQuality(bars, structure) {
  const closes = bars.slice(-12).map(row => row.close);
  if (closes.length < 4) return { score: 0, directionalEfficiency: 0, persistence: 0 };
  const net = Math.abs(closes.at(-1) - closes[0]);
  const path = closes.slice(1).reduce((sum, value, index) => sum + Math.abs(value - closes[index]), 0);
  const efficiency = path > 0 ? net / path : 0;
  let aligned = 0;
  const sign = structure.regime === 'UPTREND' ? 1 : structure.regime === 'DOWNTREND' ? -1 : 0;
  for (let i = 1; i < closes.length; i += 1) if (sign && Math.sign(closes[i] - closes[i - 1]) === sign) aligned += 1;
  const persistence = sign ? aligned / (closes.length - 1) : 0;
  return { score: clamp(0.6 * efficiency + 0.4 * persistence, 0, 1), directionalEfficiency: efficiency, persistence };
}

function deriveNarrative(perception) {
  const parts = [];
  parts.push(perception.structure.regime);
  parts.push(perception.phase.phase);
  if (perception.breakout.state !== 'NONE') parts.push(perception.breakout.state);
  parts.push(perception.volatility.state);
  if (perception.volume.elevated) parts.push('VOLUME_CONFIRMED');
  if (perception.currentCandle.bodyStrength >= 0.7) parts.push('STRONG_BODY');
  return parts.join(' | ');
}

function deriveScenario(perception) {
  const bullish = perception.structure.regime === 'UPTREND'
    && ['UPTREND_PULLBACK', 'UPTREND_IMPULSE'].includes(perception.phase.phase)
    && !['FAILED_BREAKOUT_UP'].includes(perception.breakout.state);
  const bearish = perception.structure.regime === 'DOWNTREND'
    && ['DOWNTREND_PULLBACK', 'DOWNTREND_IMPULSE'].includes(perception.phase.phase)
    && !['FAILED_BREAKOUT_DOWN'].includes(perception.breakout.state);
  if (bullish) return { primary: 'TREND_CONTINUATION_UP', invalidationReference: perception.swings.lows.at(-1)?.price ?? perception.reference.recentLow };
  if (bearish) return { primary: 'TREND_CONTINUATION_DOWN', invalidationReference: perception.swings.highs.at(-1)?.price ?? perception.reference.recentHigh };
  if (perception.breakout.state === 'FAILED_BREAKOUT_UP') return { primary: 'FAILED_BREAKOUT_REVERSAL_DOWN', invalidationReference: perception.reference.recentHigh };
  if (perception.breakout.state === 'FAILED_BREAKOUT_DOWN') return { primary: 'FAILED_BREAKOUT_REVERSAL_UP', invalidationReference: perception.reference.recentLow };
  return { primary: 'NO_CLEAR_SCENARIO', invalidationReference: null };
}

export function perceiveSingleTimeframe({ bars = [], timeframe = '5m', swingRadius = 2 } = {}) {
  const clean = normalizeBars(bars);
  if (clean.length < 24) return Object.freeze({
    phase: '57.p23.10', status: 'OBSERVE', timeframe, blockers: ['INSUFFICIENT_COMPLETED_BARS'],
    reviewOnly: true, transmitted: false, ...PHASE57_CHART_PERCEPTION_SAFETY,
  });
  const swings = swingPoints(clean, swingRadius);
  const structure = classifyStructure(swings);
  const phase = deriveImpulsePullback(clean, structure, swings);
  const currentCandle = candleShape(clean.at(-1));
  const volume = volumeContext(clean);
  const volatility = volatilityContext(clean);
  const breakout = detectBreakoutRetest(clean);
  const trendQuality = deriveTrendQuality(clean, structure);
  const reference = {
    recentHigh: Math.max(...clean.slice(-20).map(row => row.high)),
    recentLow: Math.min(...clean.slice(-20).map(row => row.low)),
    lastClose: clean.at(-1).close,
  };
  const base = {
    phase: '57.p23.10', status: 'CHART_PERCEPTION_READY', timeframe, barCount: clean.length,
    structure, swings, phase, currentCandle, volume, volatility, breakout, trendQuality, reference,
    dataCutoff: clean.at(-1).timestamp,
  };
  const scenario = deriveScenario(base);
  const narrative = deriveNarrative(base);
  return Object.freeze({
    ...base, scenario, narrative,
    pointInTimeOnly: true,
    futureBarsUsed: false,
    outcomeUsed: false,
    predictionRole: 'PERCEPTION_NOT_FORECAST',
    reviewOnly: true,
    recommendationAllowed: false,
    transmitted: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
    safety: PHASE57_CHART_PERCEPTION_SAFETY,
  });
}

function alignmentScore(perceptions) {
  const usable = perceptions.filter(row => row?.status === 'CHART_PERCEPTION_READY');
  if (!usable.length) return { direction: 'MIXED', score: 0 };
  const votes = usable.map(row => row.structure.regime === 'UPTREND' ? 1 : row.structure.regime === 'DOWNTREND' ? -1 : 0);
  const total = votes.reduce((sum, value) => sum + value, 0);
  const score = Math.abs(total) / usable.length;
  return { direction: total > 0 ? 'UP' : total < 0 ? 'DOWN' : 'MIXED', score };
}

export function buildMultiTimeframeChartPerception({ bars5m = [] } = {}) {
  const clean = normalizeBars(bars5m);
  const tf5 = perceiveSingleTimeframe({ bars: clean, timeframe: '5m' });
  const tf15 = perceiveSingleTimeframe({ bars: resampleBars(clean, 3), timeframe: '15m' });
  const tf60 = perceiveSingleTimeframe({ bars: resampleBars(clean, 12), timeframe: '60m' });
  const timeframes = Object.freeze({ '5m': tf5, '15m': tf15, '60m': tf60 });
  const alignment = alignmentScore([tf5, tf15, tf60]);
  const conflict = [tf5, tf15, tf60]
    .filter(row => row?.status === 'CHART_PERCEPTION_READY')
    .map(row => row.structure.regime)
    .filter(regime => regime !== 'RANGE_OR_TRANSITION');
  const directionalConflict = new Set(conflict).size > 1;
  return Object.freeze({
    phase: '57.p23.10', status: 'MULTI_TIMEFRAME_PERCEPTION_READY',
    architecture: 'PERCEPTION_THEN_UNDERSTANDING_THEN_PREDICTION',
    timeframes,
    alignment: Object.freeze({ ...alignment, directionalConflict }),
    causalCutoff: clean.at(-1)?.timestamp ?? null,
    completedBarsOnly: true,
    futureBarsUsed: false,
    outcomeUsed: false,
    recommendationAllowed: false,
    reviewOnly: true,
    transmitted: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
    safety: PHASE57_CHART_PERCEPTION_SAFETY,
  });
}

export function buildChartReasoningPacket({ symbol, bars5m = [] } = {}) {
  const perception = buildMultiTimeframeChartPerception({ bars5m });
  const compactTimeframes = Object.fromEntries(Object.entries(perception.timeframes).map(([timeframe, row]) => [timeframe, {
    status: row.status,
    structure: row.structure ?? null,
    phase: row.phase ?? null,
    breakout: row.breakout ?? null,
    trendQuality: row.trendQuality ?? null,
    volatility: row.volatility ?? null,
    volume: row.volume ?? null,
    scenario: row.scenario ?? null,
    narrative: row.narrative ?? null,
    dataCutoff: row.dataCutoff ?? null,
  }]));
  return Object.freeze({
    schema: 'ARK_CHART_REASONING_PACKET_V1',
    symbol: String(symbol ?? ''),
    purpose: 'STRUCTURED_CHART_UNDERSTANDING_FOR_RESEARCH_REVIEW',
    perception: compactTimeframes,
    alignment: perception.alignment,
    instructionsForReasoner: Object.freeze([
      'Describe the chart state before forecasting anything.',
      'Treat indicators as supporting evidence, not the primary narrative.',
      'Prefer market structure, impulse/pullback, breakout/retest, volatility and volume context.',
      'State a primary scenario, an alternative scenario and explicit invalidation evidence.',
      'Do not use any data after causalCutoff.',
      'Do not output an executable order or recommendation.',
    ]),
    causalCutoff: perception.causalCutoff,
    futureDataIncluded: false,
    executableTradingInstructionAllowed: false,
    recommendationAllowed: false,
    ...PHASE57_CHART_PERCEPTION_SAFETY,
    transmitted: false,
  });
}

export default {
  PHASE57_CHART_PERCEPTION_SAFETY,
  resampleBars,
  perceiveSingleTimeframe,
  buildMultiTimeframeChartPerception,
  buildChartReasoningPacket,
};
