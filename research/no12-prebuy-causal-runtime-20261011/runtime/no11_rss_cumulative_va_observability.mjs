/**
 * Original No.1.1 native Va feasibility from REAL vendor RSS Market cumulative
 * turnover/volume/VWAP snapshots. NO fabricated source-time or broker atomicity.
 * An observation-derived delta is NOT certified per-minute J-Quants Va.
 * Do not feed into frozen production as native minute Va without separate parity.
 */
const SCHEMA='ARK_NO11_RSS_CUMULATIVE_VA_FEASIBILITY_V1';
const DEC=/^(?:0|[1-9]\d*)(?:\.\d+)?$/;
const STAMP=/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$/;
const SYM=/^[0-9A-Z]{4}\.T$/;
function decimal(value){
 if(typeof value!=='string'||value.length>60||!DEC.test(value))return null;
 const n=Number(value);return Number.isFinite(n)&&n>=0?n:null;
}
function time(s){if(typeof s!=='string'||!STAMP.test(s))return null;const n=Date.parse(s);return Number.isFinite(n)?n:null;}
export function observeNo11RssCumulativeVa({record,observedEndJst}={}){
 const empty={schemaId:SCHEMA,status:'SOURCE_INCOMPLETE',symbol:record?.symbol??null,
  nativeOneMinuteVaCertified:false,usedCloseTimesVolume:false,
  turnoverUpdateClockCertified:false,observedUnitScale:null,
  cumulativeTurnoverYenObserved:null};
 if(!record||!SYM.test(record.symbol)||time(observedEndJst)===null||
    typeof record.marketDate!=='string'||!/^20\d\d-\d\d-\d\d$/.test(record.marketDate)||
    observedEndJst.slice(0,10)!==record.marketDate)return empty;
 const v=decimal(record.cumulativeVolumeRaw);
 const a=decimal(record.cumulativeTurnoverRaw);
 const w=decimal(record.vendorVolumeWeightedAverage);
 if(v===null||a===null||w===null||v<=0||w<=0)return empty;
 const errors=[1,1000].map(scale=>({
   scale,errorPct:100*Math.abs((a*scale/v)/w-1)
 }));
 errors.sort((x,y)=>x.errorPct-y.errorPct);
 const best=errors[0],ambiguous=Math.abs(errors[0].errorPct-errors[1].errorPct)<0.00001;
 if(ambiguous||!Number.isFinite(best.errorPct)||best.errorPct>=0.5)
   return {...empty,status:'TURNOVER_VWAP_RATIO_MISMATCH',
      cumulativeVolumeRaw:v,cumulativeTurnoverRaw:a,
      vendorVWAP:w,ratioResidualPct:best.errorPct};
 return {
   schemaId:SCHEMA,status:'VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA',
   symbol:record.symbol,session:record.marketDate,
   observedEndJst,cumulativeVolumeRaw:v,cumulativeTurnoverRaw:a,
   vendorVWAP:w,observedUnitScale:best.scale,
   ratioResidualPct:best.errorPct,
   cumulativeTurnoverYenObserved:a*best.scale,
   vendorSnapshotAtomicCertified:false,turnoverUpdateClockCertified:false,
   nativeOneMinuteVaCertified:false,usedCloseTimesVolume:false,
   orderTransmission:false,productionReady:false
 };
}
/**
 * Compares two LOCAL reception snapshots. Can only say the RECEIVED cumulative
 * counters advanced: neither the provider's exact Va minute boundary nor
 * matching raw trade set is established.
 */
export function inspectNo11ObservedTurnoverInterval({
 earlier,later,chartOneMinuteVolume
}={}){
 const blocked=reason=>({
  schemaId:'ARK_NO11_RSS_VA_OBSERVED_INTERVAL_V1',status:'BLOCKED_'+reason,
  nativeOneMinuteVaCertified:false,
  frozenSelectorProductionVaAllowed:false,
  orderTransmission:false,productionReady:false
 });
 if(earlier?.status!=='VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA'||
   later?.status!=='VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA'||
   earlier.symbol!==later.symbol||earlier.session!==later.session||
   earlier.observedUnitScale!==later.observedUnitScale)
   return blocked('CUMULATIVE_SOURCE_INCOMPATIBLE');
 const first=time(earlier.observedEndJst),last=time(later.observedEndJst);
 if(first===null||last===null||last<=first||last-first>90_000)
   return blocked('OBSERVATION_INTERVAL_GAP_OR_TIME');
 const vol=later.cumulativeVolumeRaw-earlier.cumulativeVolumeRaw;
 const va=later.cumulativeTurnoverYenObserved-earlier.cumulativeTurnoverYenObserved;
 if(vol<0||va<0||!Number.isFinite(vol)||!Number.isFinite(va)||
   (vol===0)!==(va===0))
   return blocked('COUNTER_REVERSED_OR_INCONSISTENT');
 if(!Number.isSafeInteger(chartOneMinuteVolume)||chartOneMinuteVolume<0)
   return blocked('CHART_ONE_MINUTE_VOLUME_UNVERIFIED');
 if(vol!==chartOneMinuteVolume)
   return blocked('CHART_VOLUME_AND_CUMULATIVE_DELTA_MISMATCH');
 return {
   schemaId:'ARK_NO11_RSS_VA_OBSERVED_INTERVAL_V1',
   status:'RECEIVED_COUNTER_DELTA_WITH_MATCHING_1M_VOLUME',
   symbol:earlier.symbol,session:earlier.session,
   intervalFirstReceivedAtJst:earlier.observedEndJst,
   intervalLastReceivedAtJst:later.observedEndJst,
   observationSpanMs:last-first,
   observedVolumeDelta:vol,chartOneMinuteVolume,
   turnoverDeltaYenObserved:va,
   exactExchangeMinuteBoundaryCertified:false,
   providerTurnoverTimestampCertified:false,
   sourceTradeListCompleteCertified:false,
   nativeOneMinuteVaCertified:false,
   frozenSelectorProductionVaAllowed:false,
   orderTransmission:false,productionReady:false
 };
}
