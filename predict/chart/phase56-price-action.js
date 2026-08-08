import { analyzeChartStructure, PHASE56_SAFETY } from './phase56-chart-intelligence.js';

function finite(value) { return Number.isFinite(Number(value)); }
function normalize(bars = []) {
  return bars.map((bar, index) => ({
    index,
    time: bar.time ?? bar.timestamp ?? index,
    open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close),
    volume: finite(bar.volume) ? Number(bar.volume) : 0,
    vwap: finite(bar.vwap) ? Number(bar.vwap) : null,
  })).filter((bar) => [bar.open, bar.high, bar.low, bar.close].every(Number.isFinite) && bar.high >= bar.low);
}
function shape(bar) {
  const range = Math.max(1e-9, bar.high - bar.low);
  const body = Math.abs(bar.close - bar.open);
  return Object.freeze({
    direction: bar.close > bar.open ? 'UP' : bar.close < bar.open ? 'DOWN' : 'FLAT',
    bodyRatio: body / range,
    upperWickRatio: (bar.high - Math.max(bar.open, bar.close)) / range,
    lowerWickRatio: (Math.min(bar.open, bar.close) - bar.low) / range,
  });
}
export function analyzePriceActionFeatures({ bars = [], swingRadius = 2 } = {}) {
  const clean = normalize(bars);
  if (clean.length < 3) return Object.freeze({ phase: '56.1', status: 'OBSERVE', blockers: ['INSUFFICIENT_BARS'], transmitted: false, executionAllowed: false, safety: PHASE56_SAFETY });
  const current = clean.at(-1), previous = clean.at(-2);
  const currentShape = shape(current), previousShape = shape(previous);
  const lookback = clean.slice(-11, -1);
  const priorHigh = Math.max(...lookback.map((bar) => bar.high));
  const priorLow = Math.min(...lookback.map((bar) => bar.low));
  const volumeBaseline = lookback.length ? lookback.reduce((sum, bar) => sum + bar.volume, 0) / lookback.length : 0;
  const volumeRatio = volumeBaseline > 0 ? current.volume / volumeBaseline : null;
  const labels = [];
  if (currentShape.direction === 'UP' && previousShape.direction === 'DOWN' && current.open <= previous.close && current.close >= previous.open) labels.push('ENGULFING_UP');
  if (currentShape.direction === 'DOWN' && previousShape.direction === 'UP' && current.open >= previous.close && current.close <= previous.open) labels.push('ENGULFING_DOWN');
  if (currentShape.lowerWickRatio >= 0.5 && currentShape.bodyRatio <= 0.35) labels.push('LONG_LOWER_WICK');
  if (currentShape.upperWickRatio >= 0.5 && currentShape.bodyRatio <= 0.35) labels.push('LONG_UPPER_WICK');
  if (current.close > priorHigh) labels.push('CLOSE_ABOVE_LOOKBACK_HIGH');
  if (current.close < priorLow) labels.push('CLOSE_BELOW_LOOKBACK_LOW');
  const chartContext = analyzeChartStructure({ bars: clean, swingRadius });
  return Object.freeze({
    phase: '56.1', status: 'PRICE_ACTION_FEATURES_READY', labels: Object.freeze(labels),
    currentCandle: currentShape,
    referenceLevels: Object.freeze({ priorHigh, priorLow }),
    volume: Object.freeze({ ratio: volumeRatio, elevated: finite(volumeRatio) ? volumeRatio >= 1.5 : false }),
    chartContext,
    descriptiveOnly: true, reviewOnly: true, executionAllowed: false, brokerWriteAllowed: false,
    excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false, liveTradingAllowed: false,
    automaticPromotionAllowed: false, productionUpdateAllowed: false, transmitted: false,
    humanApprovalRequired: true, safety: PHASE56_SAFETY,
  });
}
