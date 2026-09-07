import test from 'node:test';
import assert from 'node:assert/strict';
import {Phase57CapacityShardInternals} from '../../scripts/evaluate_phase57_selector_capacity_shard.mjs';
import {Phase57CapacitySummaryInternals} from '../../scripts/summarize_phase57_selector_capacity.mjs';

test('capacity diagnostic recomputes unchanged Frozen Hybrid digests',()=>{
  assert.equal(Phase57CapacityShardInternals.modelDigest(),'444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2');
  assert.equal(Phase57CapacityShardInternals.freezeDigest(),'a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da');
});

test('distribution includes requested quartiles and bounds',()=>{
  assert.deepEqual(Phase57CapacitySummaryInternals.distribution([0,1,2,3,4]),{n:5,mean:2,median:2,p25:1,p75:3,iqr:2,min:0,max:4,positiveRate:.8});
});

test('rank-band summary remains session-equal and cost adjusted',()=>{
  const target=value=>({status:'TARGET_READY',finalCloseReturn:0,upExcursion:value*.6,downExcursion:value*.4,twoSidedOpportunity:value});
  const rows=[1,2].map((rank,index)=>({fold:'VALIDATION',selector:'HYBRID',rank,sessionDate:'2025-01-31',preSelectionMove:.001,targetsByHorizon:Object.fromEntries([1,2,3,6,12].map(h=>[h,target(.02+index*.01)]))}));
  const result=Phase57CapacitySummaryInternals.summarizeRows(rows,'VALIDATION','HYBRID',1,5);
  assert.equal(result.candidateRows,2);assert.equal(result.costAdjustedUtilityBps,240);assert.equal(result.sessionEqual.meanUtilityBps,240);
});
