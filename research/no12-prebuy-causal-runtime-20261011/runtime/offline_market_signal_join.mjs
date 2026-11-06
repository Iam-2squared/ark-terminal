/**
 * Ark No.1.2 source join: RssChart READ ONLY + Selector/First Entry observation
 * + formally observed State9 Primary -> exactly one offline research candidate.
 *
 * NO NATIVE PREDICTOR EXISTS IN THIS MODULE. Inputs are explicitly synthetic
 * scenario records, never live-trading attestations or broker instructions.
 */
import {CAUSAL_FRAME_SCHEMA,inspectNo11ProspectiveAsOf} from
  '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {NO12_CANDIDATES_SCHEMA,rankNo12PreBuyResearch} from './prebuy_candidates.mjs';
import {bindNo12SyntheticChartReference} from './msii_rss_chart_observation.mjs';

const fail=s=>{throw Error(s)};
const time=(v,label)=>{
 if(typeof v!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(v)||!Number.isFinite(Date.parse(v)))
   fail(label);
 return Date.parse(v);
};
const symbol=x=>{
 const s=String(x??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}\.T$/.test(s))fail('NO12_SOURCE_JOIN_SYMBOL_INVALID');
 return s;
};
const day=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
 year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t)).replace(/\//g,'-');

function reviewSource(input,label,type){
 if(!input||typeof input!=='object'||Array.isArray(input)||
   input.evidenceMode!=='OBSERVED_READ_ONLY'||input.symbol===undefined)
   fail('NO12_'+label+'_SOURCE_MISSING');
 const s=symbol(input.symbol);
 const row=input.observation;
 if(!row||row.sourceType!==type||row.evidenceMode!=='OBSERVED_READ_ONLY'||
    typeof row.recordId!=='string'||!row.recordId)
   fail('NO12_'+label+'_OBSERVATION_CONTRACT_INVALID');
 if(input.sourceCertified===true||input.nativeDecisionCertified===true||
    input.productionReady===true||input.orderTransmission===true)
   fail('NO12_'+label+'_LIVE_SOURCE_CLAIM_FORBIDDEN');
 return {input,symbol:s,row};
}
export function assembleNo12OfflineChartCandidate({
 mode,chartAudit,selectorInput,stateInput,ownership,
 decisionAt,syntheticQuantity,now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_REAL_SOURCE_JOIN_NOT_IMPLEMENTED');
 if(chartAudit?.status!=='LOCAL_CHART_5M_BAR_OBSERVED_READONLY_NOT_LIVE_CERTIFIED'||
    chartAudit.actualBrokerFeedArrivalCertified!==false||
    chartAudit.productionReady!==false||chartAudit.orderTransmission!==false||
    chartAudit.sourceRecord?.sourceType!=='MARKETSPEED_II_RSS_MARKET_OBSERVATION')
   fail('NO12_CHART_NOT_A_VERIFIED_READONLY_OBSERVATION');
 const s=symbol(chartAudit.symbol);
 const selector=reviewSource(selectorInput,'SELECTOR',
   'TRADINGVIEW_SCANNER_OBSERVATION');
 const state=reviewSource(stateInput,'STATE9','ORIGINAL_NATIVE_FEATURE_OBSERVATION');
 if(selector.symbol!==s||state.symbol!==s)fail('NO12_SOURCE_JOIN_SYMBOL_MISMATCH');
 if(!Number.isSafeInteger(syntheticQuantity)||syntheticQuantity<100||
    syntheticQuantity%100!==0)fail('NO12_SOURCE_JOIN_SYNTHETIC_100_LOT_REQUIRED');
 if(typeof selectorInput.entryId!=='string'||!selectorInput.entryId.trim())
    fail('NO12_SOURCE_JOIN_ORIGINAL_ENTRY_ID_REQUIRED');
 if(!Number.isFinite(selectorInput.firstEntryScore)||
    !Number.isFinite(selectorInput.firstEntryThreshold)||
    selectorInput.firstEntryScore<=0||selectorInput.firstEntryThreshold<=0)
    fail('NO12_SOURCE_JOIN_FIRST_ENTRY_SCORE_NOT_PROVIDED');
 if(typeof stateInput.formalState9Primary!=='string')
    fail('NO12_SOURCE_JOIN_FORMAL_STATE_NOT_PROVIDED');
 const decisionTime=time(decisionAt,'NO12_SOURCE_JOIN_DECISION_AT_INVALID');
 const nowMs=now instanceof Date?now.getTime():time(now,'NO12_SOURCE_JOIN_NOW_INVALID');
 if(!Number.isFinite(nowMs)||decisionTime>nowMs+1000)
    fail('NO12_SOURCE_JOIN_DECISION_NOT_YET_OBSERVED');
 const knowns=[selector.row.knownAt,state.row.knownAt,chartAudit.sourceRecord.knownAt];
 for(const t of knowns)if(time(t,'NO12_SOURCE_JOIN_INPUT_KNOWN_AT_INVALID')>decisionTime)
    fail('NO12_SOURCE_JOIN_FUTURE_INPUT');
 const knownAt=new Date(Math.max(...knowns.map(v=>time(v,'NO12_SOURCE_JOIN_CLOCK_INVALID')))).toISOString();
 const frame={schemaId:CAUSAL_FRAME_SCHEMA,session:day(decisionTime),
    decisionAt,records:[selector.row,state.row,chartAudit.sourceRecord]};
 // Check all source as-of / captured / known dates before deriving anything.
 inspectNo11ProspectiveAsOf({frame,now});
 const candidate=bindNo12SyntheticChartReference({
   candidate:{
     entryId:selectorInput.entryId,symbol:s,
     selectorRecordId:selector.row.recordId,
     stateRecordId:state.row.recordId,
     formalState9Primary:stateInput.formalState9Primary,
     firstEntryScore:selectorInput.firstEntryScore,
     firstEntryThreshold:selectorInput.firstEntryThreshold,
     quantity:syntheticQuantity,candidateKnownAt:knownAt
   },chartAudit,requestedDecisionAt:decisionAt
 });
 const batch={schemaId:NO12_CANDIDATES_SCHEMA,session:frame.session,
    decisionAt,candidates:[candidate]};
 const candidateResult=rankNo12PreBuyResearch({
   mode:'SYNTHETIC_OFFLINE_ONLY',batch,observationFrame:frame,ownership,now
 });
 if(candidateResult.sourceFrameSha256===null)fail('NO12_SOURCE_FRAME_HASH_UNAVAILABLE');
 return Object.freeze({
   schemaId:'ARK_NO12_OFFLINE_OBSERVED_INPUT_JOIN_V1',
   status:'SYNTHETIC_CHART_SELECTOR_STATE_JOIN_NOT_LIVE',
   candidateResult,
   selectedRecordIds:Object.freeze([
      selector.row.recordId,state.row.recordId,chartAudit.sourceRecord.recordId
   ]),
   latestInputKnownAt:knownAt,
   actualBrokerMarketArrivalCertified:false,
   originalNativeSelectorCertified:false,
   originalNativeState9Certified:false,
   originalFrozenNo11R0Reproduced:false,
   productionReady:false,orderTransmission:false
 });
}
