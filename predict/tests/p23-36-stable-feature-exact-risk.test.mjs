import assert from 'node:assert/strict';
import {P23_36_POLICY,stableFeatureModel} from '../daytrade/phase57-stable-feature-exact-risk.js';
const fm=(pols)=>({ready:true,n:80,bad:20,good:60,features:Object.fromEntries(Object.entries(pols).map(([k,polarity])=>[k,{polarity,weight:1,midpoint:0,sd:1}])),weightSum:Object.keys(pols).length});
const full=fm({a:1,b:-1,c:1}),recent=fm({a:1,b:-1,c:-1});
const stable=stableFeatureModel(full,recent);assert.ok(stable);assert.equal(stable.stableFeatureCount,2);assert.deepEqual(Object.keys(stable.features).sort(),['a','b']);assert.equal(stable.features.a,full.features.a);assert.equal(stable.features.b,full.features.b);
assert.equal(stableFeatureModel(full,fm({a:-1,b:1,c:1})),null);
assert.equal(P23_36_POLICY.recentWindowRows,60);assert.equal(P23_36_POLICY.priorSessionsOnly,true);assert.equal(P23_36_POLICY.baselineCoveragePreserved,true);assert.equal(P23_36_POLICY.fullParametersPreserved,true);assert.equal(P23_36_POLICY.recentModelUsedForPolarityGateOnly,true);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_36_POLICY[k],false);
console.log('P23.36 stable-feature exact-risk invariants: OK');
