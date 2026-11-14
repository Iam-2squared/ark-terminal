import test from 'node:test';
import assert from 'node:assert/strict';
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {buildNo12SyntheticMsiiOrderText as build,NO12_ORDER_INTENT_SCHEMA} from '../runtime/synthetic_msii_draft.mjs';
import {bindObservedOrder as bind} from '../tools/no11_broker_order_state.mjs';
import {buildSyntheticCancelText as cancel} from '../tools/no11_order_cancel_preview.mjs';
import {orderInstant,currentOrderInstant,validMsiiOrderId,validateMsiiOrderIds,MSII_MAX_ORDER_ID,NS_PER_MS} from '../runtime/no11_order_boundary.mjs';

const day='2026-10-26';
const at=(second,fraction='')=>`${day}T09:30:${String(second).padStart(2,'0')}${fraction}+09:00`;

function fixture(side='BUY',recorded=at(10)){
 const core={schemaId:NO12_ORDER_INTENT_SCHEMA,evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  symbol:'7203.T',side,positionEffect:side==='BUY'?'OPEN':'CLOSE',
  quantity:200,cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
  syntheticCashAndSlotReserved:side==='BUY',syntheticArkOwnedPosition:side==='SELL',
  timeInForce:'DAY',sor:false,orderType:'MARKET',limitPrice:null,
  accountType:0,accountTypeVerified:true,transmitted:false,productionReady:false};
 const intent={...core,intentSha256:digest(core)};
 const request={intent,orderIdentity:{schemaId:'ARK_NO12_SYNTHETIC_ORDER_ID_OBSERVATION_V1',
  evidenceMode:'SYNTHETIC_OFFLINE_ONLY',observedAt:recorded,reservedOrderId:81,
  usedOrderIds:[1,2,80],sourceIntentSha256:intent.intentSha256,syntheticUniquenessChecked:true},
  now:recorded};
 const origin={schemaId:'ARK_NO11_RECORDED_ORDER_ORIGIN_V1',evidenceMode:'RECORDED_NOT_AUTHORIZATION',
  sessionDate:day,intentId:intent.intentSha256,rssOrderId:81,recordedAtJst:recorded,
  symbol:'7203.T',side,quantity:200,account:'特定',productionReady:false,orderTransmission:false};
 const idRows=[{rssOrderId:81,functionName:'RssStockOrder',orderDate:day,orderTime:'09:30:10',orderNumber:'123457'}];
 const orders=[{orderNumber:'123457',symbol:'7203',side:side==='BUY'?'買付':'売付',trade:'現物',
  account:'特定',quantity:200,filledQty:0,status:'執行中'}];
 const source={schemaId:'ARK_NO11_SYNTHETIC_CANCEL_SOURCE_V1',evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  sessionDate:day,observedAtJst:at(11),account:'特定',idRows,orders,productionReady:false,orderTransmission:false};
 return {request,origin,idRows,orders,source};
}
function link(f,through=at(11),previousFilled=0){
 return bind({origin:f.origin,idRows:f.idRows,orders:f.orders,sessionDate:day,throughJst:through,previousFilled});
}
function cancellation(f,now=at(12),cancelId=82,sourceDraft=build(f.request)){
 return cancel({orderRequest:f.request,sourceDraft,origin:f.origin,source:f.source,cancelId,nowJst:now});
}

test('exact ordinary BUY and SELL arguments, checksum, and locked output unchanged',()=>{
 for(const side of ['BUY','SELL']){
  const f=fixture(side),draft=build(f.request);
  assert.deepEqual(draft.arguments,['81','0','7203.T',side==='BUY'?'3':'1','0','0','200','0','','1','','0','','','','','0','','','']);
  const {draftSha256,...core}=draft;
  assert.equal(draftSha256,digest(core));
  assert.equal(draft.formulaCellType,'TEXT');
  for(const k of ['formulaEvaluationAllowed','orderTransmission','excelOrderWriteAllowed','brokerOrderIdActuallyReserved','brokerOrderActuallySubmitted']){
   assert.equal(draft[k],false);
  }
 }
});

test('official maximum ID accepted, maximum plus one rejected for both BUY and SELL',()=>{
 for(const side of ['BUY','SELL']){
  const f=fixture(side);f.request.orderIdentity.reservedOrderId=MSII_MAX_ORDER_ID;
  assert.equal(build(f.request).rssOrderId,MSII_MAX_ORDER_ID);
  f.request.orderIdentity.reservedOrderId++;
  assert.throws(()=>build(f.request),/NO12_RSS_ID_NOT_AVAILABLE/);
 }
});

test('used source IDs share official range and reject strings, booleans, duplicates and oversize',()=>{
 for(const item of [0,-1,1.5,'3',true,2147483648,NaN,Infinity]){
  const f=fixture();f.request.orderIdentity.usedOrderIds.push(item);
  assert.throws(()=>build(f.request),/NO12_RSS_USED_ORDER_IDS_INVALID/);
 }
 const f=fixture();f.request.orderIdentity.usedOrderIds=[1,1];
 assert.throws(()=>build(f.request),/NO12_RSS_USED_ORDER_IDS_INVALID/);
 f.request.orderIdentity.usedOrderIds=Array.from({length:5001},(_,i)=>i+100);
 assert.throws(()=>build(f.request),/NO12_RSS_USED_ORDER_IDS_INVALID/);
});

test('zero, one and max ID boundaries use numeric integers without coercion',()=>{
 assert.equal(validMsiiOrderId(1),true);assert.equal(validMsiiOrderId(2147483647),true);
 for(const n of [0,2147483648,'1',true,null,NaN,Infinity])assert.equal(validMsiiOrderId(n),false);
 assert.equal(validateMsiiOrderIds([], 'BAD').size,0);
 assert.throws(()=>validateMsiiOrderIds([1,1],'BAD'),/BAD/);
});

test('a one millisecond future observation cannot enter an order preview',()=>{
 const f=fixture('BUY',at(10,'.001'));f.request.now=at(10);
 assert.throws(()=>build(f.request),/NO12_ORDER_ID_SNAPSHOT_STALE/);
});

test('a 100 ns future observation is not silently rounded back to present',()=>{
 const f=fixture('BUY',at(10,'.0000001'));f.request.now=at(10,'.0000000');
 assert.throws(()=>build(f.request),/NO12_ORDER_ID_SNAPSHOT_STALE/);
});

test('exact thirty second age passes but thirty seconds plus 100 ns fails',()=>{
 const f=fixture('BUY',at(10,'.1234567'));f.request.now=at(40,'.1234567');
 assert.equal(build(f.request).trigger,0);
 f.request.now=at(40,'.1234568');
 assert.throws(()=>build(f.request),/NO12_ORDER_ID_SNAPSHOT_STALE/);
});

test('PowerShell seven-digit timestamps and epoch milliseconds are retained',()=>{
 const t=orderInstant(at(10,'.1234567'),'BAD',{jstOnly:true});
 assert.equal(t.ns%1000000000n,123456700n);
 assert.equal(t.epochMs,Date.parse(at(10,'.123')));
 const f=fixture('BUY',at(10,'.1234567'));f.request.now=at(10,'.1234567');
 assert.equal(build(f.request).trigger,0);
});

test('equivalent ISO offsets and Date instances give the same instant',()=>{
 assert.equal(orderInstant(at(10),'BAD').ns,orderInstant(`${day}T00:30:10Z`,'BAD').ns);
 const f=fixture();f.request.now=new Date(at(10));
 assert.equal(build(f.request).trigger,0);
 assert.equal(currentOrderInstant(new Date(at(10)),'BAD').ns,orderInstant(at(10),'BAD').ns);
 assert.throws(()=>currentOrderInstant(new Date(NaN),'BAD'),/BAD/);
});

test('calendar validation rejects impossible days instead of Date.parse rollover',()=>{
 for(const text of ['2026-02-29T09:30:10+09:00','2026-04-31T09:30:10+09:00',
  '2026-00-10T09:30:10+09:00','2026-10-00T09:30:10+09:00','2026-13-01T09:30:10+09:00']){
  assert.throws(()=>orderInstant(text,'BAD'),/BAD/);
  const f=fixture();f.request.orderIdentity.observedAt=text;
  assert.throws(()=>build(f.request),/OBSERVATION_CLOCK_INVALID/);
 }
 assert.doesNotThrow(()=>orderInstant('2028-02-29T09:30:10+09:00','BAD'));
});

test('24:00, leap second, absent zones, bad zones and more than seven digits rejected',()=>{
 for(const text of [`${day}T24:00:00+09:00`,`${day}T09:60:00+09:00`,`${day}T09:30:60+09:00`,
  `${day}T09:30:10`,`${day}T09:30:10+14:01`,`${day}T09:30:10+09:60`,`${day}T09:30:10.12345678+09:00`]){
  assert.throws(()=>orderInstant(text,'BAD'),/BAD/);
 }
});

test('recorded JST origin and through time reject invalid or non-JST values',()=>{
 for(const value of [at(10).replace('+09:00','Z'),`${day}T24:00:00+09:00`,null]){
  const f=fixture();f.origin.recordedAtJst=value;
  assert.throws(()=>link(f),/ORDER_ORIGIN/);
 }
 const f=fixture();
 assert.throws(()=>link(f,`${day}T09:30:12Z`),/ORDER_ORIGIN_CLOCK/);
});

test('same vendor second accepts the last 100 ns of local origin without an extra second delay',()=>{
 const f=fixture('BUY',at(10,'.9999999'));
 const r=link(f,at(11));
 assert.equal(r.brokerOrderNumber,'123457');
 assert.equal(r.executionTimeCertified,false);
});

test('an older vendor second never binds even if separated by less than one second',()=>{
 const f=fixture('BUY',at(10,'.0000001'));
 f.idRows[0].orderTime='09:30:09';
 assert.throws(()=>link(f),/RSS_ID_ORDER_CLOCK/);
});

test('invalid vendor order-time and nonexistent source day cannot normalize to valid map',()=>{
 for(const clock of ['24:00:00','09:60:00','09:30:60']){
  const f=fixture();f.idRows[0].orderTime=clock;
  assert.throws(()=>link(f),/RSS_ID_ORDER_CLOCK/);
 }
 const f=fixture();const invalid='2026-02-29';
 f.origin.sessionDate=invalid;f.origin.recordedAtJst=`${invalid}T09:30:10+09:00`;
 assert.throws(()=>bind({...f,sessionDate:invalid,throughJst:`${invalid}T09:30:11+09:00`}),/ORDER_ORIGIN_CLOCK/);
});

test('100 ns future origin cannot bind to a current source observation',()=>{
 const f=fixture('BUY',at(10,'.0000001'));
 assert.throws(()=>link(f,at(10)),/ORDER_ORIGIN_CLOCK/);
});

test('seven-digit recorded origin survives existing cancel compiler reconstruction',()=>{
 const f=fixture('BUY',at(10,'.1234567'));
 f.source.observedAtJst=at(11,'.7654321');
 const r=cancellation(f,at(12,'.7654321'));
 assert.deepEqual(r.arguments,['82','0','123457']);
 assert.equal(r.cancellationAcknowledged,false);
 assert.equal(r.cashReserveReleased,false);
});

test('equivalent zero fractional representations bind the identical cancel origin',()=>{
 const f=fixture();f.origin.recordedAtJst=at(10,'.0000000');
 assert.equal(cancellation(f).targetOrderNumber,'123457');
});

test('cancel source future by 100 ns is rejected without rounding',()=>{
 const f=fixture();f.source.observedAtJst=at(12,'.0000001');
 assert.throws(()=>cancellation(f,at(12)),/NO11_CANCEL_SOURCE_CLOCK/);
});

test('cancel thirty second age boundary retains sub-millisecond precision',()=>{
 const f=fixture();f.source.observedAtJst=at(11,'.3333333');
 assert.equal(cancellation(f,at(41,'.3333333')).trigger,0);
 assert.throws(()=>cancellation(f,at(41,'.3333334')),/NO11_CANCEL_SOURCE_CLOCK/);
});

test('cancel ID max is accepted but max plus one is rejected',()=>{
 const f=fixture();
 assert.equal(cancellation(f,at(12),2147483647).arguments[0],'2147483647');
 assert.throws(()=>cancellation(f,at(12),2147483648),/NO11_CANCEL_RSS_ID_RANGE/);
});

test('invalid original used-ID list fails before cancel origin reconstruction',()=>{
 const f=fixture();const draft=build(f.request);
 f.request.orderIdentity.usedOrderIds.push(2147483648);
 assert.throws(()=>cancellation(f,at(12),82,draft),/NO11_CANCEL_RSS_ID_RANGE/);
});

test('BUY acknowledgement partial fill cancel-pending cancel-complete remain distinct end to end',()=>{
 const f=fixture();const before=structuredClone(f);
 const draft=build(f.request);
 assert.equal(link(f).order.phase,'ACKNOWLEDGED');
 f.orders[0].filledQty=100;f.orders[0].status='出来有';
 let r=link(f);assert.equal(r.observedFilledDelta,100);assert.equal(r.cancelAcknowledged,false);
 const preview=cancellation(f,at(12),82,draft);
 assert.equal(preview.alreadyFilledQuantity,100);assert.equal(preview.remainingQuantity,100);
 assert.equal(preview.cashReserveReleased,false);
 f.orders[0].status='取消中（出来有）';
 r=link(f,at(13),100);assert.equal(r.order.phase,'CANCEL_PENDING');assert.equal(r.cancelAcknowledged,false);
 assert.throws(()=>cancellation(f,at(14),83,draft),/TARGET_NOT_CANCELLABLE/);
 f.orders[0].status='取消済（出来有）';
 r=link(f,at(15),100);assert.equal(r.order.phase,'CANCELLED');assert.equal(r.cancelAcknowledged,true);
 assert.equal(r.observedFilledDelta,0);assert.equal(r.order.filledQty,100);
 assert.equal(r.orderCanBeResent,false);assert.equal(r.executionPriceAttributed,false);
 assert.deepEqual(f.request,before.request);
});

test('SELL partial observation halts flag without claiming a complete sale or price attribution',()=>{
 const f=fixture('SELL');f.orders[0].filledQty=100;f.orders[0].status='出来有';
 const r=link(f);
 assert.equal(r.sellFillObserved,true);assert.equal(r.order.phase,'PARTIAL');assert.equal(r.order.terminal,false);
 assert.equal(r.executionPriceAttributed,false);assert.equal(r.orderTransmission,false);
 assert.equal(cancellation(f).alreadyFilledQuantity,100);
});

test('same-symbol other broker number cannot substitute, repeated unchanged quantity is zero delta',()=>{
 const f=fixture();f.orders.push({...f.orders[0],orderNumber:'999888',filledQty:200,status:'約定'});
 f.orders[0].filledQty=100;f.orders[0].status='出来有';
 assert.equal(link(f,at(11),100).observedFilledDelta,0);
 f.orders.shift();
 assert.throws(()=>link(f),/BROKER_ORDER_NOT_UNIQUE_OR_MISSING/);
});

test('unknown, terminal and cumulative regression never permit a cancellation preview',()=>{
 for(const [status,filled] of [['不明',0],['約定',200],['取消済（出来無）',0]]){
  const f=fixture();f.orders[0].status=status;f.orders[0].filledQty=filled;
  assert.throws(()=>cancellation(f),/TARGET_NOT_CANCELLABLE/);
 }
 const f=fixture();assert.throws(()=>link(f,at(11),100),/CUMULATIVE_FILL_REVERSED/);
});

test('200 clock fractions preserve causal ordering without Number rounding',()=>{
 const origin=orderInstant(at(10),'BAD').ns;
 for(let i=1;i<=200;i++){
  const suffix='.'+String(i).padStart(7,'0');
  const instant=orderInstant(at(10,suffix),'BAD');
  assert.equal(instant.ns-origin,BigInt(i)*100n);
  const f=fixture('BUY',at(10,suffix));f.request.now=at(10);
  assert.throws(()=>build(f.request),/SNAPSHOT_STALE/);
 }
});

test('source objects are unchanged and BigInt comparison details never leak into output JSON',()=>{
 const f=fixture('BUY',at(10,'.1234567')),before=structuredClone(f);
 const values=[build(f.request),link(f),cancellation(f)];
 assert.deepEqual(f,before);
 for(const value of values)assert.doesNotThrow(()=>JSON.stringify(value));
});

test('live authorization flags remain blocked throughout order and cancellation previews',()=>{
 const f=fixture();
 f.request.intent.productionReady=true;
 const {intentSha256,...body}=f.request.intent;
 f.request.intent.intentSha256=digest(body);
 f.request.orderIdentity.sourceIntentSha256=f.request.intent.intentSha256;
 assert.throws(()=>build(f.request),/LIVE_OR_UNVERIFIED_INTENT_REJECTED/);
 const g=fixture();g.source.orderTransmission=true;
 assert.throws(()=>cancellation(g),/SYNTHETIC_SOURCE_REQUIRED/);
});
