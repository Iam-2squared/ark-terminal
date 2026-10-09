import test from 'node:test';
import assert from 'node:assert/strict';
import {makeLockedMsiiDraft} from '../runtime/msii_order_draft.mjs';
import {FREEZE_HEAD,FREEZE_VERSION,LOCKED_FLAGS,DECISION_SCHEMA,
  sealSyntheticDecision,makeLockedIntent,digest} from '../runtime/locked_intent.mjs';
const t='2026-10-09T09:30:00+09:00',fakeHash='a'.repeat(64);
function intent(side='BUY',sor=true){
  const buy=side==='BUY';
  const input={
    schemaId:DECISION_SCHEMA,strategyFreezeCommit:FREEZE_HEAD,strategyVersion:FREEZE_VERSION,
    evidenceMode:'SYNTHETIC',liveSourceCertified:false,safety:{...LOCKED_FLAGS},
    eventId:'event',intentId:'intent',strategyId:'ARK_NO11',session:'2026-10-09',
    decisionAt:t,sourceKnownAt:t,stateKnownAt:t,sourceSymbol:'72030',
    stateObserved:true,formalState9Primary:'RISE',entryBefore1520:true,
    direction:'LONG',intentKind:buy?'ENTRY':'EXIT',side,
    positionEffect:buy?'OPEN':'CLOSE',
    admission:'APPROVED_BY_FROZEN_NO11',quantity:100,orderType:'MARKET',
    limitPrice:null,timeInForce:'DAY',sor,accountType:0,accountTypeVerified:true,
    frozenEventSourceSha256:fakeHash
  };
  return makeLockedIntent(sealSyntheticDecision(input),{symbolMap:[{
    sourceSymbol:'72030',brokerSymbol:'7203.T',authority:'DATED_SECURITY_MASTER_AND_MSII',
    verified:true,verifiedAt:t,mappingProofSha256:fakeHash
  }]});
}
function evidence(x,override={}){
  const source={schemaId:'ARK_MSII_ORDER_ID_READONLY_OBSERVATION_V1',
    source:'MARKETSPEED_II_RSS_ORDER_ID_LIST',readOnly:true,capturedAt:t,
    usedOrderIds:[1,2],reservedOrderId:3,
    sourceIntentId:x.sourceIntentId,sourceIntentHash:x.lockedIntentSha256,
    confirmedUniqueAcrossLocalWorkbooks:true,...override};
  return {...source,observationSha256:digest(source)};
}
const make=(i,e)=>makeLockedMsiiDraft(i,e,{now:t});
test('RssStockOrder 20 args keep SOR, quantity, side and locked trigger=0',()=>{
  const x=intent(),out=make(x,evidence(x));
  assert.equal(out.function,'RssStockOrder');
  assert.equal(out.arguments.length,20);
  assert.equal(out.arguments[1],'0'); // trigger
  assert.equal(out.arguments[2],'7203.T');
  assert.equal(out.arguments[3],'3'); // BUY
  assert.equal(out.arguments[5],'1'); // SOR
  assert.equal(out.arguments[6],'100');
  assert.equal(out.arguments[7],'0'); // Market
  assert.equal(out.arguments[9],'1'); // DAY
  assert.equal(out.arguments[11],'0'); // 特定
  assert.equal(out.trigger,0);
  assert.equal(out.formulaCellType,'TEXT');
  assert.equal(out.formulaEvaluationAllowed,false);
  assert.equal(out.executable,false);assert.equal(out.transmitted,false);
});
test('SELL SOR=false maps sell=1 normal SOR=0',()=>{
  const x=intent('SELL',false),out=make(x,evidence(x));
  assert.equal(out.arguments[3],'1');assert.equal(out.arguments[5],'0');
  assert.equal(out.excelOrderWriteAllowed,false);
});
test('duplicate broker-used order id is blocked',()=>{
  const x=intent();assert.throws(()=>make(x,evidence(x,{reservedOrderId:2})),/ORDER_ID_ALREADY_USED/);
});
test('missing local-workbook uniqueness proof fails closed',()=>{
  const x=intent();
  assert.throws(()=>make(x,evidence(x,{confirmedUniqueAcrossLocalWorkbooks:false})),/ORDER_ID_LOCAL_COLLISION_NOT_EXCLUDED/);
});
test('stale source used-ID list does not certify a draft',()=>{
  const x=intent();
  assert.throws(()=>makeLockedMsiiDraft(x,evidence(x),{now:'2026-10-09T09:32:00+09:00'}),/ORDER_ID_SNAPSHOT_STALE/);
});
test('order ID source hash mismatch rejects edited used-order data',()=>{
  const x=intent(),e=evidence(x);e.usedOrderIds.push(3);
  assert.throws(()=>make(x,e),/ORDER_ID_OBSERVATION_HASH_MISMATCH/);
});
test('source intent hash must match the particular Frozen cash intent',()=>{
  const x=intent();
  assert.throws(()=>make(x,evidence(x,{sourceIntentHash:fakeHash})),/ORDER_ID_INTENT_PROOF_MISMATCH/);
});
test('unverified account 7 cannot be represented in the cash-only contract',()=>{
  const x=intent();const y={...x,accountType:7};
  y.lockedIntentSha256=digest(Object.fromEntries(Object.entries(y).filter(([k])=>k!=='lockedIntentSha256')));
  assert.throws(()=>make(y,evidence(y)),/MSII_ACCOUNT_TYPE_INVALID/);
});
