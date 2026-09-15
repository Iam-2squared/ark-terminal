import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyOfflineProvenance,offlineCoverageStatus} from '../lib/phase57-offline-provenance.mjs';
import {FREEZE,SAFETY,digest} from '../lib/phase57-offline-parity.mjs';
const bytes=Buffer.from('synthetic metadata test; no market observations');
const source=(kind='COMPLETED_INPUT')=>({id:'a',kind,sha256:'a'.repeat(64),availableAt:'2026-08-13T00:05:00Z',completedAt:'2026-08-13T00:05:00Z',effectiveAt:'2026-08-12T00:00:00Z',sessionDate:'2026-08-12',fullyRealizedAt:'2026-08-12T06:30:00Z'});
const manifest=()=>({mode:'USED_FIXTURE_METADATA_ONLY',freezeSha256:FREEZE,safety:SAFETY,inputSha256:digest(bytes),sessionDate:'2026-08-13',decisionTimestamp:'2026-08-13T00:10:00Z',sources:[source()]});
test('metadata checks never claim strategy or real-source coverage',()=>{
  for(const kind of ['STATIC_PIT','COMPLETED_INPUT','REALIZED_ANALOG']){const m=manifest();m.sources=[source(kind)];const r=verifyOfflineProvenance(m,bytes);assert.equal(r.status,'OFFLINE_METADATA_CHECK_PASS');assert.equal(r.readyForRealtime,false);assert.equal(r.contentSemanticsVerified,false);assert.equal(r.analogSupportVerified,false);}
});
test('wrong identity, reserved input and non-offline mode are rejected',()=>{
  for(const mutation of [{inputSha256:'b'.repeat(64)},{freezeSha256:'b'.repeat(64)},{mode:'REALTIME'},{sessionDate:'2026-09-10'},{sessionDate:'2026-10-22'},{sessionDate:'2026-02-30'},{safety:{...SAFETY,transmitted:true}}])assert.throws(()=>verifyOfflineProvenance({...manifest(),...mutation},bytes));
});
test('missing, duplicate, future and forming inputs are rejected',()=>{
  for(const sources of [[],[source(),source()],[{...source(),availableAt:'2026-08-13T00:15:00Z'}],[{...source(),completedAt:'2026-08-13T00:06:00Z'}],[{...source('STATIC_PIT'),effectiveAt:'2026-08-14T00:00:00Z'}]])assert.throws(()=>verifyOfflineProvenance({...manifest(),sources},bytes));
});
test('strict analog causality rejects equal timestamps and future session labels',()=>{
  for(const mutation of [{sessionDate:'2026-08-13'},{fullyRealizedAt:'2026-08-13T00:10:00Z'},{fullyRealizedAt:'2026-08-13T00:09:00Z'}])assert.throws(()=>verifyOfflineProvenance({...manifest(),sources:[{...source('REALIZED_ANALOG'),...mutation}]},bytes));
});
test('coverage requires explicit upstream gates and never unlocks realtime',()=>{
  const checks=Object.fromEntries(['sourceIdentity','completedBarMeaning','fullUniversePit','selectorSameInputParity','analogPoolIdentity','analogCausalityAndSupport','v4SameInputParity','downstreamSameInputParity'].map(k=>[k,'PASS']));
  assert.equal(offlineCoverageStatus(checks).readyForRealtime,false);
  const partial=offlineCoverageStatus({...checks,analogPoolIdentity:'NOT_MEASURED',fullUniversePit:'NOT_MEASURED'});assert.deepEqual(partial.missing,['fullUniversePit','analogPoolIdentity']);assert.throws(()=>offlineCoverageStatus({downstreamSameInputParity:'PASS'}));
});
