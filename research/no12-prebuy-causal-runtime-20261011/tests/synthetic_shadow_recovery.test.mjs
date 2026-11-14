import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {openNo12SyntheticScenario,replayNo12SyntheticScenario} from '../runtime/synthetic_shadow_recovery.mjs';
const session='2026-10-13',decisionAt='2026-10-13T09:36:00+09:00';
function scenario(){
 const t='2026-10-13T09:35:01+09:00';
 const rec=(id,sourceType)=>({
  recordId:id,sourceType,evidenceMode:'OBSERVED_READ_ONLY',
  sourceAsOf:'2026-10-13T09:35:00+09:00',observedAt:t,knownAt:t
 });
 const observationFrame={schemaId:CAUSAL_FRAME_SCHEMA,session,decisionAt,
  records:[rec('selector','TRADINGVIEW_SCANNER_OBSERVATION'),
   rec('state','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
   rec('market','MARKETSPEED_II_RSS_MARKET_OBSERVATION')]};
 const batch={schemaId:NO12_CANDIDATES_SCHEMA,session,decisionAt,
  candidates:[{entryId:'e1',symbol:'7203',selectorRecordId:'selector',
   stateRecordId:'state',marketRecordId:'market',candidateKnownAt:t,
   firstEntryScore:.7,firstEntryThreshold:.5,
   referencePrice:1000,quantity:100,formalState9Primary:'RISE'}]};
 const ownCore={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:t,
  source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
  externalPositions:[{symbol:'408A.T',quantity:100}],arkManagedPositions:[]};
 return {candidateInput:{batch,observationFrame,
  ownership:{...ownCore,baselineSha256:digest(ownCore)}},
  startingCashYen:1000000,externalSymbols:['408A.T'],
  now:new Date('2026-10-13T10:04:00+09:00')};
}
const ev=(kind,eventId,at,extra={})=>({kind,eventId,session,
 knownAt:'2026-10-13T'+at+'+09:00',...extra});
test('crash between synthetic intent and fill replays identical pending order once',()=>{
 const f=scenario(),root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-shadow-replay-'));
 try{
  let journal=openNo12SyntheticScenario({...f,privateRoot:root});
  journal.append(ev('ENTRY_SIGNAL','entry','09:36:01',{entryId:'e1',orderId:'fake-B'}));
  journal=openNo12SyntheticScenario({...f,privateRoot:root});
  assert.equal(journal.append(ev('ENTRY_SIGNAL','entry','09:36:01',{entryId:'e1',orderId:'fake-B'})).status,'IDEMPOTENT_REPLAY');
  let replay=replayNo12SyntheticScenario({...f,journal});
  assert.equal(replay.evaluated.pendingBuyCount,1);
  assert.equal(replay.evaluated.positions.length,0);
  assert.equal(replay.effectsSentToBroker,0);
  journal.append(ev('BUY_FILL','fill','09:37:01',{orderId:'fake-B',quantity:100,fillPriceTenth:10000}));
  replay=replayNo12SyntheticScenario({...f,journal});
  assert.equal(replay.evaluated.positions.length,1);
  assert.equal(replay.evaluated.pendingBuyCount,0);
  assert.equal(replay.journalEventCount,2);
  assert.equal(replay.orderTransmission,false);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('daily first SELL fill persists after process restart and blocks new BUY',()=>{
 const f=scenario(),root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-shadow-sell-'));
 try{
  const journal=openNo12SyntheticScenario({...f,privateRoot:root});
  journal.append(ev('ENTRY_SIGNAL','e1','09:36:01',{entryId:'e1',orderId:'buy'}));
  journal.append(ev('BUY_FILL','f1','09:37:01',{orderId:'buy',quantity:100,fillPriceTenth:10000}));
  journal.append(ev('SELL_INTENT','s1','10:00:00',{symbol:'7203',quantity:100,orderId:'sell'}));
  journal.append(ev('SELL_FILL','sf1','10:02:00',{orderId:'sell',
    quantity:100,fillPriceTenth:10200,syntheticMatchedOrder:true}));
  const second=openNo12SyntheticScenario({...f,privateRoot:root});
  const replay=replayNo12SyntheticScenario({...f,journal:second});
  assert.equal(replay.evaluated.subsequentBuyProhibited,true);
  assert.equal(replay.evaluated.positions.length,0);
  assert.equal(replay.journalEventCount,4);
  assert.equal(replay.effectsSentToBroker,0);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('scenario cash and candidate score cannot be changed across reboot',()=>{
 const f=scenario(),root=fs.mkdtempSync(path.join(os.tmpdir(),'no12-shadow-hash-'));
 try{
  const journal=openNo12SyntheticScenario({...f,privateRoot:root});
  assert.throws(()=>replayNo12SyntheticScenario({...f,journal,
    startingCashYen:2000000}),/NO12_SHADOW_SCENARIO_FINGERPRINT_CHANGED/);
  const changed=structuredClone(f.candidateInput);
  changed.batch.candidates[0].firstEntryScore=.9;
  assert.throws(()=>openNo12SyntheticScenario({
   ...f,privateRoot:root,candidateInput:changed}),/NO12_JOURNAL_CONTRACT_INVALID/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
