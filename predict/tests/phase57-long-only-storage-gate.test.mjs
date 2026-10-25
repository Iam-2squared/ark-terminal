import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {buildAcquisitionGateSummary,evaluateLongOnlyAcquisitionGate,REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES} from '../long-only/phase57-long-only-acquisition-gate.js';
import {acquireFormalL0Session,acquireFormalL0WarmupDaily} from '../long-only/phase57-long-only-jquants-client.js';
import {buildStoragePurgeDryRun,assertPurgeCompletion,JQUANTS_STORAGE_LIFECYCLE} from '../long-only/phase57-long-only-storage-lifecycle.js';

const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));

test('official storage terms are recorded but public or unspecified cache stays blocked',()=>{
  const gate=evaluateLongOnlyAcquisitionGate(plan);
  assert.equal(plan.preAcquisitionGate.storageDeletionTermsReattested,true);
  assert.equal(JQUANTS_STORAGE_LIFECYCLE.publicRepositoryAllowed,false);
  assert.ok(gate.missing.includes('privateCacheDestinationConfirmed'));
  assert.ok(!gate.missing.includes('postCancellationPurgeMechanismTested'));
});

test('gate summary discloses no credential and plans 411 base requests including causal warmup',()=>{
  const summary=buildAcquisitionGateSummary({plan,allocation,credentialPresent:false});
  assert.equal(summary.sessions,205);assert.deepEqual(summary.requests,{daily:206,datedMaster:205,minute:0,totalBase:411});
  assert.deepEqual(summary.causalWarmup,{sessionDate:'2024-09-09',evaluationPartition:false});
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
    authorizationSha256:'a'.repeat(64),
  };
  let calls=0;
  await assert.rejects(()=>acquireFormalL0Session({plan:authorizedPlan,authorization,partition:'DEVELOPMENT_A',sessionDate:'2024-01-04',apiKey:'fixture',now:'2026-10-06T19:02:00+09:00',fetchImpl:async()=>{calls++;}}),/entitlement ended/);
  assert.equal(calls,0);
});

test('causal warmup is one Daily-only request outside the evaluation partition',async()=>{
  const authorizedPlan=structuredClone(plan);
  authorizedPlan.preAcquisitionGate=Object.fromEntries(REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES.map(key=>[key,true]));
  const planSha256=evaluateLongOnlyAcquisitionGate(authorizedPlan).planSha256;
  const authorization={planSha256,operatorApproved:true,acquisitionPartitions:['DEVELOPMENT_A'],privateCacheRoot:'/private/phase57',authorizationSha256:'a'.repeat(64)};
  let calls=0;
  const result=await acquireFormalL0WarmupDaily({plan:authorizedPlan,authorization,sessionDate:'2024-09-09',apiKey:'fixture',now:'2026-09-15T00:00:00Z',fetchImpl:async()=>{calls++;return {ok:true,status:200,text:async()=>JSON.stringify({data:[{Date:'2024-09-09'}]})};}});
  assert.equal(calls,1);assert.equal(result.evaluationPartition,false);assert.equal(result.masterRequests,0);assert.equal(result.minuteRequests,0);
  await assert.rejects(()=>acquireFormalL0WarmupDaily({plan:authorizedPlan,authorization,sessionDate:'2024-09-06',apiKey:'fixture',fetchImpl:async()=>{calls++;}}),/outside frozen/);
  assert.equal(calls,1);
});

test('Formal L0 workflow reuses repository secret and never uploads plaintext raw cache',()=>{
  const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-long-only-formal-l0.yml',import.meta.url),'utf8');
  assert.match(workflow,/JQUANTS_API_KEY: \$\{\{ secrets\.JQUANTS_API_KEY \}\}/);
  assert.match(workflow,/openssl enc -aes-256-cbc/);
  assert.match(workflow,/rm -rf -- "\$RUNNER_TEMP\/phase57-l0-cache"/);
  assert.doesNotMatch(workflow,/path:\s*\$RUNNER_TEMP\/phase57-l0-cache/);
  assert.match(workflow,/retention-days: 7/);
});

test('L0 replication reuses encrypted cache without another provider acquisition',()=>{
  const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-long-only-l0-replication.yml',import.meta.url),'utf8');
  assert.match(workflow,/actions\/download-artifact@v4/);
  assert.match(workflow,/SOURCE_RUN_ID: 34916384636/);
  assert.match(workflow,/openssl enc -d -aes-256-cbc/);
  assert.match(workflow,/--partition DEVELOPMENT_B/);
  assert.doesNotMatch(workflow,/acquire_phase57_long_only_l0/);
  assert.doesNotMatch(workflow,/equities\/bars\/minute/);
  assert.match(workflow,/retention-days: 21/);
});

test('L1 Minute workflow is limited to fixed first-20 Development A sessions in two checkpoints',()=>{
  const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-long-only-l1-minute-checkpointed-retry.yml',import.meta.url),'utf8');
  const script=fs.readFileSync(new URL('../../scripts/acquire_phase57_long_only_l1_minute.mjs',import.meta.url),'utf8');
  const contract=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-l1-discovery-sessions.json',import.meta.url),'utf8'));
  assert.equal(contract.sessions.length,20);
  assert.deepEqual(contract.sessions,allocation.partitions.DEVELOPMENT_A.slice(0,20));
  assert.equal(contract.sessionListSha256,'96b54f4a6110f7883c063f5896777a4148534c6ba9ecf2b455e6546bfb4ff975');
  assert.equal(contract.selectionUsedMinuteOutcomes,false);
  assert.match(workflow,/--shard-count 2/);
  assert.equal((workflow.match(/request_cap: 150/g)??[]).length,2);
  assert.match(script,/approvedSessions\.length!==20/);
  assert.match(workflow,/set -o pipefail/);
  assert.match(script,/FIRST_20_CALENDAR_ORDERED_SESSIONS_OF_DEVELOPMENT_A/);
  assert.doesNotMatch(script,/DEVELOPMENT_B|VALIDATION|PRIMARY_OOS|CONTINGENCY_OOS|RESERVE/);
  assert.match(workflow,/minute-shard\.tar\.gz\.enc/);
});

test('L2 Minute workflow is limited to frozen Development C+D in four checkpoints',()=>{
  const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-long-only-l2-minute-checkpointed.yml',import.meta.url),'utf8');
  const script=fs.readFileSync(new URL('../../scripts/acquire_phase57_long_only_l2_minute.mjs',import.meta.url),'utf8');
  const contract=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
  assert.equal(contract.sessions.length,40);
  assert.deepEqual(contract.sessions,[...allocation.partitions.DEVELOPMENT_C,...allocation.partitions.DEVELOPMENT_D]);
  assert.equal(contract.sessionListSha256,'9abbc28870b8885cab2b68ae2d2f3e6ef4511b5f687dc553ddcd9e0255b0281c');
  assert.equal(contract.requestHardCeiling,600);
  assert.equal(contract.validationOpened,false);assert.equal(contract.oosOpened,false);
  assert.match(workflow,/--shard-count 4/);
  assert.equal((workflow.match(/request_cap: 150/g)??[]).length,4);
  assert.match(workflow,/max-parallel: 1/);
  assert.match(script,/expected\.length!==40/);
  assert.doesNotMatch(script,/VALIDATION|PRIMARY_OOS|CONTINGENCY_OOS|RESERVE/);
  assert.match(workflow,/minute-shard\.tar\.gz\.enc/);
});
