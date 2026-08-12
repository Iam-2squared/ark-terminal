import assert from 'node:assert/strict';
import {P23_38_POLICY,empiricalCompositeScale,empiricalScaleScore} from '../daytrade/phase57-empirical-scale-exact-risk.js';
const m={ready:true,features:{a:{weight:1,polarity:1,midpoint:0,sd:1},b:{weight:1,polarity:1,midpoint:0,sd:1}},weightSum:2};
const hist=[{velocity:{a:-1,b:-1}},{velocity:{a:0,b:0}},{velocity:{a:1,b:1}}];
assert.equal(empiricalCompositeScale(hist,m),1);
assert.equal(empiricalScaleScore({velocity:{a:2,b:2}},hist,m),2);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_38_POLICY[k],false);
assert.equal(P23_38_POLICY.priorSessionsOnly,true);assert.equal(P23_38_POLICY.baselineCoveragePreserved,true);assert.equal(P23_38_POLICY.empiricalCompositeScale,true);assert.equal(P23_38_POLICY.covarianceAware,true);assert.equal(P23_38_POLICY.centerRemoved,false);
console.log('P23.38 empirical-scale exact invariants: OK');
