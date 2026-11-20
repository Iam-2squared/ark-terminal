import test from 'node:test';
import assert from 'node:assert/strict';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {buildNo12SyntheticMsiiOrderText as build,NO12_ORDER_INTENT_SCHEMA} from '../runtime/synthetic_msii_draft.mjs';
const observed='2026-10-13T09:35:10+09:00';
function fixture(side='BUY'){
 const core={schemaId:NO12_ORDER_INTENT_SCHEMA,evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  symbol:'7203.T',side,positionEffect:side==='BUY'?'OPEN':'CLOSE',
  quantity:100,cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
  syntheticCashAndSlotReserved:side==='BUY',syntheticArkOwnedPosition:side==='SELL',
  timeInForce:'DAY',sor:false,orderType:'MARKET',limitPrice:null,
  accountType:0,accountTypeVerified:true,transmitted:false,productionReady:false};
 const intent={...core,intentSha256:digest(core)};
 const orderIdentity={schemaId:'ARK_NO12_SYNTHETIC_ORDER_ID_OBSERVATION_V1',
  evidenceMode:'SYNTHETIC_OFFLINE_ONLY',observedAt:observed,reservedOrderId:81,
  usedOrderIds:[1,2,80],sourceIntentSha256:intent.intentSha256,
  syntheticUniquenessChecked:true};
 return {intent,orderIdentity,now:new Date('2026-10-13T09:35:11+09:00')};
}
function recalc(x){
 const {intentSha256,...core}=x.intent;
 x.intent.intentSha256=digest(core);
 x.orderIdentity.sourceIntentSha256=x.intent.intentSha256;
}
test('source-shaped 20 argument BUY TEXT with trigger=0 is never a live Excel formula',()=>{
 const t=build(fixture());
 assert.equal(t.arguments.length,20);
 assert.deepEqual(t.arguments.slice(0,9),['81','0','7203.T','3','0','0','100','0','']);
 assert.equal(t.arguments[9],'1');
 assert.equal(t.arguments[11],'0');
 assert.equal(t.trigger,0);
 assert.equal(t.formulaCellType,'TEXT');
 assert.equal(t.formulaEvaluationAllowed,false);
 assert.equal(t.brokerOrderActuallySubmitted,false);
 assert.equal(t.orderTransmission,false);
 assert.equal(t.productionReady,false);
 assert.match(t.formulaText,/^=RssStockOrder\(81,0,"7203.T",3,/);
});
test('SELL draft uses cash-only side 1 but only for a simulated Ark-managed holding',()=>{
 const r=build(fixture('SELL'));
 assert.equal(r.arguments[3],'1');assert.equal(r.arguments[6],'100');
 const x=fixture('SELL');x.intent.syntheticArkOwnedPosition=false;recalc(x);
 assert.throws(()=>build(x),/NO12_EXTERNAL_SELL_REJECTED/);
});
test('Market vs Limit, account class and DAY/SOR are all explicit rather than defaulted',()=>{
 const x=fixture();x.intent.orderType='LIMIT';x.intent.limitPrice=1042.5;
 x.intent.sor=true;x.intent.accountType=1;recalc(x);
 const p=build(x);
 assert.equal(p.arguments[5],'1');assert.equal(p.arguments[7],'1');
 assert.equal(p.arguments[8],'1042.5');assert.equal(p.arguments[11],'1');
 assert.equal(p.arguments[9],'1');
});
test('fake LIVE mode, transmitted input and positive Excel trigger can never pass',()=>{
 for(const change of [
  {evidenceMode:'LIVE_ATTESTED'},{transmitted:true},{productionReady:true},
  {executionAllowed:true}
 ]){
  const x=fixture();Object.assign(x.intent,change);recalc(x);
  assert.throws(()=>build(x),/NO12_LIVE_OR_UNVERIFIED_INTENT_REJECTED/);
 }
});
test('no real BUY draft without synthetic cash/slot reservation or 100-share lot',()=>{
 const x=fixture();x.intent.syntheticCashAndSlotReserved=false;recalc(x);
 assert.throws(()=>build(x),/NO12_BUY_NEEDS_SYNTHETIC_CASH_AND_SLOT_RESERVATION/);
 for(const qty of [0,1,50,150,-100]){
  const y=fixture();y.intent.quantity=qty;recalc(y);
  assert.throws(()=>build(y),/NO12_100_SHARE_LOT_REQUIRED/);
 }
});
test('no phantom broker order ID from stale observation, duplicate or mismatched origin',()=>{
 const x=fixture();x.orderIdentity.usedOrderIds.push(81);
 assert.throws(()=>build(x),/NO12_RSS_ORDER_ID_ALREADY_USED/);
 const y=fixture();y.now=new Date('2026-10-13T09:36:00+09:00');
 assert.throws(()=>build(y),/NO12_ORDER_ID_SNAPSHOT_STALE/);
 const z=fixture();z.orderIdentity.sourceIntentSha256='0'.repeat(64);
 assert.throws(()=>build(z),/NO12_ORDER_ID_TO_INTENT_NOT_MATCHED/);
});
test('changed side, symbol, TIF, account type and malformed hash fail closed',()=>{
 const x=fixture();x.intent.symbol='7203';recalc(x);
 assert.throws(()=>build(x),/NO12_BROKER_SYMBOL_NOT_VERIFIED/);
 const y=fixture();y.intent.timeInForce='GTC';recalc(y);
 assert.throws(()=>build(y),/NO12_MSII_ORDER_POLICY_MISSING/);
 const z=fixture();z.intent.quantity=200;
 assert.throws(()=>build(z),/NO12_INTENT_CHECKSUM_INVALID/);
 const w=fixture();w.intent.accountTypeVerified=false;recalc(w);
 assert.throws(()=>build(w),/NO12_BROKER_ACCOUNT_TYPE_NOT_VERIFIED/);
});
