import test from 'node:test';
import assert from 'node:assert/strict';
import {CAUSAL_FRAME_SCHEMA,inspectNo11ProspectiveAsOf} from '../runtime/native_causal_asof.mjs';
const t0='2026-10-13T09:35:00+09:00';
const row=()=>({recordId:'7203.T-5m-0930',sourceType:'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
 evidenceMode:'OBSERVED_READ_ONLY',sourceAsOf:'2026-10-13T09:30:00+09:00',
 barClosedAt:'2026-10-13T09:35:00+09:00',
 observedAt:'2026-10-13T09:35:01+09:00',knownAt:'2026-10-13T09:35:01+09:00'});
const frame=(changes={})=>({
 schemaId:CAUSAL_FRAME_SCHEMA,session:'2026-10-13',
 decisionAt:'2026-10-13T09:36:00+09:00',records:[row()],...changes
});
const inspect=x=>inspectNo11ProspectiveAsOf({frame:x,now:new Date('2026-10-13T09:36:10+09:00')});
test('strict causal closed-bar observations are eligible for input audit but never native-trading certified',()=>{
 const a=inspect(frame()),b=inspect(frame());
 assert.deepEqual(a,b);
 assert.equal(a.status,'PROSPECTIVE_SOURCE_OBSERVED_ONLY_NOT_NATIVE_DECISION');
 assert.equal(a.actualBrokerMarketDeliveryTimestampCertified,false);
 assert.equal(a.nativeFrozenFeaturesCertified,false);
 assert.equal(a.nativeDecisionPublished,false);
 assert.equal(a.orderTransmission,false);
 assert.equal(a.productionReady,false);
 assert.equal(a.recordCount,1);
});
test('out-of-order and future-clock observations never leak into a frozen decision',()=>{
 for(const change of [
  {knownAt:'2026-10-13T09:36:01+09:00'},
  {observedAt:'2026-10-13T09:36:03+09:00',knownAt:'2026-10-13T09:36:03+09:00'},
  {sourceAsOf:'2026-10-13T09:36:20+09:00'},
  {barClosedAt:'2026-10-13T09:36:10+09:00'},
  {observedAt:'2026-10-13T09:34:00+09:00'},
 ]){
  const x=frame({records:[{...row(),...change}]});
  assert.throws(()=>inspect(x),/CAUSAL_/);
 }
});
test('an unfinished research 5-minute bar cannot be read as known before its close',()=>{
 const x=frame({records:[{...row(),sourceType:'YAHOO_CLOSED_5M_RESEARCH_OBSERVATION',
   observedAt:'2026-10-13T09:34:59+09:00',knownAt:'2026-10-13T09:34:59+09:00'}]});
 assert.throws(()=>inspect(x),/CAUSAL_UNCLOSED_BAR_OR_LOOKAHEAD/);
});
test('no future teacher, PnL, label or self-issued live attestation is admitted',()=>{
 for(const key of ['futureReturnPct','actualReturnPct','label','teacher','tradeWin','outcome']){
  const v={...row(),[key]:0};
  assert.throws(()=>inspect(frame({records:[v]})),/CAUSAL_FUTURE_OUTCOME_CONTAMINATION/);
 }
 for(const key of ['nativeFrozenValue','marketFeedArrivalCertified','authorizesTrade']){
  assert.throws(()=>inspect(frame({records:[{...row(),[key]:true}]})),/CAUSAL_FALSE_LIVE_ATTESTATION/);
 }
});
test('duplicate row and fabricated market source are blocked, without scoring',()=>{
 const a=row();
 assert.throws(()=>inspect(frame({records:[a,{...a}]})),/CAUSAL_RECORD_ID_MISSING_OR_DUPLICATE/);
 assert.throws(()=>inspect(frame({records:[{...a,sourceType:'FABRICATED_LIVE'}]})),/CAUSAL_SOURCE_NOT_APPROVED/);
 assert.throws(()=>inspect(frame({records:[{...a,evidenceMode:'SYNTHETIC'}]})),/CAUSAL_SOURCE_NOT_PROSPECTIVE_OBSERVED/);
});
test('a session does not contain future timestamps or naive timezone-less clocks',()=>{
 assert.throws(()=>inspect(frame({session:'2026-10-14'})),/CAUSAL_JPX_SESSION_MISMATCH/);
 assert.throws(()=>inspect(frame({decisionAt:'2026-10-13T09:36:15+09:00'})),/CAUSAL_DECISION_NOT_YET_POSSIBLE/);
 assert.throws(()=>inspect(frame({records:[{...row(),knownAt:'2026-10-13T09:35:01'}]})),/CAUSAL_KNOWN_CLOCK_INVALID/);
});
test('one low-latency linear pass, no retransmission or model inference',()=>{
 const rows=Array.from({length:250},(_,i)=>({...row(),recordId:'record-'+i}));
 const result=inspect(frame({records:rows}));
 assert.equal(result.recordCount,250);
 assert.equal(result.nativeDecisionPublished,false);
 assert.equal(result.productionReady,false);
});
