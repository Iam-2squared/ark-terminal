import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {instrumentTrainer,replaceOnce,summarize} from '../../scripts/diagnose_phase57_capacity_v2_1.mjs';
const spec={mappingSelectionContract:{eligibleGlobalGates:{utilityDifferenceMinimumBps:-10,meanCandidateCountMinimumRelativeIncrease:1.25,meanCandidateCountMinimumAbsoluteIncrease:2,maximumAdjacentDecisionJumpGreaterThanFiveRate:0.15},eligibleFoldGate:{minimumUtilityDifferenceBpsInEveryHeldOutFold:-10}}};
const candidate={thresholds:{a:0},global:{utilityDifference:-10,countRatio:1.25,absoluteIncrease:2,jump:0.15},worstFoldUtilityDifference:-10,eligible:true};
test('exact boundaries pass and never release evaluation',()=>{
 const s=summarize({diagnostics:[candidate]},spec);
 assert.equal(s.eligibleCount,1);assert.equal(s.validationReleased,false);assert.equal(s.untouchedOosReleased,false);
});
test('reports each failure independently, including overlap',()=>{
 const c={...candidate,global:{utilityDifference:-11,countRatio:1,absoluteIncrease:0,jump:0.2},worstFoldUtilityDifference:-11,eligible:false};
 const s=summarize({diagnostics:[c]},spec);
 assert.deepEqual(Object.values(s.failedByGate),[1,1,1,1,1]);assert.equal(s.eligibleCount,0);
});
test('eligibility mismatch is technical failure',()=>assert.throws(()=>summarize({diagnostics:[{...candidate,eligible:false}]},spec),/PARITY/));
test('modified frozen source or ambiguous anchors fail closed',()=>{
 assert.throws(()=>instrumentTrainer('changed'),/HASH/);
 assert.throws(()=>replaceOnce('x x','x','y'),/ANCHOR/);
 assert.throws(()=>replaceOnce('z','x','y'),/ANCHOR/);
});
test('instrumentation captures candidates before full fit without changing gates',()=>{
 const source=fs.readFileSync('scripts/run_phase57_selector_capacity_v2_1.mjs','utf8');
 const result=instrumentTrainer(source);
 assert.ok(result.includes('diagnostics.push(candidate)'));
 assert.ok(result.indexOf('return { diagnostics, choices, grids') < result.indexOf('const fullScale = featureScale(rows)'));
 assert.ok(result.includes('global.utilityDifference >= g.utilityDifferenceMinimumBps'));
});
