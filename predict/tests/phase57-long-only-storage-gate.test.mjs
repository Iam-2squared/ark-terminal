import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {buildAcquisitionGateSummary,evaluateLongOnlyAcquisitionGate,REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES} from '../long-only/phase57-long-only-acquisition-gate.js';
import {acquireFormalL0Session} from '../long-only/phase57-long-only-jquants-client.js';
import {buildStoragePurgeDryRun,assertPurgeCompletion,JQUANTS_STORAGE_LIFECYCLE} from '../long-only/phase57-long-only-storage-lifecycle.js';

const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));

test('official storage terms are recorded but public or unspecified cache stays blocked',()=>{
  const gate=evaluateLongOnlyAcquisitionGate(plan);
  assert.equal(plan.preAcquisitionGate.storageDeletionTermsReattested,true);
  assert.equal(JQUANTS_STORAGE_LIFECYCLE.publicRepositoryAllowed,false);
  assert.ok(gate.missing.includes('privateCacheDestinationConfirmed'));
  assert.ok(gate.missing.includes('postCancellationPurgeMechanismTested'));
});

test('gate summary discloses no credential and plans exactly 410 base requests',()=>{
  const summary=buildAcquisitionGateSummary({plan,allocation,credentialPresent:false});
  assert.equal(summary.sessions,205);assert.deepEqual(summary.requests,{daily:205,datedMaster:205,minute:0,totalBase:410});
  assert.equal(summary.credential.present,false);assert.equal(summary.credential.valueObserved,false);assert.equal(summary.acquisitionMayStart,false);
});

test('storage purge dry-run covers raw and reversible data with separate deadlines',()=>{
  const dryRun=buildStoragePurgeDryRun({cacheManifest:{privateUserOnly:true,publiclyAccessible:false,objects:[
    {objectId:'daily-1',relativePath:'raw/daily-1.json',dataClass:'DAILY',sha256:'a'.repeat(64)},
    {objectId:'minute-1',relativePath:'raw/minute-1.json',dataClass:'MINUTE',sha256:'b'.repeat(64)},
    {objectId:'bars5m-1',relativePath:'derived/bars5m-1.json',dataClass:'CAUSAL_5M',sha256:'c'.repeat(64)},
  ]}});
  assert.equal(dryRun.automaticDeletionPerformed,false);assert.equal(dryRun.objects[0].deadlineJst,'2026-10-06T19:02:00+09:00');assert.equal(dryRun.objects[1].deadlineJst,'2026-10-06T19:07:00+09:00');
  const completion=assertPurgeCompletion({dryRun,completion:{dryRunSha256:dryRun.dryRunSha256,tombstones:dryRun.objects.map(x=>({objectId:x.objectId,deletedEvidenceSha256:'d'.repeat(64)}))}});
  assert.equal(completion.rawOrReversibleDataRetained,0);
  assert.throws(()=>buildStoragePurgeDryRun({cacheManifest:{privateUserOnly:false,objects:[]}}),/not confirmed private/);
});

test('formal acquisition is fail-closed after entitlement end before network',async()=>{
  const authorizedPlan=structuredClone(plan);
  authorizedPlan.preAcquisitionGate=Object.fromEntries(REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES.map(key=>[key,true]));
  const planSha256=evaluateLongOnlyAcquisitionGate(authorizedPlan).planSha256;
  const authorization={
    planSha256,operatorApproved:true,acquisitionPartitions:['DEVELOPMENT_A'],privateCacheRoot:'/private/phase57',
    authorizationSha256:'a'.repeat(64),cacheManifestSha256:'b'.repeat(64),purgeDryRunSha256:'c'.repeat(64),
  };
  let calls=0;
  await assert.rejects(()=>acquireFormalL0Session({plan:authorizedPlan,authorization,partition:'DEVELOPMENT_A',sessionDate:'2024-01-04',apiKey:'fixture',now:'2026-10-06T19:02:00+09:00',fetchImpl:async()=>{calls++;}}),/entitlement ended/);
  assert.equal(calls,0);
});
