import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const audit=JSON.parse(fs.readFileSync(new URL('../../predict/research/phase57-exit-v4-jquants-data-capacity-audit-v1.json',import.meta.url),'utf8'));

test('EXIT v4 J-Quants audit stops before outcomes and allocation',()=>{
  assert.equal(audit.scope,'DATA_CAPACITY_QUALITY_AND_CONSERVATION_ONLY');
  assert.equal(audit.performanceMeasurementAuthorized,false);
  assert.equal(audit.newOutcomeAccess,0);
  assert.equal(audit.newProtectedAccess,0);
  assert.equal(audit.sequentialUnlock.currentStage,0);
  assert.equal(audit.sequentialUnlock.allocationFrozen,false);
  assert.equal(audit.sequentialUnlock.developmentUnlocked,false);
  assert.equal(audit.sequentialUnlock.validationUnlocked,false);
  assert.equal(audit.sequentialUnlock.untouchedOosUnlocked,false);
});

test('post-cancellation raw archive is forbidden and deletion is explicit',()=>{
  assert.equal(audit.contract.permanentRawArchivePermittedAfterCancellation,false);
  assert.match(audit.contract.postCancellation,/DELETE_RAW/);
  assert.equal(audit.qualityAudit.find(row=>row.item==='RAW_ARCHIVE_AFTER_CANCELLATION')?.status,'FAIL');
  assert.ok(audit.requiredBeforeAllocationFreeze.includes('DEFINE_CANCELLATION_DELETION_LEDGER_AND_DELETE_BY_2026_10_06'));
});

test('capacity checkpoints are arithmetically conservative',()=>{
  for(const [events,required] of Object.entries(audit.entryCapacity.requiredSessions)){
    for(const scenario of ['conservative','base','optimistic']){
      const rate=audit.entryCapacity.scenarios[scenario].firstEnterPerSession;
      assert.equal(required[scenario],Math.ceil(Number(events)/rate));
    }
  }
  assert.equal(audit.entryCapacity.scenarios.optimistic.firstEnterPerSession<=audit.entryCapacity.knownHistoricalDiagnosticFirstEnterPerSession,true);
  assert.match(audit.entryCapacity.checkpointFeasibility['2000'],/^NOT_FEASIBLE/);
});

test('critical unresolved quality items fail closed',()=>{
  const status=Object.fromEntries(audit.qualityAudit.map(row=>[row.item,row.status]));
  for(const key of ['TIMESTAMP_BOUNDARY','AVAILABLE_AT','MISSING_PROVIDER_CLASSIFICATION','ADJUSTMENT','CORPORATE_ACTIONS','RAW_ARCHIVE_AFTER_CANCELLATION']){
    assert.equal(status[key],'FAIL');
  }
  assert.equal(audit.fiveMinuteContract.status,'NOT_FROZEN_TIMESTAMP_PROOF_REQUIRED');
  assert.equal(audit.datasetClassification.FULL_REPLAY_ELIGIBLE.confirmedSessions,0);
});

test('all execution and promotion safety flags remain false',()=>{
  assert.deepEqual(Object.values(audit.safety),Array(Object.keys(audit.safety).length).fill(false));
});
