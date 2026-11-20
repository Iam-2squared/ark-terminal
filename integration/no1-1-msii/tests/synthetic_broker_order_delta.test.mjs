import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileNo11SyntheticBrokerOrderDelta as check} from '../runtime/synthetic_broker_order_delta.mjs';
function base(){
 const now=new Date('2026-10-13T10:04:00+09:00');
 return {mode:'SYNTHETIC_OFFLINE_ONLY',session:'2026-10-13',
  observedAt:'2026-10-13T10:03:55+09:00',now,
  arkOrders:[{orderNumber:'ARK-ID-01',symbol:'7203.T',side:'SELL',
   quantity:100,verifiedOrigination:true,arkOwnedAtSubmission:true,
   lockedIntentSha256:'a'.repeat(64),submittedAt:'2026-10-13T10:01:00+09:00'}],
  brokerRows:[{orderNumber:'ARK-ID-01',symbol:'7203',quantity:100,filledQty:0}],
  previous:[{orderNumber:'ARK-ID-01',filledQty:0,observedAt:'2026-10-13T10:02:00+09:00'}]};
}
test('synthetic SELL intent with zero actual cumulative fills does not trigger same-day buy halt',()=>{
 const v=check(base());
 assert.equal(v.totalSellFillQuantityIncrease,0);
 assert.equal(v.buyHaltOnObservedSellDelta,false);
 assert.equal(v.brokerExecutionIdentityCertified,false);
 assert.equal(v.productionReady,false);
});
test('first SELL order filled quantity increment triggers conservative buy hold, but not fill-time certificate',()=>{
 const x=base();x.brokerRows[0].filledQty=100;
 const v=check(x);
 assert.equal(v.totalSellFillQuantityIncrease,100);
 assert.equal(v.buyHaltOnObservedSellDelta,true);
 assert.equal(v.exactFillOccurredAt,null);
 assert.equal(v.legalSellFillLatchingCertified,false);
 assert.equal(v.cashAndSlotReleaseCertified,false);
});
test('idempotent reobserved filled quantity never creates another fill delta',()=>{
 const x=base();x.brokerRows[0].filledQty=100;x.previous[0].filledQty=100;
 assert.equal(check(x).totalSellFillQuantityIncrease,0);
 assert.equal(check(x).buyHaltOnObservedSellDelta,false);
});
test('personal order on same symbol is NOT an Ark order merely by matching symbol',()=>{
 const x=base();
 x.brokerRows.push({orderNumber:'PERSONAL',symbol:'7203',quantity:100,filledQty:100});
 const v=check(x);
 assert.equal(v.totalSellFillQuantityIncrease,0);
 assert.equal(v.otherOrders,1);
 assert.equal(v.status,'UNKNOWN_EXTERNAL_ORDERS_PRESENT');
});
test('broker quantity regression, mismatched symbol and duplicate ID fail closed',()=>{
 let x=base();x.previous[0].filledQty=100;x.brokerRows[0].filledQty=50;
 assert.throws(()=>check(x),/BROKER_FILLED_QTY_REGRESSION/);
 x=base();x.brokerRows[0].symbol='6758';
 assert.throws(()=>check(x),/BROKER_ORDER_NOT_SAME_ARK_ORIGIN/);
 x=base();x.brokerRows.push({...x.brokerRows[0]});
 assert.throws(()=>check(x),/BROKER_ORDER_DUPLICATE_ID/);
});
test('missing previous or missing broker order cannot invent a zero baseline',()=>{
 let x=base();x.previous=[];
 assert.throws(()=>check(x),/PREVIOUS_CUMULATIVE_OBSERVATION_REQUIRED/);
 x=base();x.brokerRows=[];
 assert.throws(()=>check(x),/ARK_ORDER_MISSING_FROM_BROKER_FEED/);
});
test('external-personal SELL spoofing and unverified native origination never admitted',()=>{
 const x=base();x.arkOrders[0].arkOwnedAtSubmission=false;
 assert.throws(()=>check(x),/PERSONAL_OR_UNVERIFIED_SELL/);
 const y=base();y.arkOrders[0].verifiedOrigination=false;
 assert.throws(()=>check(y),/ARK_ORDER_ORIGINATION_NOT_VERIFIED/);
});
test('real mode is rejected regardless of counters until physical broker linkage is certified',()=>{
 const x=base();x.mode='LIVE_ATTESTED';
 assert.throws(()=>check(x),/REAL_ORDER_LINK_IDENTITY_NOT_CERTIFIED/);
});
