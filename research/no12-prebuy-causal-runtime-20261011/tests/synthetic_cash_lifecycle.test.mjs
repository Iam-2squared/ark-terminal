import test from 'node:test';
import assert from 'node:assert/strict';
import {runNo12SyntheticSession as run} from '../runtime/synthetic_cash_lifecycle.mjs';
import {NO12_CANDIDATES_SCHEMA} from '../runtime/prebuy_candidates.mjs';
import {CAUSAL_FRAME_SCHEMA} from '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const session='2026-10-13',decisionAt='2026-10-13T09:36:00+09:00';
function input(){
 const known='2026-10-13T09:35:01+09:00';
 const rec=(id,type)=>({recordId:id,sourceType:type,evidenceMode:'OBSERVED_READ_ONLY',
   sourceAsOf:'2026-10-13T09:35:00+09:00',observedAt:known,knownAt:known});
 const observationFrame={schemaId:CAUSAL_FRAME_SCHEMA,session,decisionAt,records:[
   rec('selector','TRADINGVIEW_SCANNER_OBSERVATION'),
   rec('state','ORIGINAL_NATIVE_FEATURE_OBSERVATION'),
   rec('market','MARKETSPEED_II_RSS_MARKET_OBSERVATION')
 ]};
 const candidate=(entryId,symbol)=>({entryId,symbol,selectorRecordId:'selector',
   stateRecordId:'state',marketRecordId:'market',candidateKnownAt:known,
   firstEntryScore:.7,firstEntryThreshold:.5,referencePrice:1000,
   quantity:100,formalState9Primary:'RISE'});
 const batch={schemaId:NO12_CANDIDATES_SCHEMA,session,decisionAt,
   candidates:[candidate('e1','7203')]};
 const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:known,
   source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
   externalPositions:[{symbol:'408A.T',quantity:100}],arkManagedPositions:[]};
 const ownership={...core,baselineSha256:digest(core)};
 return {mode:'SYNTHETIC_OFFLINE_ONLY',candidateInput:{batch,observationFrame,ownership},
   startingCashYen:1000000,externalSymbols:['408A.T'],events:[],
   now:new Date('2026-10-13T12:00:00+09:00')};
}
const event=(kind,eventId,time,extra={})=>({kind,eventId,session,
  knownAt:'2026-10-13T'+time+'+09:00',...extra});
test('only an actual synthetic SELL FILL blocks subsequent BUY, with same-time ordering',()=>{
 const x=input();
 x.candidateInput.batch.candidates.push({...x.candidateInput.batch.candidates[0],
   entryId:'e2',symbol:'6758'});
 x.events=[
  event('ENTRY_SIGNAL','ent1','09:36:02',{entryId:'e1',orderId:'ordB'}),
  event('BUY_FILL','buy1','09:37:00',{orderId:'ordB',quantity:100,fillPriceTenth:10000}),
  event('SELL_INTENT','exit','10:00:00',{orderId:'ordS',symbol:'7203',quantity:100}),
  event('ENTRY_SIGNAL','ent2','10:02:00',{entryId:'e2',orderId:'ordC'}),
  event('SELL_FILL','sell1','10:02:00',{orderId:'ordS',quantity:100,
    fillPriceTenth:10200,syntheticMatchedOrder:true})
 ];
 const r=run(x);
 assert.equal(r.status,'SYNTHETIC_SCENARIO_EVALUATED');
 assert.equal(r.history.filter(z=>z.type==='SYNTHETIC_BUY_FILL').length,1);
 assert.equal(r.history.filter(z=>z.type==='SYNTHETIC_SELL_FILL').length,1);
 assert.equal(r.firstSyntheticSellFillObservedAt,'2026-10-13T10:02:00+09:00');
 assert.equal(r.subsequentBuyProhibited,true);
 assert(r.rejected.some(y=>y.reason==='AFTER_FIRST_SYNTHETIC_SELL_FILL_NO_BUY'));
 assert.equal(r.positions.length,0);
 assert.equal(r.pendingBuyCount,0);
 assert.equal(r.orderTransmission,false);
});
test('SELL_INTENT alone does not block a later BUY when under MAX3',()=>{
 const x=input();
 x.candidateInput.batch.candidates.push({...x.candidateInput.batch.candidates[0],
   entryId:'e2',symbol:'6758'});
 x.events=[
  event('ENTRY_SIGNAL','e01','09:36:01',{entryId:'e1',orderId:'buyA'}),
  event('BUY_FILL','e02','09:37:01',{orderId:'buyA',quantity:100,fillPriceTenth:10000}),
  event('SELL_INTENT','e03','09:38:00',{symbol:'7203',quantity:100,orderId:'sellA'}),
  event('ENTRY_SIGNAL','e04','09:39:00',{entryId:'e2',orderId:'buyB'})
 ];
 const r=run(x);
 assert.equal(r.pendingBuyCount,1);
 assert.equal(r.pendingSellCount,1);
 assert.equal(r.subsequentBuyProhibited,false);
 assert.equal(r.positions.length,1);
});
test('zero yen cash does not stop research but will not place even synthetic BUY intent',()=>{
 const x=input();x.startingCashYen=0;
 x.events=[event('ENTRY_SIGNAL','one','09:36:01',{entryId:'e1',orderId:'B'})];
 const r=run(x);assert.equal(r.status,'SYNTHETIC_SCENARIO_EVALUATED');
 assert.equal(r.endingCashYen,'0.00');assert.equal(r.pendingBuyCount,0);
 assert.equal(r.rejected[0].reason,'CASH_OR_100_LOT_INSUFFICIENT');
});
test('no slot released at SELL_INTENT, nor for unfilled pending BUY',()=>{
 const x=input();
 x.candidateInput.batch.candidates.push({...x.candidateInput.batch.candidates[0],entryId:'e2',symbol:'6758'});
 x.candidateInput.batch.candidates.push({...x.candidateInput.batch.candidates[0],entryId:'e3',symbol:'8306'});
 x.candidateInput.batch.candidates.push({...x.candidateInput.batch.candidates[0],entryId:'e4',symbol:'9984'});
 x.events=[
  event('ENTRY_SIGNAL','a','09:36:01',{entryId:'e1',orderId:'b1'}),
  event('ENTRY_SIGNAL','b','09:36:02',{entryId:'e2',orderId:'b2'}),
  event('ENTRY_SIGNAL','c','09:36:03',{entryId:'e3',orderId:'b3'}),
  event('ENTRY_SIGNAL','d','09:36:04',{entryId:'e4',orderId:'b4'})
 ];
 const r=run(x);
 assert.equal(r.pendingBuyCount,3);
 assert(r.rejected.some(y=>y.reason==='MAX3_SLOTS'));
 assert.equal(r.cashReservationYen!=='0.00',true);
});
test('partial BUY fill is reconciliation stop rather than fabricated full 100-share position',()=>{
 const x=input();x.events=[
  event('ENTRY_SIGNAL','a','09:36:01',{entryId:'e1',orderId:'b1'}),
  event('BUY_FILL','b','09:37:01',{orderId:'b1',quantity:30,fillPriceTenth:10000})
 ];
 const r=run(x);assert.equal(r.status,'BLOCKED_RECONCILIATION');
 assert.equal(r.positions.length,0);
 assert.equal(r.rejected.at(-1).reason,'PARTIAL_BUY_FILL_UNRECONCILED');
});
test('partial SELL fill triggers wait and does not free the whole slot',()=>{
 const x=input();x.events=[
  event('ENTRY_SIGNAL','a','09:36:01',{entryId:'e1',orderId:'b1'}),
  event('BUY_FILL','b','09:37:01',{orderId:'b1',quantity:100,fillPriceTenth:10000}),
  event('SELL_INTENT','c','09:40:00',{symbol:'7203',quantity:100,orderId:'s1'}),
  event('SELL_FILL','d','09:41:00',{orderId:'s1',quantity:30,fillPriceTenth:10000,syntheticMatchedOrder:true})
 ];
 const r=run(x);assert.equal(r.positions.length,1);
 assert.equal(r.positions[0].quantity,70);
 assert.equal(r.pendingSellCount,1);
 assert.equal(r.subsequentBuyProhibited,true);
});
test('duplicated event with changed details is a hard failure, exact duplicate is idempotent',()=>{
 const x=input();x.events=[
  event('ENTRY_SIGNAL','same','09:36:01',{entryId:'e1',orderId:'b1'}),
  event('ENTRY_SIGNAL','same','09:36:01',{entryId:'e1',orderId:'b1'})
 ];
 assert.equal(run(x).pendingBuyCount,1);
 x.events[1].orderId='different';
 assert.throws(()=>run(x),/NO12_DUPLICATE_EVENT_ID_CONFLICT/);
});
test('live mode never accepted as a shortcut to real orders',()=>{
 const x=input();x.mode='LIVE_ATTESTED';
 assert.throws(()=>run(x),/NO12_REAL_BROKER_MODE_DISABLED/);
});

test('15:20 cutoff applies at signal event time, even when its candidate was validated earlier',()=>{
 const x=input();x.now=new Date('2026-10-13T15:21:00+09:00');
 x.events=[event('ENTRY_SIGNAL','late','15:20:00',{entryId:'e1',orderId:'late-order'})];
 const r=run(x);
 assert.equal(r.pendingBuyCount,0);
 assert.equal(r.rejected[0].reason,'AFTER_1520_CUTOFF');
 assert.equal(r.orderTransmission,false);
});
test('synthetic cash uses deterministic two-sided 0.05% cost, with no fill on SELL_INTENT',()=>{
 const x=input();
 x.events=[
  event('ENTRY_SIGNAL','a','09:36:01',{entryId:'e1',orderId:'buy'}),
  event('BUY_FILL','b','09:37:01',{orderId:'buy',quantity:100,fillPriceTenth:10000}),
  event('SELL_INTENT','c','09:38:01',{symbol:'7203',quantity:100,orderId:'sell'}),
  event('SELL_FILL','d','09:39:01',{orderId:'sell',quantity:100,fillPriceTenth:10200,syntheticMatchedOrder:true})
 ];
 const full=run(x);
 assert.equal(full.startingCashYen,'1000000.00');
 assert.equal(full.endingCashYen,'1001899.00');
 assert.equal(full.cashReservationYen,'0.00');
 const beforeFill={...x,events:x.events.slice(0,3)};
 const pending=run(beforeFill);
 assert.equal(pending.pendingSellCount,1);
 assert.equal(pending.endingCashYen,'899950.00');
});
test('synthetic reference/reserve cannot be bypassed by a higher unexpected fill price',()=>{
 const x=input();x.events=[
  event('ENTRY_SIGNAL','a','09:36:01',{entryId:'e1',orderId:'buy'}),
  event('BUY_FILL','b','09:37:01',{orderId:'buy',quantity:100,fillPriceTenth:10001})
 ];
 const result=run(x);
 assert.equal(result.status,'BLOCKED_RECONCILIATION');
 assert.equal(result.positions.length,0);
 assert.equal(result.rejected.at(-1).reason,'BUY_FILL_PRICE_OR_CASH_EXCEEDS_RESERVATION');
});
