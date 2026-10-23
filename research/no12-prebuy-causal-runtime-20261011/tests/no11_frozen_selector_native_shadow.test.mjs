import test from 'node:test';
import assert from 'node:assert/strict';
import {
 inspectFrozenSelectorAsset,runOriginalFrozenSelectorShadow
} from '../runtime/no11_frozen_selector_native_shadow.mjs';
import {OBSERVED_PASS_GATE_ID} from '../runtime/no11_observed_pass_watch_gate.mjs';

const day='2026-10-26', prior='2026-10-23';
const codes=['1111.T','2222.T','3333.T'];
function mask(symbols=codes){
 return {
  schemaId:OBSERVED_PASS_GATE_ID,asOfSession:prior,
  observedPassSymbols:symbols,observedPassCount:symbols.length,
  shadowOnly:true,productionReady:false,orderTransmission:false,
  strictNoUnknownFallback:true
 };
}
function master(symbols=codes){
 return symbols.map((symbol,i)=>({
  symbol,asOfSession:day,rawPreviousClose:100+i*25,
  segment:'PRIME',sector:'01',corporateActionsCleared:true,
  priceBasisVerified:true,commonEquity:true
 }));
}
function source(){
 return {
  schemaId:'ARK_NO11_NATIVE_MINUTE_VA_INPUT_RECEIPT_V1',
  readOnly:true,orderTransmission:false,
  priceBasis:'RAW_COMPARABLE_FOR_DAILY_REFERENCE',
  minuteVaUnit:'JPY_EXACT',
  minuteVaMethod:'SUM_EXECUTED_PRICE_TIMES_QUANTITY',
  minuteVaSourceCertified:true,
  completeFilteredUniverseCoverage:true,
  datedMasterCertified:true,
  corporateActionsCertified:true,
  observedAtJst:day+'T10:00:00+09:00'
 };
}
const clock=(min)=>{
 const m=9*60+min;
 return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
};
function raws(symbols=codes,length=60){
 const result=[];
 symbols.forEach((symbol,k)=>{
  for(let m=0;m<length;m++){
   const c=100+25*k+0.015*m+0.1*Math.sin(m/5+k),
    v=100+k*20+(m%7);
   result.push({
    Date:day,Code:symbol,Time:clock(m),
    O:c-0.02,H:c+0.12,L:c-0.13,C:c,Vo:v,Va:c*v,
    knownAtJst:day+'T'+clock(m+1)+':00+09:00'
   });
  }
 });
 return result;
}
function input(){
 return {
  sessionDate:day,decisionTimeJst:'10:00',mask:mask(),
  sourceReceipt:source(),datedMaster:master(),nativeMinuteRows:raws(),
  previousWatches:[]
 };
}
test('actual original frozen model artifact and 10 timestamps are pinned',()=>{
 const asset=inspectFrozenSelectorAsset();
 assert.equal(asset.spec.model.configuration.candidateId,'RIDGE_Y30');
 assert.equal(asset.spec.ranking.topN,5);
 assert.equal(asset.spec.ranking.decisionTimesJst.length,10);
});
test('real original model path ranks actual finite minute Va features, no fit',()=>{
 const r=runOriginalFrozenSelectorShadow(input());
 assert.equal(r.frozenRidgeParametersUnchanged,true);
 assert.equal(r.observedCandidatePool,3);
 assert.equal(r.nativeMinuteRowsInspected,180);
 assert.ok(r.selected.length>0 && r.selected.length<=3,
   JSON.stringify(r.skippedCandidates));
 assert.equal(r.originalCrossSectionReferenceUnchanged,false);
 assert.equal(r.productionReady,false);
 assert.equal(r.orderTransmission,false);
 assert.equal(r.firstEntryP1Executed,false);
 assert.equal(r.watchEvents[0].watchEventType,'WATCH_FIRST_SELECTION');
 assert.match(r.watchEvents[0].firstWatchIdentity,/2026-10-26\|/);
 for(const selected of r.selected){
  assert.equal(typeof selected.savedV1Score,'number');
  assert.equal(selected.referenceAgeMin,0);
 }
 const replay=runOriginalFrozenSelectorShadow({
  ...input(),previousWatches:r.nextWatches
 });
 assert.equal(replay.selected.length,r.selected.length);
 for(const ev of replay.watchEvents){
  assert.equal(ev.watchEventType,'WATCH_REFRESH');
  assert.equal(ev.firstWatchIdentity,day+'|'+ev.symbol);
 }
});
test('future, missing, zero or unauthenticated minute Va blocks',()=>{
 const v=input();v.nativeMinuteRows[0].Va=undefined;
 assert.throws(()=>runOriginalFrozenSelectorShadow(v),/MINUTE_NUMERIC_REQUIRED/);
 const z=input();z.nativeMinuteRows[0].Va=0;
 assert.throws(()=>runOriginalFrozenSelectorShadow(z),/MINUTE_OHLCV_VA_INVALID/);
 const s=input();s.sourceReceipt.minuteVaSourceCertified=false;
 assert.throws(()=>runOriginalFrozenSelectorShadow(s),/SOURCE_INCOMPLETE_OR_UNVERIFIED/);
 const f=input();f.nativeMinuteRows.at(-1).knownAtJst=day+'T10:00:01+09:00';
 assert.throws(()=>runOriginalFrozenSelectorShadow(f),/MINUTE_NOT_CAUSAL_OR_NOT_OBSERVED/);
});
test('wrong prior daily mask and forged new symbol block',()=>{
 const bad=input();bad.mask.asOfSession='2026-10-22';
 assert.throws(()=>runOriginalFrozenSelectorShadow(bad),/DAYPASS_MASK_STALE_OR_UNSAFE/);
 const injected=input();injected.nativeMinuteRows.push({...injected.nativeMinuteRows[0],Code:'9999.T'});
 assert.throws(()=>runOriginalFrozenSelectorShadow(injected),/MINUTE_IDENTITY_INVALID/);
});
test('no complete 1m feed means no fake 5-minute price or native Top5',()=>{
 const x=input();x.nativeMinuteRows=raws(codes,2);
 const result=runOriginalFrozenSelectorShadow(x);
 assert.equal(result.rankableCandidates,0);
 assert.equal(result.selected.length,0);
 assert.equal(result.shadowOnly,true);
});
test('missing dated master, wrong market decision clock, duplicate minute fails closed',()=>{
 const b=input();b.datedMaster.pop();
 assert.throws(()=>runOriginalFrozenSelectorShadow(b),/PASS_SYMBOL_MISSING_FROM_MASTER/);
 const c=input();c.decisionTimeJst='09:31';
 assert.throws(()=>runOriginalFrozenSelectorShadow(c),/NOT_ORIGINAL_DECISION_TIME/);
 const d=input();d.nativeMinuteRows.push({...d.nativeMinuteRows[0]});
 assert.throws(()=>runOriginalFrozenSelectorShadow(d),/MINUTE_DUPLICATE/);
});
