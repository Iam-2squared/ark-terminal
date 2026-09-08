import test from 'node:test';
import assert from 'node:assert/strict';
import { recover } from '../../scripts/recover_phase57_capacity_v2_1_development.mjs';
test('exact precommitted mapping rejection produces NO-GO without releasing data',()=>{
 const r=recover(()=>{throw new Error('V2_1_DEVELOPMENT_NO_ROBUST_MAPPING_MEETS_PRECOMMITTED_GATES')},[],{},{},{safety:{executionAllowed:false}});
 assert.equal(r.status,'CAPACITY_V2_1_FINAL_NO_GO');
 assert.equal(r.validationReleased,false);assert.equal(r.untouchedOosReleased,false);assert.equal(r.model,null);
});
test('technical exceptions remain failures',()=>{
 for(const message of ['CHECKPOINT_INTEGRITY_FAILED','insufficient target samples RANK_6_10','TypeError','V2_1_DEVELOPMENT_NO_ROBUST_MAPPING_MEETS_PRECOMMITTED_GATES extra'])
 assert.throws(()=>recover(()=>{throw new Error(message)},[],{},{},{}),new RegExp(message));
});
test('successful training result is preserved',()=>{
 const result={model:{modelDigest:'fixed'},freeze:{},summary:{}};
 assert.equal(recover(()=>result,[],{},{},{}).result,result);
});
