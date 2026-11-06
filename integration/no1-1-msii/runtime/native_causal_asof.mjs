// Native No.1.1 prospective source clock boundary, READ ONLY.
// Validates only what was available at a decision cutoff. Never invents
// Selector, State9, Entry, EXIT, private model score, or broker receipt time.
import {createHash} from 'node:crypto';
import {canonical} from './locked_intent.mjs';

export const CAUSAL_FRAME_SCHEMA='ARK_NO11_NATIVE_ASOF_OBSERVATION_FRAME_V1';
export const SOURCE_TYPES=Object.freeze([
 'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
 'TRADINGVIEW_SCANNER_OBSERVATION',
 'YAHOO_CLOSED_5M_RESEARCH_OBSERVATION',
 'ORIGINAL_NATIVE_FEATURE_OBSERVATION'
]);
const bad=(s)=>{throw Error(s)};
const timestamp=(s,label)=>{
 if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))
    bad(label);
 return Date.parse(s);
};
const jstDay=ms=>new Intl.DateTimeFormat('en-CA',{
 timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(ms)).replace(/\//g,'-');
const invalidKeys=new Set([
 'futureReturnPct','actualReturnPct','target','label','teacher','tradeWin',
 'futurePnl','realizedPnl','futureMfe','futureMae','outcome','profitLabel'
]);
function inspectRow(record,cutoff,now,index,seen){
 if(!record||typeof record!=='object'||Array.isArray(record))bad('CAUSAL_RECORD_INVALID');
 const id=record.recordId;
 if(typeof id!=='string'||!/^[0-9A-Za-z_.:-]{1,128}$/.test(id)||seen.has(id))
   bad('CAUSAL_RECORD_ID_MISSING_OR_DUPLICATE');
 seen.add(id);
 if(!SOURCE_TYPES.includes(record.sourceType))bad('CAUSAL_SOURCE_NOT_APPROVED');
 if(record.evidenceMode!=='OBSERVED_READ_ONLY')bad('CAUSAL_SOURCE_NOT_PROSPECTIVE_OBSERVED');
 if(Object.keys(record).some(k=>invalidKeys.has(k)))bad('CAUSAL_FUTURE_OUTCOME_CONTAMINATION');
 const asOf=timestamp(record.sourceAsOf,'CAUSAL_SOURCE_CLOCK_INVALID');
 const observed=timestamp(record.observedAt,'CAUSAL_OBSERVATION_CLOCK_INVALID');
 const known=timestamp(record.knownAt,'CAUSAL_KNOWN_CLOCK_INVALID');
 if(asOf>observed||observed>known||known>cutoff||known>now+1000)bad('CAUSAL_FUTURE_OR_OUT_OF_ORDER_INPUT');
 if(record.barClosedAt!==undefined){
   const closed=timestamp(record.barClosedAt,'CAUSAL_BAR_CLOSE_INVALID');
   if(closed>observed||closed>known||closed>cutoff||asOf>closed)bad('CAUSAL_UNCLOSED_BAR_OR_LOOKAHEAD');
 }
 if(record.nativeFrozenValue===true||record.marketFeedArrivalCertified===true||
    record.authorizesTrade===true)bad('CAUSAL_FALSE_LIVE_ATTESTATION');
 return {
   recordId:id,sourceType:record.sourceType,
   sourceAsOf:record.sourceAsOf,observedAt:record.observedAt,
   knownAt:record.knownAt,
   barClosedAt:record.barClosedAt??null
 };
}
export function inspectNo11ProspectiveAsOf({frame,now=new Date()}={}){
 if(!frame||frame.schemaId!==CAUSAL_FRAME_SCHEMA)bad('CAUSAL_FRAME_SCHEMA_INVALID');
 const cutoff=timestamp(frame.decisionAt,'CAUSAL_DECISION_TIME_INVALID');
 const nowMs=now instanceof Date?now.getTime():timestamp(now,'CAUSAL_NOW_INVALID');
 if(!Number.isFinite(nowMs)||cutoff>nowMs+1000)bad('CAUSAL_DECISION_NOT_YET_POSSIBLE');
 if(!/^\d{4}-\d{2}-\d{2}$/.test(frame.session??'')||jstDay(cutoff)!==frame.session)
   bad('CAUSAL_JPX_SESSION_MISMATCH');
 if(!Array.isArray(frame.records)||frame.records.length===0||frame.records.length>10000)
   bad('CAUSAL_RECORD_SET_REQUIRED');
 const seen=new Set();
 const accepted=frame.records.map((r,i)=>inspectRow(r,cutoff,nowMs,i,seen));
 // One canonical receipt is cheap to compute and explicitly NOT an authenticity
 // signature, exchange delivery attestation, or native model inference.
 const receipt=createHash('sha256').update(JSON.stringify(canonical({
   schemaId:CAUSAL_FRAME_SCHEMA,session:frame.session,
   decisionAt:frame.decisionAt,records:accepted
 }))).digest('hex');
 return Object.freeze({
   schemaId:'ARK_NO11_CAUSAL_INPUT_AUDIT_V1',
   status:'PROSPECTIVE_SOURCE_OBSERVED_ONLY_NOT_NATIVE_DECISION',
   session:frame.session,decisionAt:frame.decisionAt,
   recordCount:accepted.length,sourceFrameSha256:receipt,
   actualBrokerMarketDeliveryTimestampCertified:false,
   nativeFrozenFeaturesCertified:false,nativeDecisionPublished:false,
   orderTransmission:false,productionReady:false
 });
}
