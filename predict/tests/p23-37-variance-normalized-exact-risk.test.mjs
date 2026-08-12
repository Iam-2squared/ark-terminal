import assert from 'node:assert/strict';
import {P23_37_POLICY,compositeScale,varianceNormalizedScore} from '../daytrade/phase57-variance-normalized-exact-risk.js';
const m={ready:true,features:{a:{weight:1,polarity:1,midpoint:0,sd:1},b:{weight:1,polarity:1,midpoint:0,sd:1}},weightSum:2};
assert.equal(compositeScale(m),Math.SQRT1_2);
const z=varianceNormalizedScore({velocity:{a:1,b:1}},m);assert.ok(Math.abs(z-Math.SQRT2)<1e-12);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_37_POLICY[k],false);
assert.equal(P23_37_POLICY.priorSessionsOnly,true);assert.equal(P23_37_POLICY.baselineCoveragePreserved,true);assert.equal(P23_37_POLICY.varianceNormalization,true);
console.log('P23.37 variance-normalized exact invariants: OK');
