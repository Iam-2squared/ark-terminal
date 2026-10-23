/**
 * No.1.1 ORIGINAL Selector — minimal RSS-observed daily uptrend candidate mask.
 * No training, no model change, no RSS, no broker/order side effects.
 * Never certifies the original market-wide cross-sectional/Va inputs.
 */
import {inspectDailyCapture, summarizeDailyCaptures} from './no11_rss_daily_trend_census.mjs';

export const OBSERVED_PASS_GATE_ID='ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1';
const symbolOK=s=>typeof s==='string'&&/^[0-9A-Z]{4}\.T$/.test(s);
export function makeObservedPassWatchMask(plan,captures){
  const {summary}=summarizeDailyCaptures(plan,captures);
  if(summary.status!=='COMPLETE_OBSERVED_STRUCTURE_ONLY')
    throw Error('NO11_DAYPASS_FULL_CAPTURE_REQUIRED');
  const passed=new Set();
  for(const capture of captures){
    const outcome=inspectDailyCapture(capture,plan);
    if(outcome.status==='PASS')passed.add(capture.symbol);
  }
  const symbols=plan.symbols.filter(symbol=>passed.has(symbol));
  if(symbols.length!==summary.observedStructureCounts.PASS)
    throw Error('NO11_DAYPASS_COUNT_MISMATCH');
  return {
    schemaId:OBSERVED_PASS_GATE_ID,
    asOfSession:plan.asOfSession,planId:plan.planId,
    source:'RSS_CHART_UNVERIFIED_DAILY_CLOSES',
    observedPassSymbols:symbols,
    observedPassCount:symbols.length,
    excludedFromActiveWatchCount:plan.symbols.length-symbols.length,
    dataStillUnknown:summary.observedStructureCounts.UNKNOWN,
    strictNoUnknownFallback:true,
    originalIntradayTop5SchedulePreserved:true,
    originalSelectorMarketBreadthResolved:false,
    minuteVaResolved:false,
    priceBasisCertified:false,corporateActionsCertified:false,
    originalSelectorExecuted:false,shadowOnly:true,
    productionReady:false,orderTransmission:false
  };
}
/**
 * Fail-closed prerequisite for a prospective BUY decision. This guard alone
 * NEVER authorizes an order. Existing original Entry/Capital and RSS safety
 * checks must independently pass after the original candidate is selected.
 */
export function checkObservedPassBeforeBuy({mask,symbol,priorSession}={}){
  if(!mask||mask.schemaId!==OBSERVED_PASS_GATE_ID||
     mask.shadowOnly!==true||mask.productionReady!==false||
     mask.orderTransmission!==false||
     mask.strictNoUnknownFallback!==true)
    return {dailyGatePassed:false,reason:'INVALID_DAYPASS_MANIFEST',orderAuthorized:false};
  if(typeof priorSession!=='string'||mask.asOfSession!==priorSession)
    return {dailyGatePassed:false,reason:'STALE_OR_WRONG_DAILY_SESSION',orderAuthorized:false};
  if(!symbolOK(symbol)||!Array.isArray(mask.observedPassSymbols)||
     mask.observedPassCount!==mask.observedPassSymbols.length||
     new Set(mask.observedPassSymbols).size!==mask.observedPassSymbols.length||
     mask.observedPassSymbols.some(s=>!symbolOK(s)))
    return {dailyGatePassed:false,reason:'INVALID_SYMBOL_OR_MANIFEST',orderAuthorized:false};
  if(!mask.observedPassSymbols.includes(symbol))
    return {dailyGatePassed:false,reason:'NOT_CONFIRMED_UPTREND',orderAuthorized:false};
  return {dailyGatePassed:true,reason:'OBSERVED_DAILY_PASS_ONLY_FURTHER_CHECKS_REQUIRED',
    orderAuthorized:false};
}
