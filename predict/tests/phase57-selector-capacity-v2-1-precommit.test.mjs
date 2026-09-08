import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const research=new URL('../research/',import.meta.url);
const read=name=>JSON.parse(fs.readFileSync(new URL(name,research),'utf8'));
const sha256=value=>createHash('sha256').update(value).digest('hex');

test('Capacity v2 terminal evidence records one failed gate and keeps OOS sealed',()=>{
  const report=read('phase57-selector-capacity-v2-validation-no-go.json');
  assert.equal(report.status,'CAPACITY_V2_FINAL_NO_GO');
  assert.deepEqual(Object.entries(report.validation.gates).filter(([,pass])=>!pass).map(([name])=>name),['utilityNonInferior']);
  assert.equal(report.validation.metrics.utilityDifferenceBps,-13.701722);
  assert.equal(report.validation.metrics.marginMissBps,-3.701722);
  assert.equal(report.researchDecision.untouchedOosReleased,false);
});

test('Capacity v2.1 precommit quarantines old OOS and allocates new chronological gates',()=>{
  const spec=read('phase57-selector-capacity-v2-1-precommit.json');
  assert.equal(spec.developmentDataset.sessionCount,89);
  assert.equal(spec.developmentDataset.originalUntouchedOos92To120Role,'QUARANTINED_NOT_OPENED_NOT_REUSED');
  assert.deepEqual(spec.newFreshEvaluationAllocation.freshValidationOrdinals,[121,149]);
  assert.equal(spec.newFreshEvaluationAllocation.purgeValidationOosOrdinal,150);
  assert.deepEqual(spec.newFreshEvaluationAllocation.freshUntouchedOosOrdinals,[151,179]);
  assert.equal(spec.newFreshEvaluationAllocation.reserveRemainingSessions,103);
  assert.equal(spec.releasePolicy.releaseFreshOosOnlyAfterFreshValidationPass,true);
});

test('Capacity v2.1 makes candidate count a constraint and prioritizes held-out utility',()=>{
  const spec=read('phase57-selector-capacity-v2-1-precommit.json');
  assert.equal(spec.mappingSelectionContract.candidateCountIsConstraintNotPrimaryObjective,true);
  assert.equal(spec.mappingSelectionContract.lexicographicObjective[0],'MAXIMIZE_WORST_HELD_OUT_FOLD_UTILITY_DIFFERENCE_BPS');
  assert.equal(spec.outOfFoldContract.thresholdSelectionUsesOnlyHeldOutPredictions,true);
  assert.equal(spec.mappingSelectionContract.eligibleFoldGate.minimumUtilityDifferenceBpsInEveryHeldOutFold,-10);
});

test('Capacity v2.1 preserves all research and trading safety locks',()=>{
  const spec=read('phase57-selector-capacity-v2-1-precommit.json');
  assert.ok(Object.values(spec.safety).every(value=>value===false));
  assert.equal(spec.guards.mainChangeAllowed,false);
  assert.equal(spec.guards.laneYChangeAllowed,false);
  assert.equal(spec.releasePolicy.automaticPromotion,false);
});

test('Capacity v2 evidence and v2.1 precommit bytes match sidecars',()=>{
  for(const name of ['phase57-selector-capacity-v2-validation-no-go.json','phase57-selector-capacity-v2-1-precommit.json']){
    const bytes=fs.readFileSync(new URL(name,research));
    const expected=fs.readFileSync(new URL(`${name}.sha256`,research),'utf8').trim().split(/\s+/)[0];
    assert.equal(sha256(bytes),expected);
  }
});
