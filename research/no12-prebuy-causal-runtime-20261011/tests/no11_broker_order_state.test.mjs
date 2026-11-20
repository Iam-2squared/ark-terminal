import test from 'node:test';
import assert from 'node:assert/strict';
import {cashSide,observedCashOrder,bindObservedOrder} from '../tools/no11_broker_order_state.mjs';
import {observe,ENVELOPE} from '../tools/no11_account_observation.mjs';
import {LOCKED_FLAGS} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
const day='2026-10-26',at=s=>`${day}T09:30:${String(s).padStart(2,'0')}+09:00`;
const row=(filled=0,status='執行中')=>({orderNumber:'123',symbol:'7203',account:'特定',side:'買付',trade:'現物',quantity:200,filledQty:filled,status});
const args=()=>({sessionDate:day,throughJst:at(20),previousFilled:0,
 origin:{schemaId:'ARK_NO11_RECORDED_ORDER_ORIGIN_V1',evidenceMode:'RECORDED_NOT_AUTHORIZATION',sessionDate:day,intentId:'c'.repeat(64),rssOrderId:777,
 recordedAtJst:at(5),symbol:'7203.T',side:'BUY',account:'特定',quantity:200,productionReady:false,orderTransmission:false},
 idRows:[{rssOrderId:777,functionName:'RssStockOrder',orderDate:day,orderTime:'09:30:06',orderNumber:'123',result:'受注完了'}],orders:[row()]});
function envelope(){
 const rss={capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'};
 return {schemaId:ENVELOPE,runId:'a'.repeat(32),sequence:1,status:'OBSERVED',readOnly:true,productionReady:false,orderTransmission:false,
 snapshot:{schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',capturedAt:at(8),captureCompletedAt:at(10),rssStatus:rss,
 safety:{...LOCKED_FLAGS},positions:[],orders:[],executions:[],buyingPower:1000000},
 health:{schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,
 actualFeedTimestampCertified:false,healthCapturedAt:at(10),feeds:Object.fromEntries(Object.entries(rss).map(([k,state])=>[k,{state,observedAt:at(10)}]))}};
}
test('official cash sides are accepted while credit sides are not',()=>{
 assert.equal(cashSide('買付'),'BUY');assert.equal(cashSide('売付'),'SELL');
 for(const bad of ['買建','買埋','売建','売埋','BUY',null])assert.throws(()=>cashSide(bad));
});
test('official order and execution sides pass the existing account observer',()=>{
 const e=envelope();e.snapshot.orders=[row(100,'出来有')];
 e.snapshot.executions=[{symbol:'7203',account:'特定',side:'買付',quantity:100,price:1000}];
 const r=observe({envelope:e,sessionDate:day,throughJst:at(12)});
 assert.equal(r.state.orders['123'].side,'BUY');assert.equal(r.state.orders['123'].phase,'PARTIAL');
 assert.equal(r.report.newShadowEntriesAllowed,false);assert.equal(r.report.realFillsAppliedToShadow,false);
});
test('cancel-pending does not acknowledge cancellation or erase partial fills',()=>{
 for(const [filled,status] of [[0,'取消中（出来無）'],[100,'取消中（出来有）']]){
 const r=observedCashOrder(row(filled,status));assert.equal(r.terminal,false);assert.equal(r.phase,'CANCEL_PENDING');assert.equal(r.filledQty,filled);}
});
test('terminal partial cancellation preserves the actually observed executed quantity',()=>{
 const r=observedCashOrder(row(100,'取消済（出来有）'));
 assert.equal(r.phase,'CANCELLED');assert.equal(r.terminal,true);assert.equal(r.filledQty,100);
 const expired=observedCashOrder(row(100,'出来ず（出来有）'));assert.equal(expired.phase,'EXPIRED');
});
test('status and filled quantity contradictions fail rather than release funds',()=>{
 for(const [qty,status] of [[100,'取消済（出来無）'],[0,'取消済（出来有）'],[200,'出来ず（出来有）'],[100,'取消中（出来無）'],[0,'出来有'],[100,'約定']]){
 assert.throws(()=>observedCashOrder(row(qty,status)));}
});
test('unknown vendor status stays unresolved rather than treated as rejected',()=>{
 const r=observedCashOrder(row(0,'新しい未確認状態'));
 assert.equal(r.phase,'UNKNOWN');assert.equal(r.terminal,false);
});
test('recorded RSS ID plus exact broker order identity provides quantity-only linkage',()=>{
 const a=args();a.orders=[row(100,'出来有')];const r=bindObservedOrder(a);
 assert.equal(r.brokerOrderNumber,'123');assert.equal(r.observedFilledDelta,100);
 assert.equal(r.executionPriceAttributed,false);assert.equal(r.executionTimeCertified,false);
 assert.equal(r.orderCanBeResent,false);assert.equal(r.orderTransmission,false);
});
test('same-symbol personal order cannot substitute for the recorded broker number',()=>{
 const a=args();a.orders=[{...row(),orderNumber:'456'}];assert.throws(()=>bindObservedOrder(a),/BROKER_ORDER_NOT_UNIQUE_OR_MISSING/);
});
test('wrong RSS ID, reused broker number, cancel function or wrong day cannot bind',()=>{
 for(const change of [{rssOrderId:778},{functionName:'RssCancelOrder'},{orderDate:'2026-10-23'}]){
 const a=args();Object.assign(a.idRows[0],change);assert.throws(()=>bindObservedOrder(a));}
 const a=args();a.idRows.push({...a.idRows[0],rssOrderId:778});assert.throws(()=>bindObservedOrder(a),/MULTIPLE_IDS/);
});
test('symbol side account and quantity must match the recorded order origin',()=>{
 for(const change of [{symbol:'6501.T'},{side:'SELL'},{account:'一般'},{quantity:100}]){
 const a=args();Object.assign(a.origin,change);assert.throws(()=>bindObservedOrder(a),/ORIGIN_ORDER_MISMATCH/);}
});
test('cumulative counter regression is rejected; partial SELL is not a full exit',()=>{
 const a=args();a.previousFilled=101;a.orders=[row(100,'出来有')];assert.throws(()=>bindObservedOrder(a),/CUMULATIVE_FILL_REVERSED/);
 a.previousFilled=0;a.origin.side='SELL';a.orders[0].side='売付';const r=bindObservedOrder(a);
 assert.equal(r.sellFillObserved,true);assert.equal(r.order.terminal,false);assert.equal(r.observedFilledDelta,100);
});
test('no actual transmission or future order can be authorized by a stored origin',()=>{
 const a=args();a.origin.orderTransmission=true;assert.throws(()=>bindObservedOrder(a),/ORDER_ORIGIN_REQUIRED/);
 const b=args();b.idRows[0].orderTime='09:30:21';assert.throws(()=>bindObservedOrder(b),/RSS_ID_ORDER_CLOCK/);
 const c=args();c.idRows[0].orderTime='09:29:59';assert.throws(()=>bindObservedOrder(c),/RSS_ID_ORDER_CLOCK/);
});
