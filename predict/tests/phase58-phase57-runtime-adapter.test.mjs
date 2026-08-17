import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFrozenPhase57SnapshotFromRuntimeDecision,
  buildProspectivePhase57Phase58Record,
} from '../scalping/phase58-phase57-runtime-adapter.js';

const HASH='a'.repeat(64);
const baseDecision=Object.freeze({
  direction:'LONG',
  confidence:0.72,
  setup:'Q4_HIGH_TREND_CONTINUATION',
  context:{session:'AM'},
  asOf:'2026-08-17T00:01:00.000Z',
  frozenByPhase57:true,
  pointInTimeOnly:true,
  futureOutcomeUsed:false,
  thresholdSearchAfterCapture:false,
  entryRetunedAfterCapture:false,
});

test('builds canonical snapshot only from explicit frozen point-in-time Phase57 decision',()=>{
  const out=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:baseDecision,modelId:'phase57-fixed-horizon-v1',artifactSha256:HASH});
  assert.equal(out.complete,true);
  assert.equal(out.snapshot.direction,1);
  assert.equal(out.snapshot.frozen,true);
  assert.equal(out.snapshot.futureOutcomeUsed,false);
  assert.equal(out.snapshot.modelId,'phase57-fixed-horizon-v1');
  assert.equal(out.snapshot.artifactSha256,HASH);
});

test('blocks historical realized rows instead of reconstructing a Phase57 decision',()=>{
  const out=buildFrozenPhase57SnapshotFromRuntimeDecision({
    decision:{...baseDecision,netReturnPct:1.2,futureBars:[{close:101}]},
    modelId:'phase57-fixed-horizon-v1',artifactSha256:HASH,
  });
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('OUTCOME_FIELDS_PRESENT_IN_PHASE57_RUNTIME_DECISION'));
  assert.deepEqual([...out.forbiddenOutcomeFields].sort(),['futureBars','netReturnPct']);
});

test('blocks missing provenance and anti-retune guards',()=>{
  const {frozenByPhase57,thresholdSearchAfterCapture,...unsafe}=baseDecision;
  const out=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:unsafe,modelId:'',artifactSha256:'bad'});
  assert.equal(out.complete,false);
  assert.ok(out.blockers.includes('RUNTIME_DECISION_NOT_EXPLICITLY_FROZEN_BY_PHASE57'));
  assert.ok(out.blockers.includes('PHASE57_POST_CAPTURE_SEARCH_GUARD_MISSING'));
  assert.ok(out.blockers.includes('MISSING_PHASE57_MODEL_ID'));
  assert.ok(out.blockers.includes('INVALID_PHASE57_ARTIFACT_SHA256'));
});

test('synchronizes Phase57 and Phase58 prospectively when timestamps are causal',()=>{
  const out=buildProspectivePhase57Phase58Record({
    decision:baseDecision,
    modelId:'phase57-fixed-horizon-v1',
    artifactSha256:HASH,
    capturedAt:'2026-08-17T00:03:00.000Z',
    microstructure:{orderBook:{ready:true},tickFlow:{ready:true}},
  });
  assert.equal(out.complete,true);
  assert.equal(out.synchronized.phase57.direction,1);
  assert.equal(out.synchronized.methodology.phase58MayReverseDirection,false);
});

test('blocks future or stale Phase57 snapshots at synchronization boundary',()=>{
  const future=buildProspectivePhase57Phase58Record({
    decision:{...baseDecision,asOf:'2026-08-17T00:04:00.000Z'},
    modelId:'phase57-fixed-horizon-v1',artifactSha256:HASH,capturedAt:'2026-08-17T00:03:00.000Z',microstructure:{},
  });
  assert.equal(future.complete,false);
  assert.ok(future.synchronized.validation.blockers.includes('PHASE57_FUTURE_TIMESTAMP'));

  const stale=buildProspectivePhase57Phase58Record({
    decision:{...baseDecision,asOf:'2026-08-16T23:55:00.000Z'},
    modelId:'phase57-fixed-horizon-v1',artifactSha256:HASH,capturedAt:'2026-08-17T00:03:00.000Z',microstructure:{},
  });
  assert.equal(stale.complete,false);
  assert.ok(stale.synchronized.validation.blockers.includes('STALE_PHASE57_SNAPSHOT'));
});

test('all exposed safety write flags remain false',()=>{
  const out=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:baseDecision,modelId:'phase57-fixed-horizon-v1',artifactSha256:HASH});
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(out.safety[key],false,key);
  }
});
