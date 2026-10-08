import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const bytes=readFileSync(new URL('../../predict/research/phase57-entry-protected190-cross-research-2026-09-09.json',import.meta.url));
const m=JSON.parse(bytes);
test('immutable metadata fingerprint',()=>assert.equal(createHash('sha256').update(bytes).digest('hex'),'0fc974b527244dfdab069a9bab69b17f6f6cfe22839ef8d5c471416a83087a02'));
test('190 identities remain unknown and protected, not clean',()=>{
  assert.equal(new Set(m.protectedSessionIds).size,190);
  assert.deepEqual(m.unknownGovernanceSessionIds,m.protectedSessionIds);
  assert.deepEqual([m.classification.confirmedClean,m.classification.confirmedExposed,m.classification.unknown],[0,0,190]);
  assert.equal(m.priorityConservationSessionIds.length,103);
});
test('structural admission is not performance exposure or a blanket negative',()=>{
  const rows=m.crossResearchExposureSummary;
  assert.deepEqual(rows.map(r=>r.sessions),[29,29,29,103]);
  assert.equal(rows.filter(r=>r.SelectorCapacity.STRUCTURE_AUDITED==='YES_ATTESTED').reduce((n,r)=>n+r.sessions,0),58);
  for(const r of rows){
    for(const line of ['Entry','EXIT','CapitalAllocation'])assert.ok(Object.values(r[line]).every(v=>v==='UNKNOWN'));
    assert.equal(r.SelectorCapacity.FUTURE_LABEL,'UNKNOWN');
    assert.equal(r.SelectorCapacity.MARKET_DATA,'UNKNOWN');
    assert.equal(r.negativeAttestationComplete,false);
  }
});
test('no guessed calendar, no purge consumption',()=>{
  assert.equal(m.mapping.knownCount,2);assert.equal(m.mapping.unknownCount,280);
  assert.equal(m.mapping.protectedKnownCount,1);assert.equal(m.mapping.protectedUnknownCount,189);
  assert.equal(m.mapping.calendarInferred,false);
  assert.equal(m.purgeSessionIds.length,3);
  assert.ok(m.purgeSessionIds.every(id=>!m.protectedSessionIds.includes(id)));
});
test('allocation and measurement fail closed with complete field contract',()=>{
  for(const k of ['developmentSessionIds','validationSessionIds','untouchedOosSessionIds','excludedSessionIds'])assert.deepEqual(m[k],[]);
  for(const k of ['allocationFreezeComplete','releaseAllowed','baselineMeasurementAllowed','newEntryFittingAllowed','automaticReallocationAllowed','resultBasedReallocationAllowed'])assert.equal(m[k],false);
  assert.equal(m.baselineDiagnostic.measuredSessions,0);assert.equal(m.baselineDiagnostic.sessionCount,17);
  assert.equal(m.outcomesViewedAtCreation,false);assert.equal(m.sealedAtCreation,true);
  assert.equal(m.additionalMetadataQuestions.length,6);
});
test('run listings and artifact identities never prove global cleanliness',()=>{
  assert.deepEqual(m.workflowRunCoverage.map(x=>x.returned),[97,6,86]);
  assert.ok(m.workflowRunCoverage.every(x=>x.globalAccessLedgerComplete===false));
  assert.ok(m.artifactMetadata.some(x=>x.runId===31785422471));
  assert.ok(m.artifactMetadata.some(x=>x.runId===33943395885));
  assert.ok(m.artifactMetadata.every(x=>x.artifacts.every(a=>a.digest.startsWith('sha256:'))));
});
test('no new content, outcomes, performance or unsafe actions',()=>{
  for(const k of ['sealedContentNewlyOpened','newOutcomesViewed','newPerformanceComputed','mainChanged'])assert.equal(m.audit[k],false);
  for(const k of ['sealedSessionsOpened','outcomeSessionsViewed','performanceSessions','modelRuns'])assert.equal(m.audit[k],0);
  assert.equal(Object.keys(m.safety).length,9);assert.ok(Object.values(m.safety).every(v=>v===false));
});
