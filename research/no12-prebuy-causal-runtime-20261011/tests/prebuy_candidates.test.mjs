import test from 'node:test';
import assert from 'node:assert/strict';
import {rankNo12PreBuyResearch,NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const ts='2026-10-13T09:36:00+09:00';
function fixture(){
 const known='2026-10-13T09:35:01+09:00';
 const obs=(recordId,sourceType)=>({
  recordId,sourceType,evidenceMode:'OBSERVED_READ_ONLY',
  sourceAsOf:'2026-10-13T09:35:00+09:00',observedAt:known,knownAt:known
 });
 const observationFrame={schemaId:CAUSAL_FRAME_SCHEMA,session:'2026-10-13',
  decisionAt:ts,records:[
   obs('selector','TRADINGVIEW_SCANNER_OBSERVATION'),
   obs('state','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
   obs('market','MARKETSPEED_II_RSS_MARKET_OBSERVATION')
  ]};
 const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:known,
   source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
   externalPositions:[{symbol:'408A.T',quantity:100}],arkManagedPositions:[]};
 const ownership={...core,baselineSha256:digest(core)};
 const candidate={entryId:'first-001',symbol:'7203',selectorRecordId:'selector',
   stateRecordId:'state',marketRecordId:'market',
   candidateKnownAt:known,firstEntryScore:0.7,firstEntryThreshold:0.5,
   referencePrice:1000,quantity:100,formalState9Primary:'RISE'};
 const batch={schemaId:NO12_CANDIDATES_SCHEMA,session:'2026-10-13',decisionAt:ts,
  candidates:[candidate]};
 return {mode:'SYNTHETIC_OFFLINE_ONLY',observationFrame,batch,ownership,
  now:new Date('2026-10-13T09:36:05+09:00')};
}
test('genuine point-in-time input shape yields a RESEARCH candidate, never executable No1.1 intent',()=>{
 const x=rankNo12PreBuyResearch(fixture());
 assert.equal(x.eligible.length,1);assert.equal(x.declined.length,0);
 assert.equal(x.eligible[0].symbol,'7203.T');
 assert.equal(x.eligible[0].researchPreBuyRatio,1.4);
 assert.equal(x.originalFrozenR0Reproduced,false);
 assert.equal(x.productionReady,false);assert.equal(x.orderTransmission,false);
});
test('PULLBACK and SHARP_DROP excluded before rank; unavailable State is not inferred',()=>{
 for(const s of ['PULLBACK','SHARP_DROP','UNAVAILABLE']){
  const x=fixture();x.batch.candidates[0].formalState9Primary=s;
  const r=rankNo12PreBuyResearch(x);
  assert.equal(r.eligible.length,0);
  assert.equal(r.declined[0].reason,s==='UNAVAILABLE'?'FORMAL_STATE_UNAVAILABLE':'FROZEN_STATE_EXCLUDED');
 }
});
test('external personal holdings and duplicate Ark positions cannot be offered as new BUY',()=>{
 const a=fixture();a.batch.candidates[0].symbol='408A';
 assert.equal(rankNo12PreBuyResearch(a).declined[0].reason,'EXTERNAL_PERSONAL_SYMBOL_PROTECTED');
 const b=fixture();
 const core={...b.ownership,arkManagedPositions:[{symbol:'7203.T',quantity:100}]};
 delete core.baselineSha256;b.ownership={...core,baselineSha256:digest(core)};
 assert.equal(rankNo12PreBuyResearch(b).declined[0].reason,'DUPLICATE_ARK_SYMBOL');
});
test('score below threshold and 15:20 cutoff leave slot empty without forced backfill',()=>{
 const x=fixture();x.batch.candidates[0].firstEntryScore=.1;
 assert.equal(rankNo12PreBuyResearch(x).declined[0].reason,'FIRST_ENTRY_THRESHOLD_NOT_MET');
 const y=fixture();
 y.observationFrame.decisionAt='2026-10-13T15:20:00+09:00';y.batch.decisionAt=y.observationFrame.decisionAt;
 y.now=new Date('2026-10-13T15:20:02+09:00');
 assert.equal(rankNo12PreBuyResearch(y).declined[0].reason,'AFTER_1520_CUTOFF');
});
test('not permitted to silently substitute original H2 H3 H5 R0 or a forecast fill',()=>{
 for(const k of ['originalFrozenR0','usesPostFillPrice','usesPostFillDelay']){
  const x=fixture();x.batch.candidates[0][k]=true;
  assert.throws(()=>rankNo12PreBuyResearch(x),/NO12_POSTFILL_LEAK/);
 }
});
test('time, missing source, duplicate canonical entry ID and wrong source fail closed',()=>{
 const x=fixture();x.batch.candidates[0].candidateKnownAt='2026-10-13T09:34:59+09:00';
 assert.throws(()=>rankNo12PreBuyResearch(x),/NOT_AVAILABLE_BEFORE_DECISION/);
 const y=fixture();y.observationFrame.records.pop();
 assert.throws(()=>rankNo12PreBuyResearch(y),/PREBUY_OBSERVATION_MISSING/);
 const z=fixture();z.batch.candidates.push({...z.batch.candidates[0]});
 assert.throws(()=>rankNo12PreBuyResearch(z),/ORIGINAL_ENTRY_ID_DUPLICATE/);
 const n=fixture();n.observationFrame.records[0].knownAt='2026-10-13T09:37:00+09:00';
 assert.throws(()=>rankNo12PreBuyResearch(n),/CAUSAL_/);
});
test('no real strategy promotion, no additional user approval and 0-yen research still possible',()=>{
 const x=fixture();x.mode='LIVE_ATTESTED';
 assert.throws(()=>rankNo12PreBuyResearch(x),/NO12_LIVE_STRATEGY_NOT_VALIDATED/);
 const y=fixture();assert.equal(rankNo12PreBuyResearch(y).status,'SYNTHETIC_PREBUY_ONLY_NOT_FROZEN_NO11');
});
