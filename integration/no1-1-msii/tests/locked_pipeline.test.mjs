import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  FREEZE_HEAD, FREEZE_VERSION,DECISION_SCHEMA,LOCKED_FLAGS,
  sealSyntheticDecision,makeLockedIntent,digest
} from '../runtime/locked_intent.mjs';
import {No11SafetyLedger} from '../runtime/safety_ledger.mjs';
import {inspectLockedAccount} from '../runtime/account_gate.mjs';

const t0='2026-10-09T09:30:00+09:00';
const t1='2026-10-09T09:31:00+09:00';
const fakeHash='a'.repeat(64);
const map=[{
  sourceSymbol:'72030',brokerSymbol:'7203.T',verified:true,
  verifiedAt:'2026-10-09T08:00:00+09:00',
  authority:'DATED_SECURITY_MASTER_AND_MSII',mappingProofSha256:fakeHash
}];
const core = (override={}) => ({
  schemaId:DECISION_SCHEMA,strategyFreezeCommit:FREEZE_HEAD,strategyVersion:FREEZE_VERSION,
  eventId:'frozen-event-001',intentId:'frozen-intent-001',strategyId:'ARK_NO11',
  session:'2026-10-09',decisionAt:t0,sourceKnownAt:t0,
  sourceSymbol:'72030',direction:'LONG',intentKind:'ENTRY',
  side:'BUY',positionEffect:'OPEN',admission:'APPROVED_BY_FROZEN_NO11',
  quantity:100,orderType:'MARKET',limitPrice:null,timeInForce:'DAY',
  sor:true,accountType:0,accountTypeVerified:true,
  evidenceMode:'SYNTHETIC',liveSourceCertified:false,
  stateObserved:true,formalState9Primary:'RISE',stateKnownAt:t0,entryBefore1520:true,
  frozenEventSourceSha256:fakeHash,safety:{...LOCKED_FLAGS},...override
});
function decide(override={}){return sealSyntheticDecision(core(override));}
function locked(override={}){return makeLockedIntent(decide(override),{symbolMap:map});}
function mustFail(override,part){assert.throws(()=>locked(override),e=>e.message.includes(part));}
function clone(x){return structuredClone(x);}
function baseline(external=[{symbol:'408A',quantity:180}],ark=[]) {
  const x={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,
    capturedAt:t0,source:'LOCAL_PRIVATE_BASELINE',externalPositions:external,arkManagedPositions:ark};
  return {...x,baselineSha256:digest(x)};
}
function freshSnapshot() {
  return {schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',
    mode:'READ_ONLY',capturedAt:t0,captureCompletedAt:t1,positions:[{symbol:'408A',quantity:180}],
    orders:[],executions:[],buyingPower:800000,safety:{...LOCKED_FLAGS}};
}
function health(){
  return {schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,
    addinLoaded:true,workbookPersisted:true,rssErrors:0,healthCapturedAt:t1,
    feeds:Object.fromEntries(Object.entries({
      capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'
    }).map(([k,state])=>[k,{state,observedAt:t1}]))};
}
function account(overrides={}) {
  return inspectLockedAccount({snapshot:freshSnapshot(),health:health(),ownership:baseline(),
    lockedIntent:locked(),now:new Date('2026-10-09T09:31:02+09:00'),maxOrderNotional:250000,...overrides});
}
function ledgerFixture() {
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'ark-no11-'));
  const filename=path.join(folder,'private-ledger.json');
  return {folder,filename,ledger:new No11SafetyLedger(filename),
    cleanup(){fs.rmSync(folder,{recursive:true,force:true});}};
}
function verifySession(ledger,day='2026-10-09',at='2026-10-09T09:30:00+09:00'){
  return ledger.verifyTradingSession({session:day,readAt:at,calendarVerified:true,accountReconciled:true,sourceFresh:true});
}
const sellFill = (override={})=>({
  brokerExecutionId:'E001',orderId:'O001',side:'SELL',quantity:30,
  session:'2026-10-09',executedAt:'2026-10-09T09:33:00+09:00',
  source:'MARKETSPEED_II_RSS',brokerReconciled:true,verifiedExecution:true,...override
});

test('deterministic locked intent, no execution ability, SOR preserved',()=>{
  const a=locked(),b=locked();
  assert.deepEqual(a,b);assert.equal(a.sor,true);
  assert.equal(a.symbol,'7203.T');assert.equal(a.quantity,100);
  assert.equal(a.executionAllowed,undefined);assert.equal(a.executable,false);
  assert.equal(a.safety.rssOrderFunctionAllowed,false);
});
test('intent hash detects any mutation',()=>{const d=decide();d.quantity=200;assert.throws(()=>makeLockedIntent(d,{symbolMap:map}),/DECISION_HASH_MISMATCH/);});
test('reject changed Frozen SHA',()=>mustFail({strategyFreezeCommit:'bad'},'FROZEN_STRATEGY_IDENTITY_MISMATCH'));
test('reject negative, zero and non-lot quantity',()=>{for(const q of [-100,0,1,101,NaN,1.5])mustFail({quantity:q},'CASH_100_LOT_REQUIRED');});
test('both excluded State9 entry classes reject',()=>{
  for(const formalState9Primary of ['PULLBACK','SHARP_DROP'])mustFail({formalState9Primary},'NO11_ENTRY_STATE_EXCLUDED');
});
test('missing State9 rejects rather than assumed RISE',()=>mustFail({stateObserved:false,formalState9Primary:null},'ENTRY_STATE_UNAVAILABLE'));
test('source known later than decision fails',()=>mustFail({sourceKnownAt:t1},'FUTURE_INFORMATION_USED'));
test('state known later than decision fails',()=>mustFail({stateKnownAt:t1},'FUTURE_STATE_USED'));
test('session mismatch fails',()=>mustFail({session:'2026-10-08'},'SESSION_TIMESTAMP_MISMATCH'));
test('15:20 entry cutoff is fail closed',()=>mustFail({decisionAt:'2026-10-09T15:20:00+09:00',sourceKnownAt:t0,stateKnownAt:t0},'CASH_ENTRY_CUTOFF_1520'));
test('cannot make buy out of sell effect',()=>mustFail({positionEffect:'CLOSE'},'LONG_SIDE_EFFECT_MISMATCH'));
test('cannot make short or margin',()=>mustFail({direction:'SHORT'},'CASH_LONG_ONLY'));
test('cannot infer admission from a rank or score',()=>mustFail({admission:'SCORED_ONLY'},'UPSTREAM_FROZEN_ADMISSION_REQUIRED'));
test('cannot invent order type or SOR',()=>{
  mustFail({orderType:'MARGIN'},'ORDER_TYPE_NOT_SUPPORTED');
  mustFail({sor:null},'SOR_NOT_EXPLICIT');
  mustFail({timeInForce:'GTC'},'DAY_ORDERS_ONLY');
});
test('requires explicit and verified broker account type',()=>mustFail({accountTypeVerified:false},'ACCOUNT_TYPE_NOT_VERIFIED'));
test('requires exact source symbol mapping, not blind truncate',()=>{
  const x=decide();assert.throws(()=>makeLockedIntent(x,{symbolMap:[]}),/SYMBOL_MAP_UNRESOLVED/);
  assert.throws(()=>makeLockedIntent(x,{symbolMap:[map[0],map[0]]}),/SYMBOL_MAP_UNRESOLVED/);
  assert.throws(()=>makeLockedIntent(x,{symbolMap:[{...map[0],verified:false}]}),/SYMBOL_MAP_NOT_VERIFIED/);
});
test('distinct verified source codes cannot collide into same broker code',()=>{
  assert.throws(()=>makeLockedIntent(decide(),{symbolMap:[...map,
    {...map[0],sourceSymbol:'99990'}]}),/BROKER_SYMBOL_MAPPING_COLLISION/);
});
test('reject fake LIVE source certification',()=>{
  const unverified=core({evidenceMode:'LIVE_ATTESTED',liveSourceCertified:false});
  assert.throws(()=>makeLockedIntent({...unverified,decisionSha256:digest(unverified)},{symbolMap:map}),/LIVE_SOURCE_RECEIPT_REQUIRED/);
  mustFail({evidenceMode:'SYNTHETIC',liveSourceCertified:true},'SYNTHETIC_CANNOT_BE_LIVE_CERTIFIED');
});
test('EXIT intent is independent of Entry current state and never unlocks',()=>{
  const x=locked({intentKind:'EXIT',side:'SELL',positionEffect:'CLOSE',
    stateObserved:false,formalState9Primary:null});
  assert.equal(x.side,'SELL');assert.equal(x.executable,false);
});
test('fresh RSS plus explicit ownership may reach LOCKED candidate, never send',()=>{
  const result=account();
  assert.equal(result.status,'LOCKED_CANDIDATE_ONLY');
  assert.equal(result.executionAllowed,false);
});
test('snapshot stale blocks, never age rejuvenate',()=>{
  const s=freshSnapshot();s.captureCompletedAt='2026-10-09T09:29:00+09:00';
  assert.equal(account({snapshot:s}).status,'BLOCKED');
});
test('RSS status and #NAME? fail closed',()=>{
  const h=health();h.feeds.capacity.state='#NAME?';
  assert(account({health:h}).blockers.some(x=>x.includes('RSS_FEED_NOT_READY')));
});
test('one stale RSS feed blocks even if snapshot is new',()=>{
  const h=health();h.feeds.positions.observedAt='2026-10-09T09:20:00+09:00';
  assert(account({health:h}).blockers.some(x=>x.includes('RSS_FEED_NOT_FRESH')));
});
test('missing positions/orders/exec arrays are not converted to zero',()=>{
  const s=freshSnapshot();delete s.positions;assert.equal(account({snapshot:s}).status,'BLOCKED');
});
test('personal ownership must be frozen explicitly and hash-valid',()=>{
  assert(account({ownership:baseline([])}).blockers.some(x=>x.includes('UNKNOWN_BROKER_POSITION')));
  const o=baseline();o.externalPositions[0].quantity=100;
  assert(account({ownership:o}).blockers.some(x=>x.includes('OWNERSHIP_BASELINE_HASH')));
});
test('open orders and partial fills are blocked',()=>{
  const s=freshSnapshot();s.orders=[{orderNumber:'123',status:'配信中',quantity:100,filledQty:10}];
  assert(account({snapshot:s}).blockers.includes('BROKER_PARTIAL_FILL'));
});
test('MAX3 and cash-only preflight never assume available money',()=>{
  assert(account({maxOrderNotional:null}).blockers.includes('FRESH_CASH_RESERVATION_REQUIRED'));
  assert(account({maxOrderNotional:900000}).blockers.includes('INSUFFICIENT_CASH'));
});
test('failed own-stock SELL never uses personal holding',()=>{
  const d=locked({intentKind:'EXIT',side:'SELL',positionEffect:'CLOSE'});
  const x=account({lockedIntent:d});
  assert(x.blockers.includes('SELL_NOT_SUPPORTED_BY_ARK_OWNERSHIP'));
});
test('fresh ledger starts kill-switched and cannot transmit',()=>{
  const f=ledgerFixture();try{
    assert(f.ledger.snapshot().killSwitchLatched);
    assert.equal(f.ledger.inspectBuy('2026-10-09').status,'BLOCKED');
    assert.equal(f.ledger.snapshot().safety.transmitted,false);
  }finally{f.cleanup();}
});
test('explicit human health reset only after verified session',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);
    f.ledger.explicitSafetyReset({humanApproved:true,healthyAccountVerified:true,sourceFresh:true,readAt:t1});
    assert.equal(f.ledger.inspectBuy('2026-10-09').status,'LOCKED_ONLY_CANDIDATE');
    assert.equal(f.ledger.snapshot().safety.executionAllowed,false);
  }finally{f.cleanup();}
});
test('SELL intent alone does not latch; first PARTIAL fill does',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);
    f.ledger.explicitSafetyReset({humanApproved:true,healthyAccountVerified:true,sourceFresh:true,readAt:t1});
    assert.equal(f.ledger.snapshot().sellFillLatched,false);
    f.ledger.recordBrokerSellFill(sellFill());
    assert.equal(f.ledger.inspectBuy('2026-10-09').status,'BLOCKED');
    assert(f.ledger.inspectBuy('2026-10-09').blockers.includes('NO11_AFTER_FIRST_SELL_FILL_BUY_PROHIBITED'));
  }finally{f.cleanup();}
});
test('repeat RSS polls idempotent; divergent duplicate kills',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);f.ledger.recordBrokerSellFill(sellFill());
    const old=f.ledger.snapshot();
    f.ledger.recordBrokerSellFill(sellFill());
    assert.equal(f.ledger.snapshot().revision,old.revision);
    f.ledger.recordBrokerSellFill(sellFill({quantity:31}));
    assert(f.ledger.snapshot().faults.includes('BROKER_EXECUTION_ID_CONFLICT'));
  }finally{f.cleanup();}
});
test('latched SELL fill survives restart and resets on verified next session',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);f.ledger.recordBrokerSellFill(sellFill());
    const reopened=new No11SafetyLedger(f.filename);
    assert.equal(reopened.snapshot().sellFillLatched,true);
    reopened.verifyTradingSession({session:'2026-10-12',readAt:'2026-10-12T09:30:00+09:00',
      calendarVerified:true,accountReconciled:true,sourceFresh:true});
    assert.equal(reopened.snapshot().sellFillLatched,false);
    assert.equal(reopened.snapshot().killSwitchLatched,true);
  }finally{f.cleanup();}
});
test('unverified/foreign sell receipt cannot be treated as legal fill',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);
    f.ledger.recordBrokerSellFill(sellFill({brokerReconciled:false}));
    assert(f.ledger.snapshot().killSwitchLatched);
  }finally{f.cleanup();}
});
test('corrupted restart file stops all transitions',()=>{
  const f=ledgerFixture();try{
    fs.writeFileSync(f.filename,'{"tampered":true}');
    const reopened=new No11SafetyLedger(f.filename);
    assert.throws(()=>reopened.inspectBuy('2026-10-09'),/SAFETY_LEDGER_CORRUPT_FAIL_CLOSED/);
  }finally{f.cleanup();}
});
test('health-only reset without explicit approval stays latched',()=>{
  const f=ledgerFixture();try{
    verifySession(f.ledger);
    f.ledger.explicitSafetyReset({humanApproved:false,healthyAccountVerified:true,sourceFresh:true,readAt:t1});
    assert.equal(f.ledger.snapshot().killSwitchLatched,true);
  }finally{f.cleanup();}
});
