import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {buildLongOnlyAcquisitionDryRun} from '../long-only/phase57-long-only-acquisition-dry-run.js';

const loadPlan=()=>JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));

test('dry-run plans all 205 historical sessions without authorizing acquisition',()=>{
  const result=buildLongOnlyAcquisitionDryRun(loadPlan());
  assert.equal(result.mode,'DRY_RUN_ZERO_NETWORK');
  assert.equal(result.acquisitionMayStart,false);
  assert.equal(result.historicalSessions,205);
  assert.equal(result.requests.daily,205);
  assert.equal(result.requests.master,205);
  assert.equal(result.requests.minutePages,0);
  assert.equal(result.requests.total,410);
  assert.equal(result.selectorOnlyConsumptionProhibited,true);
  assert.deepEqual(result.integratedReuse,['SELECTOR','ENTRY','EXIT','ALLOCATION','PORTFOLIO_REPLAY']);
  assert.ok(result.missingGates.includes('storageDeletionTermsReattested'));
  assert.ok(result.missingGates.includes('freshExactDatesFrozen'));
  assert.ok(result.missingGates.includes('operatorExplicitAcquisitionApproval'));
  assert.match(result.dryRunSha256,/^[a-f0-9]{64}$/);
});

test('minute planning is bounded by Development envelope and still performs zero network calls',()=>{
  const result=buildLongOnlyAcquisitionDryRun(loadPlan(),{includeMinute:true,minuteSessions:20});
  assert.equal(result.mode,'DRY_RUN_ZERO_NETWORK');
  assert.equal(result.minute.requested,true);
  assert.equal(result.minute.sessions,20);
  assert.ok(result.requests.minutePages>0);
  assert.equal(result.acquisitionMayStart,false);
  assert.throws(()=>buildLongOnlyAcquisitionDryRun(loadPlan(),{includeMinute:true,minuteSessions:81}),/may not exceed/);
});
