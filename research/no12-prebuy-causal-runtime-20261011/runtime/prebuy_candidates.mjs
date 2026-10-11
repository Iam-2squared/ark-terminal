/**
 * No.1.2 independent pre-buy research candidate gate.
 * It is NOT the Frozen No.1.1 H2/H3/H5 R0 rank, model, or BUY decision.
 * All events must be present before the decision. No execution methods.
 */
import {CAUSAL_FRAME_SCHEMA,inspectNo11ProspectiveAsOf} from '../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {digest} from '../../integration/no1-1-msii/runtime/locked_intent.mjs';

export const NO12_CANDIDATES_SCHEMA='ARK_NO12_PREBUY_RESEARCH_BATCH_V1';
const bad=reason=>{throw Error(reason)};
const ms=(time,label)=>{
 if(typeof time!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(time)||!Number.isFinite(Date.parse(time)))bad(label);
 return Date.parse(time);
};
const codeOf=value=>{
 const s=String(value??'').trim().toUpperCase();
 if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(s))bad('PREBUY_SYMBOL_INVALID');
 return s.endsWith('.T')?s:s+'.T';
};
const localTime=time=>new Intl.DateTimeFormat('en-GB',{
 timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
}).format(new Date(time));
function externalSymbols(baseline){
 if(baseline?.schemaId!=='ARK_CASH_OWNERSHIP_BASELINE_V1'||baseline.frozen!==true)bad('OWNERSHIP_BASELINE_REQUIRED');
 const {baselineSha256,...core}=baseline;
 if(digest(core)!==baselineSha256)bad('OWNERSHIP_BASELINE_HASH_INVALID');
 if(!Array.isArray(baseline.externalPositions)||!Array.isArray(baseline.arkManagedPositions))
   bad('OWNERSHIP_ARRAYS_REQUIRED');
 const external=new Set(),ark=new Set();
 for(const p of baseline.externalPositions){
   const s=codeOf(p.symbol);
   if(!Number.isSafeInteger(p.quantity)||p.quantity<=0||external.has(s))bad('EXTERNAL_POSITION_INVALID');
   external.add(s);
 }
 for(const p of baseline.arkManagedPositions){
   const s=codeOf(p.symbol);
   if(!Number.isSafeInteger(p.quantity)||p.quantity<100||p.quantity%100!==0||ark.has(s)||external.has(s))
     bad('ARK_OWNERSHIP_INVALID');
   ark.add(s);
 }
 if(ark.size>3)bad('ARK_MAX3_EXCEEDED');
 return {external,ark};
}
function requiredObservation(obs,id,decisionMs,allowedSources){
 if(typeof id!=='string'||!obs.has(id))bad('PREBUY_OBSERVATION_MISSING');
 const x=obs.get(id);
 if(!allowedSources.includes(x.sourceType))bad('PREBUY_OBSERVATION_TYPE_INVALID');
 if(ms(x.knownAt,'PREBUY_OBSERVATION_TIME_INVALID')>decisionMs)bad('PREBUY_OBSERVATION_FUTURE');
 return x;
}
const scoreOf=(value,name)=>{
 if(typeof value!=='number'||!Number.isFinite(value)||value<=0)bad(name);
 return value;
};
export function rankNo12PreBuyResearch({
  mode,batch,observationFrame,ownership,now=new Date()
}={}){
 if(mode!=='SYNTHETIC_OFFLINE_ONLY')bad('NO12_LIVE_STRATEGY_NOT_VALIDATED');
 if(batch?.schemaId!==NO12_CANDIDATES_SCHEMA||!Array.isArray(batch.candidates))
   bad('NO12_BATCH_INVALID');
 if(observationFrame?.schemaId!==CAUSAL_FRAME_SCHEMA)bad('NO12_SOURCE_FRAME_INVALID');
 const evidence=inspectNo11ProspectiveAsOf({frame:observationFrame,now});
 const decisionMs=ms(observationFrame.decisionAt,'NO12_DECISION_TIME_INVALID');
 if(batch.session!==observationFrame.session||
    batch.decisionAt!==observationFrame.decisionAt)bad('NO12_BATCH_SOURCE_CLOCK_MISMATCH');
 const owned=externalSymbols(ownership);
 const inputs=new Map(observationFrame.records.map(x=>[x.recordId,x]));
 const seenIds=new Set(),seenSymbols=new Set();
 const eligible=[],declined=[];
 for(const r of batch.candidates){
   if(!r||typeof r!=='object'||Array.isArray(r))bad('NO12_CANDIDATE_INVALID');
   const eventId=r.entryId;
   if(typeof eventId!=='string'||!/^[a-zA-Z0-9_.:-]{1,128}$/.test(eventId)||seenIds.has(eventId))
     bad('NO12_ORIGINAL_ENTRY_ID_DUPLICATE_OR_INVALID');
   seenIds.add(eventId);
   const symbol=codeOf(r.symbol);
   if(seenSymbols.has(symbol))bad('NO12_SAME_BATCH_SYMBOL_DUPLICATE');
   seenSymbols.add(symbol);
   const first=requiredObservation(inputs,r.selectorRecordId,decisionMs,
     ['TRADINGVIEW_SCANNER_OBSERVATION','ORIGINAL_NATIVE_FEATURE_OBSERVATION']);
   const primary=requiredObservation(inputs,r.stateRecordId,decisionMs,
     ['ORIGINAL_NATIVE_FEATURE_OBSERVATION']);
   const price=requiredObservation(inputs,r.marketRecordId,decisionMs,
     ['MARKETSPEED_II_RSS_MARKET_OBSERVATION','YAHOO_CLOSED_5M_RESEARCH_OBSERVATION']);
   const available=ms(r.candidateKnownAt,'NO12_ENTRY_KNOWN_AT_INVALID');
   if(available>decisionMs||available<Math.max(ms(first.knownAt,'NO12_SELECTOR_KNOWN_AT'),
     ms(primary.knownAt,'NO12_STATE_KNOWN_AT'),ms(price.knownAt,'NO12_PRICE_KNOWN_AT')))
     bad('NO12_CANDIDATE_NOT_AVAILABLE_BEFORE_DECISION');
   const score=scoreOf(r.firstEntryScore,'NO12_FIRST_ENTRY_SCORE_INVALID');
   const threshold=scoreOf(r.firstEntryThreshold,'NO12_FIRST_ENTRY_THRESHOLD_INVALID');
   const priceValue=scoreOf(r.referencePrice,'NO12_REFERENCE_PRICE_INVALID');
   if(!Number.isSafeInteger(r.quantity)||r.quantity<100||r.quantity%100!==0)
     bad('NO12_100_SHARE_LOT_REQUIRED');
   if(r.usesPostFillPrice===true||r.usesPostFillDelay===true||r.originalFrozenR0===true)
     bad('NO12_POSTFILL_LEAK_OR_FALSE_ORIGINAL_RANK');
   let reason=null;
   if(owned.external.has(symbol))reason='EXTERNAL_PERSONAL_SYMBOL_PROTECTED';
   else if(owned.ark.has(symbol))reason='DUPLICATE_ARK_SYMBOL';
   else if(localTime(decisionMs)>='15:20')reason='AFTER_1520_CUTOFF';
   else if(r.formalState9Primary==='PULLBACK'||r.formalState9Primary==='SHARP_DROP')
     reason='FROZEN_STATE_EXCLUDED';
   else if(typeof r.formalState9Primary!=='string'||
     !new Set(['RISE_STOP','RISE','SHARP_RISE','RANGE','REBOUND','DROP','DROP_STOP']).has(r.formalState9Primary))
     reason='FORMAL_STATE_UNAVAILABLE';
   else if(score<threshold)reason='FIRST_ENTRY_THRESHOLD_NOT_MET';
   const item=Object.freeze({
     entryId:eventId,symbol,session:batch.session,decisionAt:batch.decisionAt,
     formalState9Primary:r.formalState9Primary,quantity:r.quantity,
     syntheticReferencePrice:priceValue,
     researchPreBuyRatio:score/threshold,
     selectorRecordId:r.selectorRecordId,stateRecordId:r.stateRecordId,
     marketRecordId:r.marketRecordId,sourceKnownAt:r.candidateKnownAt,
     status:reason?'DECLINED':'RESEARCH_CANDIDATE_ONLY',reason,
     brokerOrderAllowed:false
   });
   (reason?declined:eligible).push(item);
 }
 eligible.sort((a,b)=>b.researchPreBuyRatio-a.researchPreBuyRatio||
   a.entryId.localeCompare(b.entryId)||a.symbol.localeCompare(b.symbol));
 return Object.freeze({
   schemaId:'ARK_NO12_PREBUY_RESEARCH_RESULT_V1',
   status:'SYNTHETIC_PREBUY_ONLY_NOT_FROZEN_NO11',
   sourceFrameSha256:evidence.sourceFrameSha256,
   eligible:Object.freeze(eligible),declined:Object.freeze(declined),
   originalFrozenR0Reproduced:false,realMarketFeedCertified:false,
   strategyPerformanceValidated:false,productionReady:false,
   orderTransmission:false
 });
}
