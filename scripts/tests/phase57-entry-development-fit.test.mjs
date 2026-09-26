import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyDevelopmentContracts,foldSessions,solveWeightedLogistic,ALLOCATION,FIT} from '../lib/phase57-entry-development-fit.mjs';

test('58 exact dates, immutable feature/target/state and safety contracts',()=>{
  assert.match(verifyDevelopmentContracts().allocationSha256,/^[a-f0-9]{64}$/);
  assert.equal(ALLOCATION.sessions[0].sessionDate,'2025-10-09');
  assert.equal(ALLOCATION.sessions.at(-1).sessionDate,'2026-01-07');
});
test('four chronological folds; each evaluation session appears once',()=>{
  const seen=[];
  for(let i=0;i<4;i++){
    const f=foldSessions(i);assert(f.train.at(-1)<f.embargo[0]);assert(f.embargo[0]<f.evaluate[0]);
    assert(f.evaluate.every(s=>!f.train.includes(s)));seen.push(...f.evaluate);
  }
  assert.equal(seen.length,28);assert.equal(new Set(seen).size,28);
});
test('threshold grid is small and validation stays closed',()=>{
  assert.deepEqual(FIT.threshold.candidates,[0.5,0.55,0.6]);
  assert.equal(FIT.freshValidationAllowed,false);assert.equal(FIT.freshOosAllowed,false);
});
test('synthetic numerical solver is deterministic and converges',()=>{
  const x=Array.from({length:40},(_,i)=>[i/20-1,...Array(9).fill(0)]);
  const y=x.map(r=>Number(r[0]>0)),w=x.map(()=>1);
  const a=solveWeightedLogistic(x,y,w),b=solveWeightedLogistic(x,y,w);
  assert.deepEqual(a,b);assert(a.converged);assert(a.weights[0]>0);
  assert(a.scales.slice(1).every(v=>v===1));
});
test('missing values and one-class input fail closed',()=>{
  assert.throws(()=>solveWeightedLogistic([Array(10).fill(0)],[1],[1]),/BOTH_CLASSES/);
  assert.throws(()=>solveWeightedLogistic([Array(10).fill(NaN),Array(10).fill(0)],[0,1],[1,1]),/MISSING_FEATURE/);
});
