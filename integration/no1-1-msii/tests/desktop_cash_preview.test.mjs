import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {check} from '../tools/no11_desktop_cash_preview.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
function input(){
  const now=new Date().toISOString();
  const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    capturedAt:now,captureCompletedAt:now,source:'MARKETSPEED_II_RSS',
    mode:'READ_ONLY',positions:[{symbol:'408A',quantity:180,marketValue:300000}],
    orders:[],executions:[],buyingPower:700000,safety:{...LOCKED_FLAGS}};
  const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',
    readOnly:true,addinLoaded:true,workbookPersisted:true,rssErrors:0,healthCapturedAt:now,
    actualFeedTimestampCertified:false,
    feeds:Object.fromEntries(Object.entries({capacity:'完了',orders:'配信中',
      executions:'配信中',positions:'配信中'})
      .map(([key,state])=>[key,{state,observedAt:now}]))};
  const core={schemaId:'ARK_CASH_OWNERSHIP_BASELINE_V1',frozen:true,
    capturedAt:now,source:'MARKETSPEED_II_RSS_EXPLICIT_OWNER_CONFIRMED',
    externalPositions:[{symbol:'408A.T',quantity:180}],arkManagedPositions:[]};
  return {snapshot,health,ownership:{...core,baselineSha256:digest(core)},now:new Date(now)};
}
test('full cash plus explicit personal ownership becomes shadow preview, never live',()=>{
  const x=check(input());
  assert.equal(x.status,'READ_ONLY_CAPITAL_PREVIEW');
  assert.deepEqual(x.arkCapitalInputs,{cash:700000,equity:700000,exposure:0});
  for(const key of ['liveFeedCertified','liveDecisionCertified',
    'liveOrderReconciliationCertified','productionReady','orderTransmission']){
    assert.equal(x[key],false);
  }
});
test('personal market price changes do not inflate Ark equity',()=>{
  const x=input();x.snapshot.positions[0].marketValue=900000;
  assert.equal(check(x).arkCapitalInputs.equity,700000);
});
test('mismatched personal holdings or private ownership checksum fails',()=>{
  const x=input();x.snapshot.positions[0].quantity=100;
  assert.equal(check(x).status,'BLOCKED');
  const y=input();y.ownership.baselineSha256='0'.repeat(64);
  assert.equal(check(y).status,'BLOCKED');
});
test('unverified or pending broker orders block cash usage',()=>{
  const x=input();x.snapshot.orders.push({orderNumber:'test'});
  assert.equal(check(x).status,'BLOCKED');
  const y=input();y.health.feeds.positions.state='接続待ち';
  assert.equal(check(y).status,'BLOCKED');
});
test('stale observation is never automatically certified',()=>{
  const x=input();x.now=new Date(Date.now()+120000);
  assert.equal(check(x).status,'BLOCKED');
});
test('desktop launcher cannot create/save sheets or call broker orders',()=>{
  const text=fs.readFileSync(path.join(here,'../windows/Start-No11DesktopReadOnly.ps1'),'utf8');
  assert(text.includes('Ark_No11_MSII_RSS.xlsx'));
  assert(text.includes('Ark-No11-CaptureReadOnly-v2.ps1'));
  assert(text.includes('0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C'));
  assert.doesNotMatch(text,/Workbooks\s*\.\s*(?:Add|Open)\s*\(/i);
  assert.doesNotMatch(text,/\.\s*(?:Save|SaveAs|RegisterXLL)\s*\(/i);
  assert.doesNotMatch(text,/\.Formula\s*=/);
  assert.doesNotMatch(text,/\bRssStockOrder\s*\(/i);
  assert(text.includes('ORDER_TRANSMISSION=False'));
});
