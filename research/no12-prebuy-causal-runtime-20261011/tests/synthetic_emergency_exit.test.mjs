import test from 'node:test';
import assert from 'node:assert/strict';
import {proposeNo12SyntheticEmergencyExits as decide} from '../runtime/synthetic_emergency_exit.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
function inp(){
 const frame={schemaId:CAUSAL_FRAME_SCHEMA,session:'2026-10-13',
  decisionAt:'2026-10-13T10:00:00+09:00',records:[{
   recordId:'state-1000',sourceType:'ORIGINAL_NATIVE_FEATURE_OBSERVATION',
   evidenceMode:'OBSERVED_READ_ONLY',sourceAsOf:'2026-10-13T09:59:00+09:00',
   observedAt:'2026-10-13T10:00:00+09:00',knownAt:'2026-10-13T10:00:00+09:00'
  }]};
 return {mode:'SYNTHETIC_OFFLINE_ONLY',observationFrame:frame,
  managedPositions:[{symbol:'7203.T',entryId:'e1',quantity:100,
   syntheticArkOwned:true,confirmedSyntheticBuyFillKnownAt:'2026-10-13T09:37:00+09:00'}],
  checkpoints:[{symbol:'7203',stateRecordId:'state-1000',stateUsable:true,
   formalState9Primary:'SHARP_DROP',intentAlreadyIssued:false,controlIntentKnownAt:null}],
  now:new Date('2026-10-13T10:00:04+09:00')};
}
test('first available SHARP_DROP emits one SELL intent but neither fill nor buy halt',()=>{
 const r=decide(inp());assert.equal(r.exits.length,1);
 assert.equal(r.exits[0].kind,'SELL_INTENT');
 assert.equal(r.exits[0].quantity,100);
 assert.equal(r.brokerFillCertified,false);
 assert.equal(r.orderTransmission,false);
});
test('structural or control SELL intention wins first or same checkpoint',()=>{
 for(const t of ['2026-10-13T09:59:59+09:00','2026-10-13T10:00:00+09:00']){
  const x=inp();x.checkpoints[0].controlIntentKnownAt=t;
  const r=decide(x);assert.equal(r.exits.length,0);
  assert.equal(r.pending[0].reason,'ORIGINAL_CONTROL_EXIT_PRIORITY');
 }
});
test('DROP_STOP and PULLBACK are not a SHARP_DROP emergency EXIT',()=>{
 for(const state of ['DROP','DROP_STOP','PULLBACK','RISE','RANGE']){
  const x=inp();x.checkpoints[0].formalState9Primary=state;
  assert.equal(decide(x).exits.length,0);
 }
});
test('missing State and unknown semantic remain blocked rather than fabricated SHARP_DROP',()=>{
 const x=inp();x.checkpoints[0].stateUsable=false;
 assert.equal(decide(x).blocked[0].reason,'STATE9_EVIDENCE_GAP_NOT_IMPUTED');
 const y=inp();y.checkpoints[0].formalState9Primary='UNKNOWN';
 assert.equal(decide(y).exits.length,0);
});
test('personal not-A rk-owned and future or prefill states rejected',()=>{
 const x=inp();x.managedPositions[0].syntheticArkOwned=false;
 assert.throws(()=>decide(x),/NO12_EXIT_POSITION_UNPROVEN/);
 const y=inp();y.managedPositions[0].confirmedSyntheticBuyFillKnownAt='2026-10-13T10:00:01+09:00';
 assert.throws(()=>decide(y),/NO12_EXIT_FILL_AFTER_DECISION/);
 const z=inp();z.observationFrame.records[0].knownAt='2026-10-13T10:00:01+09:00';
 assert.throws(()=>decide(z),/CAUSAL_/);
});
test('duplicate exit intent is not retransmitted, and LIVE mode is forbidden',()=>{
 const x=inp();x.checkpoints[0].intentAlreadyIssued=true;
 assert.equal(decide(x).exits.length,0);
 const y=inp();y.mode='LIVE_ATTESTED';
 assert.throws(()=>decide(y),/NO12_REAL_EXIT_NOT_CERTIFIED/);
});
