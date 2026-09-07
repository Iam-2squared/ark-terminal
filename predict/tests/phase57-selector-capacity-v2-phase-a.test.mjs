import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

import {
  PHASE57_SELECTOR_CAPACITY_V2_PHASE_A,
  applyPhase57CapacityV2Prefix,
  extractPhase57CapacityV2Inputs,
  planPhase57CapacityV2OrdinalAllocation,
} from '../daytrade/phase57-selector-capacity-v2-contract.js';

const MODEL='444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2';

function hybrid({selectedCount=5}={}){
  const ranked=Array.from({length:30},(_,index)=>({
    symbol:String(1000+index),hybridRank:index+1,hybridScore:1-index*0.02,
    stage2:{remainingOpportunityScore:index<12?0.7:0.6},features:{marketBreadth:0.55},
  }));
  return {modelDigest:MODEL,featureCutoff:'2025-05-01T01:00:00.000Z',ranked,selected:ranked.slice(0,selectedCount)};
}

test('Capacity v2 Phase A bytes match the committed SHA-256 freeze',()=>{
  const bytes=fs.readFileSync(new URL('../research/phase57-selector-capacity-v2-phase-a.json',import.meta.url));
  const expected=fs.readFileSync(new URL('../research/phase57-selector-capacity-v2-phase-a.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  assert.equal(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.status,'CAPACITY_V2_ARCHITECTURE_FROZEN_BEFORE_RESERVE_RELEASE');
  assert.equal(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.learning.started,false);
});

test('only four whitelisted causal trainable inputs are emitted',()=>{
  const result=extractPhase57CapacityV2Inputs({hybridResult:hybrid(),decisionTime:'2025-05-01T01:00:00.000Z'});
  assert.deepEqual(Object.keys(result.features),PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.trainableFeatureWhitelist);
  assert.equal(result.features.hybridQualityDecayRank5To1,0.08);
  assert.equal(result.features.qualifiedCandidateCount,12);
  assert.equal(result.features.marketBreadth,0.55);
  assert.equal(result.features.dataQualityConfidence,1);
  assert.equal(result.futureInformationUsed,false);
});

test('Capacity v2 selection is always an unchanged Frozen Hybrid prefix',()=>{
  const source=hybrid();
  for(const capacity of [5,10,15,20]){
    const result=applyPhase57CapacityV2Prefix({hybridResult:source,capacity});
    assert.equal(result.prefixIdentity,true);
    assert.equal(result.reranked,false);
    assert.deepEqual(result.selected.map(row=>row.symbol),source.ranked.slice(0,capacity).map(row=>row.symbol));
  }
  assert.throws(()=>applyPhase57CapacityV2Prefix({hybridResult:source,capacity:7}),/must be one of/);
});

test('Frozen Hybrid v1 ABSTAIN cannot be overridden in Phase A',()=>{
  const source=hybrid({selectedCount:0});
  assert.equal(applyPhase57CapacityV2Prefix({hybridResult:source,capacity:0}).selected.length,0);
  assert.throws(()=>applyPhase57CapacityV2Prefix({hybridResult:source,capacity:5}),/preserves Frozen Hybrid v1 ABSTAIN/);
});

test('future outcome and responsibility leakage fail closed',()=>{
  assert.throws(()=>extractPhase57CapacityV2Inputs({hybridResult:{...hybrid(),realizedReturn:0.1},decisionTime:'2025-05-01T01:00:00.000Z'}),/forbidden realizedReturn/);
  const source=hybrid();source.ranked[0]={...source.ranked[0],entry:{direction:'LONG'}};
  assert.throws(()=>extractPhase57CapacityV2Inputs({hybridResult:source,decisionTime:'2025-05-01T01:00:00.000Z'}),/forbidden entry/);
});

test('ordinal allocation consumes 120 sessions including purges and leaves 162 sealed',()=>{
  const allocation=planPhase57CapacityV2OrdinalAllocation({reserveSessionCount:282});
  assert.equal(allocation.developmentSessions,60);
  assert.equal(allocation.validationSessions,29);
  assert.equal(allocation.untouchedOosSessions,29);
  assert.equal(allocation.purgeSessions,2);
  assert.equal(allocation.totalAllocatedIncludingPurges,120);
  assert.equal(allocation.reserveRemainingSessions,162);
  assert.equal(allocation.sessionDatesMaterialized,false);
});

test('all safety flags and architecture mutation permissions remain false',()=>{
  assert.ok(Object.values(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.safety).every(value=>value===false));
  assert.equal(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.architecture.rerankingAllowed,false);
  assert.equal(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.guards.reserveFullReleaseAllowed,false);
  assert.equal(PHASE57_SELECTOR_CAPACITY_V2_PHASE_A.goNoGoContract.automaticPromotionAllowed,false);
});
