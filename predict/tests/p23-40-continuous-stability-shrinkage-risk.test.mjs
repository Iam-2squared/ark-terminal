import assert from 'node:assert/strict';
import {P23_40_POLICY,stabilityReliability,shrinkageFeatureModel} from '../daytrade/phase57-continuous-stability-shrinkage-risk.js';
const a={weight:1,polarity:1,midpoint:0,sd:1},b={weight:.5,polarity:1,midpoint:0,sd:1},c={weight:.5,polarity:-1,midpoint:0,sd:1};
assert.equal(stabilityReliability(a,b),.5);assert.equal(stabilityReliability(a,c),0);
const full={ready:true,n:100,features:{x:a,y:b},weightSum:1.5},recent={ready:true,n:60,features:{x:b,y:{...b,weight:.25}},weightSum:.75};
const m=shrinkageFeatureModel(full,recent);assert.ok(m?.ready);assert.equal(m.stableFeatureCount,2);assert.ok(m.features.x.weight<full.features.x.weight);assert.ok(m.features.y.weight<full.features.y.weight);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_40_POLICY[k],false);
assert.equal(P23_40_POLICY.priorSessionsOnly,true);assert.equal(P23_40_POLICY.baselineCoveragePreserved,true);assert.equal(P23_40_POLICY.continuousReliabilityShrinkage,true);
console.log('P23.40 continuous stability shrinkage invariants: OK');
