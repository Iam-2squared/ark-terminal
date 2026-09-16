import assert from 'node:assert/strict';
import {digest,exposedDate,instant,jstDate,FREEZE,SAFETY} from './phase57-offline-parity.mjs';

const sha=x=>assert.match(x,/^[a-f0-9]{64}$/,'SHA256_REQUIRED');
const date=x=>{
  assert.match(x,/^\d{4}-\d{2}-\d{2}$/,'DATE_REQUIRED');
  assert.equal(new Date(x+'T00:00:00Z').toISOString().slice(0,10),x,'INVALID_CALENDAR_DATE');
};

/** Pure offline metadata validation. Does not acquire data or invoke a strategy. */
export function verifyOfflineProvenance(manifest,bytes){
  assert.equal(manifest.mode,'USED_FIXTURE_METADATA_ONLY','REAL_SOURCE_NOT_ADMITTED');
  assert.equal(manifest.freezeSha256,FREEZE,'FREEZE_MISMATCH');
  assert.deepEqual(manifest.safety,SAFETY,'SAFETY_MISMATCH');
  sha(manifest.inputSha256);assert.equal(digest(bytes),manifest.inputSha256,'INPUT_HASH_MISMATCH');
  date(manifest.sessionDate);exposedDate(manifest.sessionDate);
  const decision=instant(manifest.decisionTimestamp);
  assert.equal(jstDate(manifest.decisionTimestamp),manifest.sessionDate,'SESSION_TIMESTAMP_MISMATCH');
  assert.ok(Array.isArray(manifest.sources)&&manifest.sources.length>0,'SOURCE_RECORDS_REQUIRED');
  const seen=new Set();
  for(const source of manifest.sources){
    assert.ok(typeof source.id==='string'&&source.id.length>0&&!seen.has(source.id),'DUPLICATE_OR_MISSING_SOURCE_ID');seen.add(source.id);
    sha(source.sha256);
    assert.ok(instant(source.availableAt)<=decision,'FUTURE_AVAILABLE_SOURCE');
    assert.ok(['STATIC_PIT','COMPLETED_INPUT','REALIZED_ANALOG'].includes(source.kind),'UNDECLARED_SOURCE_KIND');
    if(source.kind==='STATIC_PIT')assert.ok(instant(source.effectiveAt)<=decision,'FUTURE_EFFECTIVE_METADATA');
    if(source.kind==='COMPLETED_INPUT')assert.ok(instant(source.completedAt)<=instant(source.availableAt),'FORMING_INPUT');
    if(source.kind==='REALIZED_ANALOG'){
      date(source.sessionDate);
      assert.ok(source.sessionDate<manifest.sessionDate,'SAME_OR_FUTURE_SESSION_ANALOG');
      assert.ok(instant(source.fullyRealizedAt)<decision,'NOT_YET_REALIZED_ANALOG');
      assert.ok(instant(source.fullyRealizedAt)<=instant(source.availableAt),'LABEL_NOT_AVAILABLE');
    }
  }
  return {status:'OFFLINE_METADATA_CHECK_PASS',sources:seen.size,inputSha256:manifest.inputSha256,
    contentSemanticsVerified:false,analogSupportVerified:false,selectorCoverageVerified:false,
    strategyEvaluated:false,readyForRealtime:false,safety:SAFETY};
}

/** Admission evidence cannot be promoted by checking hashes alone. */
export function offlineCoverageStatus(checks){
  const gates=['sourceIdentity','completedBarMeaning','fullUniversePit','selectorSameInputParity','analogPoolIdentity','analogCausalityAndSupport','v4SameInputParity','downstreamSameInputParity'];
  assert.deepEqual(Object.keys(checks).sort(),[...gates].sort(),'EXPLICIT_COVERAGE_GATES_REQUIRED');
  for(const value of Object.values(checks))assert.ok(['PASS','FAIL','NOT_MEASURED'].includes(value),'INVALID_GATE_STATUS');
  const missing=gates.filter(k=>checks[k]!=='PASS');
  return {classification:missing.length?'PARTIAL_OFFLINE_COVERAGE':'OFFLINE_SAME_INPUT_COVERAGE',missing,
    realSourceVerified:false,readyForRealtime:false,automaticPromotionAllowed:false};
}
