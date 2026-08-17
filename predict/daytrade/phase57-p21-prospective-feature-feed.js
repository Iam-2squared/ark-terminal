import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';

export const PHASE57_P21_PROSPECTIVE_FEATURE_FEED_SAFETY = Object.freeze({
  phase:'57.p21.prospective-feature-feed',
  mode:'PHASE57_P21_PROSPECTIVE_READ_ONLY_FEATURE_BUILD',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P21_PROSPECTIVE_HORIZONS = Object.freeze([1,3,6,12,24]);

const FORBIDDEN_OUTCOME_KEYS = Object.freeze([
  'outcomeAt','outcome','outcomes','label','actualReturnPct','futureBars','realizedReturn',
  'grossReturnPct','netReturnPct','mfePct','maePct','exitTimestamp','exitReason','hit','target',
]);

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));

function normalizeBar(bar){
  const timestamp = bar?.timestamp ?? bar?.time ?? bar?.datetime;
  if(!timestamp || !finite(bar?.open) || !finite(bar?.high) || !finite(bar?.low) || !finite(bar?.close)) return null;
  const parsed = Date.parse(timestamp);
  if(!Number.isFinite(parsed)) return null;
  const out = {
    timestamp:new Date(parsed).toISOString(),
    open:Number(bar.open), high:Number(bar.high), low:Number(bar.low), close:Number(bar.close),
    volume:finite(bar?.volume) ? Number(bar.volume) : 0,
  };
  return out.high >= out.low && out.open > 0 && out.close > 0 ? out : null;
}

function jstSessionDate(timestamp){
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone:'Asia/Tokyo', year:'numeric', month:'2-digit', day:'2-digit',
  }).formatToParts(new Date(timestamp));
  const row = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${row.year}-${row.month}-${row.day}`;
}

function average(values){
  return values.length ? values.reduce((sum,value)=>sum+Number(value),0)/values.length : 0;
}

function buildP24ParityFeatures(bars){
  const current = bars.at(-1);
  const previous = bars.length > 1 ? bars.at(-2) : current;
  const enriched = enrichHistoricalIntradayBars(bars);
  const multiFactor = enriched.at(-1)?.multiFactor ?? {};
  const recentPriorVolumes = bars.slice(Math.max(0,bars.length-1-5),bars.length-1).map(bar=>Number(bar.volume||0));
  const priorVolumeAverage = average(recentPriorVolumes);
  const open0 = Number(bars[0]?.open || 0);
  return Object.freeze({
    returnFromOpen:open0 ? (Number(current.close)/open0-1)*100 : 0,
    rangePosition:Number(current.high) > Number(current.low)
      ? (Number(current.close)-Number(current.low))/(Number(current.high)-Number(current.low)) : 0.5,
    shortMomentum:Number(previous.close) ? (Number(current.close)/Number(previous.close)-1)*100 : 0,
    relativeVolume:priorVolumeAverage > 0 ? Number(current.volume||0)/priorVolumeAverage : 1,
    ...multiFactor,
  });
}

/**
 * Builds the current, outcome-free P21 rows from a completed 5-minute OHLCV prefix.
 * Feature definitions intentionally mirror the P24 historical integrated backtest.
 * No current/future outcome field is materialized here.
 */
export function buildProspectiveP21FeatureFeed({
  symbol,
  sessionDate,
  bars5m=[],
  horizons=PHASE57_P21_PROSPECTIVE_HORIZONS,
  latestBarClosed=false,
}={}){
  const blockers=[];
  if(typeof symbol !== 'string' || !symbol.trim()) blockers.push('MISSING_SYMBOL');
  if(typeof sessionDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) blockers.push('INVALID_SESSION_DATE');
  if(latestBarClosed !== true) blockers.push('LATEST_5M_BAR_NOT_EXPLICITLY_CLOSED');

  const normalized = (Array.isArray(bars5m) ? bars5m : []).map(normalizeBar).filter(Boolean)
    .sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(normalized.length < 6) blockers.push('INSUFFICIENT_5M_PREFIX');
  if(normalized.some((bar,index)=>index>0 && bar.timestamp === normalized[index-1].timestamp)) blockers.push('DUPLICATE_5M_TIMESTAMP');
  if(sessionDate && normalized.some(bar=>jstSessionDate(bar.timestamp)!==sessionDate)) blockers.push('CROSS_SESSION_5M_PREFIX');

  if(blockers.length) return Object.freeze({
    phase:'57.p21.prospective-feature-feed',
    status:'BLOCKED_PROSPECTIVE_FEATURE_FEED',
    complete:false,
    blockers:Object.freeze(blockers),
    safety:PHASE57_P21_PROSPECTIVE_FEATURE_FEED_SAFETY,
  });

  const current = normalized.at(-1);
  const features = buildP24ParityFeatures(normalized);
  const hs = [...new Set((Array.isArray(horizons)?horizons:[]).map(Number)
    .filter(value=>Number.isInteger(value)&&value>0))].sort((a,b)=>a-b);
  if(!hs.length) return Object.freeze({
    phase:'57.p21.prospective-feature-feed',
    status:'BLOCKED_NO_VALID_HORIZONS',
    complete:false,
    blockers:Object.freeze(['NO_VALID_HORIZONS']),
    safety:PHASE57_P21_PROSPECTIVE_FEATURE_FEED_SAFETY,
  });

  const currentRowsByHorizon = Object.freeze(Object.fromEntries(hs.map(horizonBars=>{
    const row = Object.freeze({
      symbol:symbol.trim(),
      sessionDate,
      featureCutoff:current.timestamp,
      entryPrice:Number(current.close),
      horizonBars,
      features,
      pointInTimeValid:true,
      intradayOnly:true,
      sourceMode:'prospective_completed_5m_ohlcv_prefix',
    });
    const forbidden = FORBIDDEN_OUTCOME_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(row,key));
    if(forbidden.length) throw new Error(`prospective current row unexpectedly contains outcome fields: ${forbidden.join(',')}`);
    return [horizonBars,row];
  })));

  return Object.freeze({
    phase:'57.p21.prospective-feature-feed',
    status:'PROSPECTIVE_P21_FEATURE_FEED_READY',
    complete:true,
    symbol:symbol.trim(),
    sessionDate,
    featureCutoff:current.timestamp,
    sourceBarCount:normalized.length,
    horizonsBars:Object.freeze(hs),
    currentRowsByHorizon,
    integrity:Object.freeze({
      latestBarExplicitlyClosed:true,
      completedFiveMinuteBarsOnly:true,
      sameSessionOnly:true,
      featureParityTarget:'PHASE57_P24_HISTORICAL_INTEGRATED_FEATURE_ROWS',
      currentOutcomeFieldsPresent:false,
      futureBarsUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P21_PROSPECTIVE_FEATURE_FEED_SAFETY,
  });
}

export default { buildProspectiveP21FeatureFeed, PHASE57_P21_PROSPECTIVE_FEATURE_FEED_SAFETY };
