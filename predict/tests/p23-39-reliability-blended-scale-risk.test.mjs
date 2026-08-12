import assert from 'node:assert/strict';
import {P23_39_POLICY,empiricalReliability,reliabilityBlendedScale} from '../daytrade/phase57-reliability-blended-scale-risk.js';
const m={ready:true,features:{a:{weight:1,polarity:1,midpoint:0,sd:1},b:{weight:1,polarity:1,midpoint:0,sd:1}},weightSum:2};
const hist=[{velocity:{a:1,b:1}},{velocity:{a:-1,b:-1}},{velocity:{a:.5,b:.5}},{velocity:{a:-.5,b:-.5}}];
assert.ok(empiricalReliability(0)===0);assert.ok(empiricalReliability(30)===0.5);assert.ok(empiricalReliability(300)>0.9);
const scale=reliabilityBlendedScale(hist,m);assert.ok(Number.isFinite(scale)&&scale>0);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_39_POLICY[k],false);
assert.equal(P23_39_POLICY.priorSessionsOnly,true);assert.equal(P23_39_POLICY.baselineCoveragePreserved,true);assert.equal(P23_39_POLICY.reliabilityBlendedScale,true);assert.equal(P23_39_POLICY.empiricalReliabilityPriorRows,30);
console.log('P23.39 reliability-blended scale invariants: OK');
