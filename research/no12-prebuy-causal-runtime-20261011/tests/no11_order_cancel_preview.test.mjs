import test from 'node:test';
import assert from 'node:assert/strict';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {buildNo12SyntheticMsiiOrderText as buildOrder,NO12_ORDER_INTENT_SCHEMA} from '../runtime/synthetic_msii_draft.mjs';
import {buildSyntheticCancelText as cancel} from '../tools/no11_order_cancel_preview.mjs';
const day='2026-10-26',created=day+'T09:30:05+09:00';
function fixture(){
 const core={schemaId:NO12_ORDER_INTENT_SCHEMA,evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  symbol:'7203.T',side:'BUY',positionEffect:'OPEN',quantity:200,cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
  syntheticCashAndSlotReserved:true,syntheticArkOwnedPosition:false,timeInForce:'DAY',sor:false,
  orderType:'LIMIT',limitPrice:100.1,accountType:0,accountTypeVerified:true,transmitted:false,productionReady:false};
 const intent={...core,intentSha256:digest(core)};
 const orderIdentity={schemaId:'ARK_NO12_SYNTHETIC_ORDER_ID_OBSERVATION_V1',evidenceMode:'SYNTHETIC_OFFLINE_ONLY',observedAt:created,
  reservedOrderId:81,usedOrderIds:[1,2,80],sourceIntentSha256:intent.intentSha256,syntheticUniquenessChecked:true};
 const orderRequest={intent,orderIdentity,now:new Date(created)},sourceDraft=buildOrder(orderRequest);
 const origin={schemaId:'ARK_NO11_RECORDED_ORDER_ORIGIN_V1',evidenceMode:'RECORDED_NOT_AUTHORIZATION',sessionDate:day,
  intentId:intent.intentSha256,rssOrderId:81,recordedAtJst:created,symbol:'7203.T',side:'BUY',account:'特定',quantity:200,
  productionReady:false,orderTransmission:false};
 const source={schemaId:'ARK_NO11_SYNTHETIC_CANCEL_SOURCE_V1',evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  sessionDate:day,observedAtJst:day+'T09:31:10+09:00',account:'特定',productionReady:false,orderTransmission:false,
  idRows:[{rssOrderId:81,functionName:'RssStockOrder',orderDate:day,orderTime:'09:30:05',orderNumber:'12345',result:'受注完了'}],
  orders:[{orderNumber:'12345',symbol:'7203',account:'特定',side:'買付',trade:'現物',quantity:200,filledQty:100,status:'出来有'}]};
 return {orderRequest,sourceDraft,origin,source,cancelId:82,nowJst:day+'T09:31:11+09:00'};
}

test('cancel preview uses the observed broker number and exactly the official three arguments',()=>{
 const r=cancel(fixture());assert.deepEqual(r.arguments,['82','0','12345']);assert.equal(r.formulaText,'=RssCancelOrder(82,0,12345)');
 assert.equal(r.formulaCellType,'TEXT');assert.equal(r.trigger,0);assert.equal(r.alreadyFilledQuantity,100);assert.equal(r.remainingQuantity,100);
 for(const k of ['cancellationRequestedInBroker','cancellationAcknowledged','cashReserveReleased','formulaEvaluationAllowed','excelOrderWriteAllowed','brokerOrderIdActuallyReserved','orderTransmission','productionReady'])assert.equal(r[k],false,k);
});
test('a long-lived original order can be cancelled using fresh observation without pretending its original id snapshot is new',()=>{
 const x=fixture();x.source.observedAtJst=day+'T10:00:00+09:00';x.nowJst=day+'T10:00:01+09:00';
 const r=cancel(x);assert.equal(r.targetOrderNumber,'12345');assert.equal(x.orderRequest.orderIdentity.observedAt,created);
});
test('cancellation of an unfilled order has zero filled quantity and does not acknowledge completion',()=>{
 const x=fixture();x.source.orders[0].filledQty=0;x.source.orders[0].status='執行中';const r=cancel(x);
 assert.equal(r.alreadyFilledQuantity,0);assert.equal(r.remainingQuantity,200);assert.equal(r.cancellationAcknowledged,false);
});
test('filled cancelled expired pending-cancel and unknown orders are not new cancellable targets',()=>{
 for(const [status,q] of [['約定',200],['取消済（出来有）',100],['出来ず（出来有）',100],['取消中（出来有）',100],['UNKNOWN',100]]){
 const x=fixture();Object.assign(x.source.orders[0],{status,filledQty:q});assert.throws(()=>cancel(x),/TARGET_NOT_CANCELLABLE/);}
});
test('same-symbol personal order cannot replace the exact recorded target number',()=>{
 const x=fixture();x.source.orders[0].orderNumber='99999';assert.throws(()=>cancel(x),/BROKER_ORDER_NOT_UNIQUE_OR_MISSING/);
});
test('cash account side quantity and symbol are checked against the original synthetic order',()=>{
 for(const patch of [{account:'一般'},{side:'SELL'},{quantity:100},{symbol:'6501.T'}]){const x=fixture();Object.assign(x.origin,patch);assert.throws(()=>cancel(x));}
});
test('changed stored order arguments cannot be hidden by recalculating only a draft checksum',()=>{
 const x=fixture();x.sourceDraft=structuredClone(x.sourceDraft);x.sourceDraft.arguments[6]='300';
 const {draftSha256,...body}=x.sourceDraft;x.sourceDraft.draftSha256=digest(body);assert.throws(()=>cancel(x),/ORIGINAL_DRAFT_CHANGED/);
});
test('cancel ids are integer 1 through 2147483647 and must not reuse any known id',()=>{
 for(const id of [0,-1,1.5,2147483648,'82',true,81,80]){const x=fixture();x.cancelId=id;assert.throws(()=>cancel(x));}
 const x=fixture();x.cancelId=2147483647;assert.equal(cancel(x).arguments[0],'2147483647');
});
test('id already observed on a different function is still unavailable for cancellation',()=>{
 const x=fixture();x.source.idRows.push({...x.source.idRows[0],rssOrderId:82,functionName:'RssCancelOrder',orderNumber:'55555'});
 assert.throws(()=>cancel(x),/CANCEL_ID_ALREADY_USED/);
});
test('ambiguous duplicate RSS id cannot be repaired by guessing its target',()=>{
 const x=fixture();x.source.idRows.push({...x.source.idRows[0]});assert.throws(()=>cancel(x),/SOURCE_ID_DUPLICATE_OR_INVALID/);
});
test('unsafe numeric target and injection strings cannot enter a cancellation argument',()=>{
 for(const id of ['9007199254740992','123);BAD(','000123','0']){const x=fixture();x.source.idRows[0].orderNumber=id;x.source.orders[0].orderNumber=id;assert.throws(()=>cancel(x));}
});
test('stale future and cross-session cancellation evidence is rejected',()=>{
 for(const patch of [{nowJst:day+'T09:31:41+09:00'},{nowJst:day+'T09:31:09+09:00'},{nowJst:'2026-10-27T09:31:11+09:00'}]){
 const x=fixture();Object.assign(x,patch);assert.throws(()=>cancel(x));}
});
test('preview cannot consume LIVE evidence or claim transmission permission',()=>{
 for(const patch of [{evidenceMode:'LIVE_ATTESTED'},{orderTransmission:true},{productionReady:true}]){
 const x=fixture();Object.assign(x.source,patch);assert.throws(()=>cancel(x),/SYNTHETIC_SOURCE_REQUIRED/);}
});
test('same inputs produce the same preview without changing any source object or portfolio',()=>{
 const x=fixture(),before=structuredClone(x),a=cancel(x),b=cancel(x);assert.deepEqual(a,b);assert.deepEqual(x,before);
});
