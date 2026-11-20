import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {inspect} from '../tools/no11_shadow_preflight.mjs';
import {No11SafetyLedger} from '../runtime/safety_ledger.mjs';
import {DECISION_SCHEMA,FREEZE_HEAD,FREEZE_VERSION,LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';

const tokyoDay=ms=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',
  year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms)).replace(/\//g,'-');
function fixture(){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-e2e-'));
  const current=new Date();
  const now=current.toISOString(), before=new Date(+current-1500).toISOString();
  const session=tokyoDay(+current), hash='a'.repeat(64);
  const write=(key,obj)=>{const filename=path.join(root,key+'.json');fs.writeFileSync(filename,JSON.stringify(obj));return filename};
  const snap={
    schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',capturedAt:before,captureCompletedAt:now,
    source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',positions:[{symbol:'408A',quantity:180}],
    orders:[],executions:[],buyingPower:500000,safety:{...LOCKED_FLAGS}
  };
  const health={
    schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,
    workbookPersisted:true,addinLoaded:true,rssErrors:0,healthCapturedAt:now,
    actualFeedTimestampCertified:false,
    feeds:Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',
      executions:'配信中',positions:'配信中'}).map(([k,state])=>[k,{state,observedAt:now}]))
  };
  const own={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',capturedAt:now,source:'LOCAL_TEST',
    frozen:true,externalPositions:[{symbol:'408A',quantity:180}],arkManagedPositions:[]};
  const dec={schemaId:DECISION_SCHEMA,strategyFreezeCommit:FREEZE_HEAD,
    strategyVersion:FREEZE_VERSION,session,eventId:'source-id',intentId:'intent-id',
    strategyId:'ARK_NO11',decisionAt:now,sourceKnownAt:now,sourceSymbol:'72030',
    direction:'LONG',intentKind:'ENTRY',side:'BUY',positionEffect:'OPEN',
    admission:'APPROVED_BY_FROZEN_NO11',quantity:100,orderType:'MARKET',limitPrice:null,
    timeInForce:'DAY',sor:false,accountType:0,accountTypeVerified:true,
    evidenceMode:'SYNTHETIC',liveSourceCertified:false,stateObserved:true,
    formalState9Primary:'RISE',stateKnownAt:now,entryBefore1520:true,
    frozenEventSourceSha256:hash,safety:{...LOCKED_FLAGS}};
  const args={
    snapshot:write('snapshot',snap),health:write('health',health),
    ownership:write('ownership',{...own,baselineSha256:digest(own)}),
    decision:write('decision',{...dec,decisionSha256:digest(dec)}),
    'symbol-map':write('symbols',{rows:[{sourceSymbol:'72030',brokerSymbol:'7203.T',
      verified:true,verifiedAt:now,authority:'DATED_SECURITY_MASTER_AND_MSII',
      mappingProofSha256:hash}]}),
    reservation:write('reservation',{schemaId:'ARK_NO11_EXPLICIT_SHADOW_CASH_RESERVATION_V1',
      maxCashDebit:250000}),
    ledger:path.join(root,'private-ledger.json')
  };
  const ledger=new No11SafetyLedger(args.ledger);
  ledger.verifyTradingSession({session,readAt:now,calendarVerified:true,accountReconciled:true,sourceFresh:true});
  ledger.explicitSafetyReset({humanApproved:true,healthyAccountVerified:true,sourceFresh:true,readAt:now});
  return {root,args,session,now,hash,ledger,cleanup:()=>fs.rmSync(root,{recursive:true,force:true})};
}
test('local RSS probe never upgrades to live readiness from RSS status cells',()=>{
  const f=fixture();try{
    const result=inspect({mode:'probe',snapshot:f.args.snapshot,health:f.args.health});
    assert.equal(result.status,'RSS_STATUS_OBSERVED_READ_ONLY');
    assert.equal(result.liveDataFreshnessCertified,false);
    assert.equal(result.executionAllowed,false);
  }finally{f.cleanup();}
});
test('fully constrained synthetic path stops at locked-only intent inspection',()=>{
  const f=fixture();try{
    // Use EXIT action to avoid time-of-day Entry cutoff dependence.
    const dec=JSON.parse(fs.readFileSync(f.args.decision));dec.intentKind='EXIT';
    dec.side='SELL';dec.positionEffect='CLOSE';dec.stateObserved=false;
    dec.formalState9Primary=null;dec.decisionSha256=digest(Object.fromEntries(Object.entries(dec).filter(([k])=>k!=='decisionSha256')));
    fs.writeFileSync(f.args.decision,JSON.stringify(dec));
    const result=inspect({mode:'prepare-locked',...f.args});
    // SELL with no Ark-owned positions correctly blocks.
    assert.equal(result.status,'BLOCKED');
    assert(result.blockers.includes('SELL_NOT_SUPPORTED_BY_ARK_OWNERSHIP'));
    assert.equal(result.transmissionAllowed,false);
    assert.equal(result.executionAllowed,false);
  }finally{f.cleanup();}
});
test('persistent sell fill prevents same-day new buy through complete preflight',()=>{
  const f=fixture();try{
    const dec=JSON.parse(fs.readFileSync(f.args.decision));
    if(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',
      minute:'2-digit',hourCycle:'h23'}).format(new Date(f.now))>='15:20') {
      // Any later-hour test session is outside the allowed Entry window by design.
      assert.throws(()=>inspect({mode:'prepare-locked',...f.args}),/CASH_ENTRY_CUTOFF_1520/);
      return;
    }
    const before=inspect({mode:'prepare-locked',...f.args});
    assert.equal(before.status,'LOCKED_CANDIDATE_ONLY');
    assert.equal(before.transmitted,false);
    f.ledger.recordBrokerSellFill({
      brokerExecutionId:'RSS-E-1',orderId:'MSII-ORDER-1',side:'SELL',quantity:20,
      session:f.session,executedAt:f.now,source:'MARKETSPEED_II_RSS',
      brokerReconciled:true,verifiedExecution:true,arkManagedPositionMatched:true,
      matchedArkIntentSha256:f.hash
    });
    const after=inspect({mode:'prepare-locked',...f.args});
    assert.equal(after.status,'BLOCKED');
    assert(after.blockers.includes('NO11_AFTER_FIRST_SELL_FILL_BUY_PROHIBITED'));
  }finally{f.cleanup();}
});
test('missing source health file blocks inspection, not synthesized healthy',()=>{
  const f=fixture();try{
    fs.unlinkSync(f.args.health);
    assert.throws(()=>inspect({mode:'probe',...f.args}),/ENOENT/);
  }finally{f.cleanup();}
});
test('private safety ledger bootstrap defaults to kill-switched not production ready',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'no11-safety-bootstrap-'));
  try{
    const x=inspect({mode:'initialize-ledger',ledger:path.join(root,'safety.json')});
    assert.equal(x.killSwitchLatched,true);assert.equal(x.transmitted,false);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
