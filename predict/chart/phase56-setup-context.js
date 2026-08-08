import { analyzePriceActionFeatures } from './phase56-price-action.js';

export const PHASE56_2_SAFETY = Object.freeze({
  mode: 'CHART_SETUP_CONTEXT_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(value) { return Number.isFinite(Number(value)); }
function pctDistance(a, b) { return finite(a) && finite(b) && Number(b) !== 0 ? (Number(a) - Number(b)) / Number(b) : null; }

export function analyzeChartSetupContext({ bars = [], swingRadius = 2, proximityPct = 0.004 } = {}) {
  const priceAction = analyzePriceActionFeatures({ bars, swingRadius });
  if (priceAction.status !== 'PRICE_ACTION_FEATURES_READY') {
    return Object.freeze({ phase: '56.2', status: 'OBSERVE', blockers: ['PRICE_ACTION_NOT_READY'], priceAction, executionAllowed: false, transmitted: false, safety: PHASE56_2_SAFETY });
  }

  const latest = bars.at(-1) || {};
  const previous = bars.at(-2) || {};
  const close = Number(latest.close);
  const low = Number(latest.low);
  const high = Number(latest.high);
  const previousClose = Number(previous.close);
  const priorHigh = Number(priceAction.referenceLevels.priorHigh);
  const priorLow = Number(priceAction.referenceLevels.priorLow);
  const zones = Array.isArray(priceAction.chartContext?.zones) ? priceAction.chartContext.zones : [];
  const vwap = Number(priceAction.chartContext?.vwap?.value);
  const labels = [];

  const brokeAbove = finite(close) && finite(priorHigh) && close > priorHigh;
  const brokeBelow = finite(close) && finite(priorLow) && close < priorLow;
  if (brokeAbove) labels.push('BREAKOUT_ABOVE_LOOKBACK');
  if (brokeBelow) labels.push('BREAKDOWN_BELOW_LOOKBACK');

  const retestLong = finite(low) && finite(priorHigh) && low <= priorHigh * (1 + proximityPct) && close >= priorHigh && previousClose > priorHigh;
  const retestShort = finite(high) && finite(priorLow) && high >= priorLow * (1 - proximityPct) && close <= priorLow && previousClose < priorLow;
  if (retestLong) labels.push('RETEST_HOLD_ABOVE');
  if (retestShort) labels.push('RETEST_HOLD_BELOW');

  const nearestSupport = zones.filter((z) => z.type === 'SUPPORT').sort((a, b) => Math.abs(a.distancePct) - Math.abs(b.distancePct))[0] ?? null;
  const nearestResistance = zones.filter((z) => z.type === 'RESISTANCE').sort((a, b) => Math.abs(a.distancePct) - Math.abs(b.distancePct))[0] ?? null;
  const nearSupport = nearestSupport ? Math.abs(pctDistance(close, nearestSupport.price)) <= proximityPct : false;
  const nearResistance = nearestResistance ? Math.abs(pctDistance(close, nearestResistance.price)) <= proximityPct : false;
  if (nearSupport) labels.push('NEAR_SUPPORT_ZONE');
  if (nearResistance) labels.push('NEAR_RESISTANCE_ZONE');

  const nearVwap = finite(vwap) ? Math.abs(pctDistance(close, vwap)) <= proximityPct : false;
  if (nearVwap) labels.push('NEAR_VWAP');

  const trend = priceAction.chartContext?.marketStructure?.regime ?? 'UNKNOWN';
  if (trend === 'UPTREND' && (nearSupport || nearVwap)) labels.push('UPTREND_PULLBACK_CONTEXT');
  if (trend === 'DOWNTREND' && (nearResistance || nearVwap)) labels.push('DOWNTREND_PULLBACK_CONTEXT');

  return Object.freeze({
    phase: '56.2', status: 'SETUP_CONTEXT_READY', labels: Object.freeze(labels),
    levels: Object.freeze({ priorHigh, priorLow, nearestSupport, nearestResistance, vwap }),
    context: Object.freeze({ trend, brokeAbove, brokeBelow, retestLong, retestShort, nearSupport, nearResistance, nearVwap }),
    priceAction,
    descriptiveOnly: true, reviewOnly: true,
    executionAllowed: false, brokerWriteAllowed: false, excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false,
    liveTradingAllowed: false, automaticPromotionAllowed: false, productionUpdateAllowed: false,
    transmitted: false, humanApprovalRequired: true, safety: PHASE56_2_SAFETY,
  });
}
