import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileNo12SyntheticRssOrigin as check} from '../runtime/synthetic_rss_order_origin.mjs';
function fixture(){
 const now=new Date('2026-10-13T10:05:02+09:00'),
  prev='2026-10-13T10:04:00+09:00',obs='2026-10-13T10:05:00+09:00';
 return {mode:'SYNTHETIC_OFFLINE_ONLY',session:'2026-10-13',observationAt:obs,now,
 arkIssued:[{rssOrderId:42,side:'SELL',symbol:'7203.T',quantity:100,
   verifiedSyntheticOrigination:true,lockedIntentSha256:'a'.repeat(64),
   issuedAt:'2026-10-13T10:02:00+09:00'}],
 rssOrderIds:[{rssOrderId:42,orderFunction:'RssStockOrder',
   orderNumber:'BROKER42',observedAt:obs}],
 rssOrders:[{orderNumber:'BROKER42',symbol:'7203',side:'売付',trade:'現物',
   quantity:100,filledQty:0,observedAt:obs}],
 previous:[{orderNumber:'BROKER42',filledQty:0,observedAt:prev}],
 externalSymbols:['408A.T']};
}
test('exact Ark RSS ID -> broker order number -> no cumulative fill does not halt BUY',()=>{
 const r=check(fixture());assert.equal(r.arkOriginOrders,1);
 assert.equal(r.conservativeHoldNewBuys,false);
 assert.equal(r.realOrderOriginCertified,false);
 assert.equal(r.orderTransmission,false);
});
test('positive partial SELL cumulative fill halts new BUY conservatively, not exact broker-time certified',()=>{
 const x=fixture();x.rssOrders[0].filledQty=30;const r=check(x);
 assert.equal(r.observedSellFilledQtyDelta,30);
 assert.equal(r.conservativeHoldNewBuys,true);
 assert.equal(r.brokerExactFillTime,null);
 assert.equal(r.cashReleaseCertified,false);
});
test('outside personal order of same symbol is never included as an Ark origin',()=>{
 const x=fixture();x.rssOrders.push({orderNumber:'PERSONAL',
   symbol:'7203',side:'売付',trade:'現物',quantity:100,filledQty:100,
   observedAt:x.observationAt});
 const r=check(x);assert.equal(r.otherOrders,1);
 assert.equal(r.observedSellFilledQtyDelta,0);
});
test('different Ark RSS ID or broker order identity prevents a fictitious fill',()=>{
 const x=fixture();x.arkIssued[0].rssOrderId=43;
 assert.throws(()=>check(x),/ARK_RSS_ID_NOT_PRESENT/);
 const y=fixture();y.rssOrders[0].side='買付';
 assert.throws(()=>check(y),/ARK_ORDER_IDENTITY_MISMATCH/);
});
test('counter regression, missing previous and ambiguous ID-order relationship fail',()=>{
 const x=fixture();x.previous[0].filledQty=100;x.rssOrders[0].filledQty=25;
 assert.throws(()=>check(x),/ARK_ORDER_FILLED_COUNTER_REGRESSED/);
 const y=fixture();y.previous=[];
 assert.throws(()=>check(y),/ARK_ORDER_CUMULATIVE_BASELINE_MISSING/);
 const z=fixture();z.rssOrderIds.push({...z.rssOrderIds[0],rssOrderId:99});
 assert.throws(()=>check(z),/RSS_ORDER_NUMBER_COLLISION/);
});
test('credit a SELL intent from external stock is forbidden even if a brokerage ID exists',()=>{
 const x=fixture();x.arkIssued[0].symbol='408A';
 assert.throws(()=>check(x),/PERSONAL_SYMBOL_CANNOT_BE_ARK_ORDER/);
});
test('real feed mode is explicitly uncertified; this code cannot issue orders',()=>{
 const x=fixture();x.mode='LIVE_ATTESTED';
 assert.throws(()=>check(x),/NO12_REAL_ORDER_ORIGIN_NOT_CERTIFIED/);
});
