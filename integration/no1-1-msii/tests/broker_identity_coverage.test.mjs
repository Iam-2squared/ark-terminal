import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectNo11BrokerRssIdentityCoverage as check} from '../runtime/broker_identity_coverage.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';
function input(){
 const t='2026-10-13T09:40:00+09:00';
 const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,capturedAt:t,
  source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
  externalPositions:[{symbol:'408A.T',quantity:100}],
  arkManagedPositions:[{symbol:'7203.T',quantity:100}]};
 const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',
  capturedAt:t,captureCompletedAt:t,positions:[{symbol:'408A',quantity:100},{symbol:'7203',quantity:100}],
  buyingPower:0,orders:[],executions:[],safety:{...LOCKED_FLAGS}};
 const feeds=Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'})
  .map(([k,state])=>[k,{state,observedAt:t}]));
 const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,
  addinLoaded:true,workbookPersisted:true,rssErrors:0,healthCapturedAt:t,feeds};
 return {snapshot,health,ownership:{...core,baselineSha256:digest(core)},
  now:new Date('2026-10-13T09:40:10+09:00')};
}
const exec=(symbol,side)=>({executionDate:'2026/10/13 09:39:20',symbol,side,
 account:'特定',quantity:100,price:2400});
test('empty RSS broker rows verify read-only source, not certify a future trading pipeline',()=>{
 const v=check(input());
 assert.equal(v.status,'ZERO_BROKER_ORDER_EXECUTION_ROWS');
 assert.equal(v.productionReady,false);
 assert.equal(v.firstSellFillLatchedFromRss,false);
 assert.equal(v.rowCounts.orders,0);
});
test('a personal SELL on the broker RSS feed must never be treated as an Ark SELL fill',()=>{
 const x=input();x.snapshot.executions.push(exec('408A','売付'));
 const v=check(x);
 assert.equal(v.status,'BROKER_IDENTITY_UNCERTIFIED');
 assert.equal(v.personalSellRows,1);
 assert.equal(v.arkSellFillIdentityCertified,false);
 assert.equal(v.firstSellFillLatchedFromRss,false);
 assert(v.blockers.includes('PERSONAL_SELL_ROW_MUST_NEVER_TRIGGER_ARK_LATCH'));
});
test('even a symbol owned by Ark is insufficient without unique broker execution and order identity',()=>{
 const x=input();x.snapshot.executions.push(exec('7203','売付'));
 const v=check(x);
 assert.equal(v.unlinkedSellRows,1);
 assert.equal(v.personalSellRows,0);
 assert(v.blockers.includes('RSS_EXECUTION_ROWS_HAVE_NO_ORDER_OR_EXECUTION_ID'));
 assert.equal(v.firstSellFillLatchedFromRss,false);
});
test('populated order row without side/time proof cannot reserve or release safely',()=>{
 const x=input();x.snapshot.orders.push({orderNumber:'test-order',status:'出来有',symbol:'7203',quantity:100,filledQty:30});
 const v=check(x);
 assert.equal(v.status,'BROKER_IDENTITY_UNCERTIFIED');
 assert(v.blockers.includes('BROKER_ORDER_SIDE_AND_RECEIPT_NOT_CAPTURED'));
 assert.equal(v.liveOrderReconciliationCertified,false);
});
test('duplicated order identity and nonsensical fill quantity block rather than silently dropping rows',()=>{
 const x=input();x.snapshot.orders.push({orderNumber:'A',status:'執行中',symbol:'7203',quantity:100,filledQty:25});
 x.snapshot.orders.push({...x.snapshot.orders[0]});
 assert.throws(()=>check(x),/BROKER_ORDER_ID_MISSING_OR_DUPLICATE/);
 const y=input();y.snapshot.orders.push({orderNumber:'A',status:'執行中',symbol:'7203',quantity:100,filledQty:101});
 assert.throws(()=>check(y),/BROKER_ORDER_FILLED_QTY_INVALID/);
});
test('execution invalid time, market side, symbols and negative quantity fail closed',()=>{
 for(const row of [
  {...exec('7203','売付'),executionDate:'2026/10/13 99:39:20'},
  {...exec('7203','売埋')},{...exec('ABC','売付')},
  {...exec('7203','売付'),quantity:-1}
 ]){
  const x=input();x.snapshot.executions.push(row);
  assert.throws(()=>check(x));
 }
});
test('stale source and tampered ownership baseline never certify reconciliation',()=>{
 const x=input();x.now=new Date('2026-10-13T09:41:00+09:00');
 assert.throws(()=>check(x),/BROKER_SOURCE_READONLY_GATE_BLOCKED/);
 const y=input();y.ownership.baselineSha256='0'.repeat(64);
 assert.throws(()=>check(y),/OWNERSHIP_CHECKSUM_MISMATCH/);
});
