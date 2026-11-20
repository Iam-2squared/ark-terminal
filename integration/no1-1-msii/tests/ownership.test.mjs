import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {freezeConfirmedOwnership} from '../runtime/freeze_ownership.mjs';
import {runOwnershipTool} from '../tools/no11_ownership_cli.mjs';
import {LOCKED_FLAGS,digest} from '../runtime/locked_intent.mjs';

const clock=()=>new Date().toISOString();
function data(){
  const now=clock();
  const snapshot={schemaId:'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',source:'MARKETSPEED_II_RSS',
    mode:'READ_ONLY',capturedAt:now,captureCompletedAt:now,safety:{...LOCKED_FLAGS},
    positions:[{symbol:'408A',quantity:180}],orders:[],executions:[],buyingPower:300000};
  const health={schemaId:'ARK_MSII_RSS_SOURCE_HEALTH_V1',source:'MARKETSPEED_II_RSS',readOnly:true,
    addinLoaded:true,workbookPersisted:true,rssErrors:0,healthCapturedAt:now,
    actualFeedTimestampCertified:false,feeds:Object.fromEntries(Object.entries({
      capacity:'完了',orders:'配信中',executions:'配信中',positions:'配信中'
    }).map(([k,state])=>[k,{state,observedAt:now}]))};
  return {snapshot,health};
}
const confirm='I_CONFIRM_EACH_POSITION_OWNER';
test('the 408A personal position remains explicit External with frozen hash',()=>{
  const {snapshot,health}=data();
  const output=freezeConfirmedOwnership({snapshot,health,
    confirmedExternal:[{symbol:'408A',quantity:180}],confirmedArkManaged:[],
    explicitUserConfirmation:confirm});
  assert.equal(output.arkManagedPositions.length,0);
  assert.equal(output.externalPositions[0].symbol,'408A.T');
  const {baselineSha256,...core}=output;
  assert.equal(baselineSha256,digest(core));
});
test('never infers personal holding as Ark-managed or all-external',()=>{
  const {snapshot,health}=data();
  assert.throws(()=>freezeConfirmedOwnership({snapshot,health,
    confirmedExternal:[],confirmedArkManaged:[],explicitUserConfirmation:confirm}),
    /BROKER_OWNERSHIP_CLASSIFICATION_MISMATCH/);
  assert.throws(()=>freezeConfirmedOwnership({snapshot,health,
    confirmedExternal:[{symbol:'408A',quantity:180}],confirmedArkManaged:[]}),
    /EXPLICIT_POSITION_OWNERSHIP_CONFIRMATION_REQUIRED/);
});
test('mismatched or overlapping quantities are forbidden',()=>{
  const {snapshot,health}=data();
  assert.throws(()=>freezeConfirmedOwnership({snapshot,health,confirmedExternal:[
    {symbol:'408A',quantity:100}],confirmedArkManaged:[],explicitUserConfirmation:confirm}),
    /BROKER_OWNERSHIP_CLASSIFICATION_MISMATCH/);
  assert.throws(()=>freezeConfirmedOwnership({snapshot,health,confirmedExternal:[
    {symbol:'408A',quantity:180}],confirmedArkManaged:[{symbol:'408A',quantity:100}],
    explicitUserConfirmation:confirm}),/POSITION_OWNER_OVERLAP/);
});
test('a missing open-order clearance blocks baseline capture',()=>{
  const {snapshot,health}=data();
  snapshot.orders.push({orderNumber:'123',status:'配信中'});
  assert.throws(()=>freezeConfirmedOwnership({snapshot,health,
    confirmedExternal:[{symbol:'408A',quantity:180}],confirmedArkManaged:[],
    explicitUserConfirmation:confirm}),/OPEN_ORDERS_BLOCK_BASELINE_FREEZE/);
});
test('the local CLI draft is intentionally UNCLASSIFIED',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'no11-own-'));
  try{
    const {snapshot,health}=data();
    const a=path.join(dir,'account.json'),h=path.join(dir,'health.json'),d=path.join(dir,'draft.json');
    fs.writeFileSync(a,JSON.stringify(snapshot));fs.writeFileSync(h,JSON.stringify(health));
    const draft=runOwnershipTool({mode:'draft',snapshot:a,health:h});
    assert.equal(draft.positions[0].owner,'UNCLASSIFIED');
    fs.writeFileSync(d,JSON.stringify(draft));
    assert.throws(()=>runOwnershipTool({mode:'freeze',snapshot:a,health:h,
      classification:d,confirm}),/UNCLASSIFIED_POSITION_REMAINS/);
    draft.positions[0].owner='EXTERNAL';
    fs.writeFileSync(d,JSON.stringify(draft));
    const baseline=runOwnershipTool({mode:'freeze',snapshot:a,health:h,classification:d,confirm});
    assert.equal(baseline.frozen,true);assert.equal(baseline.arkManagedPositions.length,0);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
