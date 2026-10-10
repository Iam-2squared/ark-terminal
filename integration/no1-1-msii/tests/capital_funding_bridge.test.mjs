import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectNo11CapitalFunding,CAPITAL_CASH_POLICY} from '../runtime/capital_funding_bridge.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';

function fixture() {
  const now=new Date().toISOString();
  const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',capturedAt:now,captureCompletedAt:now,
    positions:[{symbol:'408A',quantity:180,marketValue:300000}],
    orders:[],executions:[],buyingPower:700000,safety:{...LOCKED_FLAGS}};
  const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',
    source:'MARKETSPEED_II_RSS',readOnly:true,addinLoaded:true,workbookPersisted:true,
    rssErrors:0,healthCapturedAt:now,actualFeedTimestampCertified:false,
    feeds:Object.fromEntries(Object.entries({capacity:'完了',
      orders:'配信中',executions:'配信中',positions:'配信中'})
      .map(([key,state])=>[key,{state,observedAt:now}]))};
  const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',
    source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',capturedAt:now,
    frozen:true,externalPositions:[{symbol:'408A.T',quantity:180}],
    arkManagedPositions:[]};
  const ownership={...core,baselineSha256:digest(core)};
  return {snapshot,health,ownership,now:new Date(now)};
}
function confirm(input) {
  const {baselineSha256,...core}=input.ownership;
  input.ownership.baselineSha256=digest(core);
  return input;
}
const preview=input=>inspectNo11CapitalFunding(input);
test('full brokerage cash buying power is the Ark shadow ceiling, not total-account equity',()=>{
  const v=preview(fixture());
  assert.equal(v.status,'READ_ONLY_CAPITAL_PREVIEW');
  assert.deepEqual(v.arkCapitalInputs,{cash:700000,equity:700000,exposure:0});
  assert.equal(v.policyId,CAPITAL_CASH_POLICY);
  assert.equal(v.externalHoldingsIncludedInEquity,false);
  assert.equal(v.extraDeductionForPersonalStock,false);
  assert.equal(v.productionReady,false);
  assert.equal(v.allocationInputsForTradingCertified,false);
});
test('Ark-only MTM increases Ark equity; personal holding value never does',()=>{
  const f=fixture();
  f.snapshot.positions.push({symbol:'7203',quantity:100,marketValue:150000});
  f.ownership.arkManagedPositions.push({symbol:'7203.T',quantity:100});
  confirm(f);
  const v=preview(f);
  assert.equal(v.status,'READ_ONLY_CAPITAL_PREVIEW');
  assert.deepEqual(v.arkCapitalInputs,{cash:700000,equity:850000,exposure:150000});
  assert.equal(v.arkManagedPositionCount,1);
});
test('personal stock price change does not affect Capital input',()=>{
  const f=fixture(); f.snapshot.positions[0].marketValue=900000;
  assert.deepEqual(preview(f).arkCapitalInputs,{cash:700000,equity:700000,exposure:0});
});
test('unclassified or tampered ownership fails closed',()=>{
  const f=fixture();
  f.ownership.arkManagedPositions.push({symbol:'7203.T',quantity:100});
  assert.equal(preview(f).status,'BLOCKED');
  const g=fixture();g.ownership.externalPositions=[];
  confirm(g);
  assert.equal(preview(g).status,'BLOCKED');
});
test('personal and Ark ownership may not mix the same symbol',()=>{
  const f=fixture();
  f.ownership.arkManagedPositions.push({symbol:'408A.T',quantity:100});
  confirm(f);
  assert(preview(f).blockers.includes('PERSONAL_AND_ARK_SYMBOL_OVERLAP'));
});
test('pending or unverified orders block use of apparent free cash',()=>{
  const f=fixture();f.snapshot.orders=[{orderNumber:'order-1'}];
  assert(preview(f).blockers.includes('BROKER_ORDERS_UNVERIFIED_BLOCK_NEW_BUY'));
});
test('missing Ark MTM cannot be guessed from personal or brokerage total equity',()=>{
  const f=fixture();
  f.snapshot.positions.push({symbol:'7203',quantity:100,marketValue:null});
  f.ownership.arkManagedPositions.push({symbol:'7203.T',quantity:100});
  confirm(f);
  const v=preview(f);
  assert(v.blockers.includes('ARK_MARKET_VALUE_UNAVAILABLE'));
  assert.equal(v.arkCapitalInputs,null);
});
test('missing broker position / zero, negative or invalid buying power fails closed',()=>{
  for(const bad of [-1,NaN,null,undefined,Infinity]){
    const f=fixture();f.snapshot.buyingPower=bad;
    assert.equal(preview(f).status,'BLOCKED');
  }
  const g=fixture();g.snapshot.positions=[];
  assert.equal(preview(g).status,'BLOCKED');
});
test('a stale RSS snapshot must not be reused for Capital',()=>{
  const f=fixture();
  f.now=new Date(Date.now()+120000);
  const v=preview(f);
  assert.equal(v.status,'BLOCKED');
  assert.equal(v.arkCapitalInputs,null);
});
test('read-only preview never becomes trade-ready from status cells',()=>{
  const f=fixture();
  f.health.actualFeedTimestampCertified=true;
  const v=preview(f);
  assert.equal(v.status,'READ_ONLY_CAPITAL_PREVIEW');
  assert.equal(v.actualFeedTimestampCertified,false);
  assert.equal(v.executionAllowed,false);
  assert.equal(v.rssOrderFunctionAllowed,false);
  assert.equal(v.transmitted,false);
});
