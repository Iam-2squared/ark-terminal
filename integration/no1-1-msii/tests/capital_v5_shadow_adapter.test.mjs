import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {prepareNo11SyntheticCapitalV5} from '../runtime/capital_v5_shadow_adapter.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';

const here=path.dirname(fileURLToPath(import.meta.url));
const runner=path.resolve(here,'../tools/no11_capital_v5_shadow.py');
function fixture() {
  const now=new Date().toISOString();
  const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    source:'MARKETSPEED_II_RSS',mode:'READ_ONLY',
    capturedAt:now,captureCompletedAt:now,
    positions:[{symbol:'408A',quantity:180,marketValue:300000}],
    orders:[],executions:[],buyingPower:700000,safety:{...LOCKED_FLAGS}};
  const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',
    readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,
    healthCapturedAt:now,actualFeedTimestampCertified:false,
    feeds:Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',
      executions:'配信中',positions:'配信中'})
      .map(([name,state])=>[name,{state,observedAt:now}]))};
  const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',
    source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
    capturedAt:now,frozen:true,
    externalPositions:[{symbol:'408A.T',quantity:180}],arkManagedPositions:[]};
  const ownership={...core,baselineSha256:digest(core)};
  const batch={schemaId:'ARK_NO11_SYNTHETIC_FROZEN_V5_BATCH_V1',
    evidenceMode:'SYNTHETIC_OFFLINE_ONLY',sessionVerified:false,
    afterFirstLegalSellFill:false,pendingBrokerOrders:false,minute:600,
    existingBands:[],preorderedCandidates:[{entry_id:'synthetic-S',brokerSymbol:'6758.T',
      rank:'S',ML:2.5,capital_score:2.2,raw_reference:'1000',block:'1'}],
    syntheticTrainingTables:{'1':{minute_counts:{'600':[1,0,2]},
      training_session_N:10,B_median:1.3,B_p75:1.4,
      minute_bucket:{'600':'unit'}}}};
  return {snapshot,health,ownership,batch,now:new Date(now)};
}
function runPython(request){
  const windows=process.platform==='win32';
  const r=spawnSync(windows?'py':'python3',windows?['-3',runner]:[runner],
    {encoding:'utf8',input:JSON.stringify(request),timeout:10000});
  assert.equal(r.status,0,'Frozen v5 synthetic bridge failed: '+r.stdout+' '+r.stderr);
  return JSON.parse(r.stdout);
}

test('real broker RSS preview funding composes into exact Frozen Capital v5 synthetic adapter',()=>{
  const f=fixture(), preview=prepareNo11SyntheticCapitalV5(f);
  assert.equal(preview.status,'SYNTHETIC_SHADOW_REQUEST_ONLY');
  assert.deepEqual(preview.request.arkCapitalInputs,
    {cash:700000,equity:700000,exposure:0});
  assert.deepEqual(preview.request.externalSymbols,['408A.T']);
  const result=runPython(preview.request);
  assert.equal(result.status,'SYNTHETIC_SHADOW_ONLY');
  assert.equal(result.allocatedDebitJpy,'300150.0000');
  assert.equal(result.allocations[0].quantity,300);
  assert.equal(result.orderAllowed,false);
  assert.equal(result.transmitted,false);
});

test('personal holding price change never changes the Ark Capital inputs',()=>{
  const f=fixture(); f.snapshot.positions[0].marketValue=999999;
  const projected=prepareNo11SyntheticCapitalV5(f);
  assert.deepEqual(projected.request.arkCapitalInputs,
    {cash:700000,equity:700000,exposure:0});
});

test('personal holding symbol is blocked by exact Frozen Capital intake',()=>{
  const f=fixture();f.batch.preorderedCandidates[0].brokerSymbol='408A.T';
  const projected=prepareNo11SyntheticCapitalV5(f);
  assert.equal(projected.status,'SYNTHETIC_SHADOW_REQUEST_ONLY');
  const windows=process.platform==='win32';
  const result=spawnSync(windows?'py':'python3',windows?['-3',runner]:[runner],
    {encoding:'utf8',input:JSON.stringify(projected.request),timeout:10000});
  assert.equal(result.status,2);
  assert.match(result.stdout,/PERSONAL_SYMBOL_BUY_PROHIBITED/);
  assert.doesNotMatch(result.stdout,/"orderAllowed": true/);
});

test('an unconfirmed snapshot status or missing ownership blocks before funding',()=>{
  const f=fixture(); f.health.feeds.positions.state='接続待ち';
  const projected=prepareNo11SyntheticCapitalV5(f);
  assert.equal(projected.status,'BLOCKED');
  assert.equal(projected.orderAllowed,false);
  const g=fixture();g.ownership.externalPositions=[];
  assert.equal(prepareNo11SyntheticCapitalV5(g).status,'BLOCKED');
});

test('broker orders and stale snapshot block before Python is invoked',()=>{
  const f=fixture(); f.snapshot.orders=[{orderNumber:'pending-1'}];
  assert.equal(prepareNo11SyntheticCapitalV5(f).status,'BLOCKED');
  const g=fixture();g.now=new Date(Date.now()+60000);
  assert.equal(prepareNo11SyntheticCapitalV5(g).status,'BLOCKED');
});

test('no live source admission or SELL-fill override is created by the bridge',()=>{
  const f=fixture();f.batch.evidenceMode='LIVE_ATTESTED';
  assert.equal(prepareNo11SyntheticCapitalV5(f).status,'BLOCKED');
  const g=fixture();g.batch.afterFirstLegalSellFill=true;
  assert.equal(prepareNo11SyntheticCapitalV5(g).status,'BLOCKED');
});
