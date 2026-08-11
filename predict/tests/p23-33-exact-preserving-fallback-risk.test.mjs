import assert from 'node:assert/strict';
import {combineExactPreserving,P23_33_POLICY,p2333Key} from '../daytrade/phase57-exact-preserving-fallback-risk.js';
const row=(symbol,score,extra={})=>({symbol,setup:'A',direction:'DOWN',timestamp:`2026-08-01T0${symbol.length}:00:00.000Z`,offsetBars:2,riskScore:score,...extra});
const a=row('X',.7),b=row('YY',-.2);const baseline=[a,b];
const hierarchical=[{...a,riskScore:-9,exactReady:true,directionReady:true},{...b,riskScore:9,exactReady:true,directionReady:true},row('ZZZ',.4,{exactReady:false,directionReady:true}),row('WWWW',.9,{exactReady:true,directionReady:true})];
const out=combineExactPreserving(baseline,hierarchical);assert.equal(out.exactCount,2);assert.equal(out.fallbackCount,1);assert.equal(out.rows.length,3);
const byKey=new Map(out.rows.map(r=>[p2333Key(r),r]));assert.equal(byKey.get(p2333Key(a)).riskScore,.7);assert.equal(byKey.get(p2333Key(b)).riskScore,-.2);assert.equal(byKey.get(p2333Key(a)).scoreSource,'EXACT_P23_30');assert.equal(byKey.get(p2333Key(hierarchical[2])).scoreSource,'DIRECTION_FALLBACK');assert.equal(byKey.has(p2333Key(hierarchical[3])),false);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_33_POLICY[k],false);assert.equal(P23_33_POLICY.priorSessionsOnly,true);assert.equal(P23_33_POLICY.exactP2330Preserved,true);assert.equal(P23_33_POLICY.directionFallbackOnlyWhenExactUnavailable,true);console.log('P23.33 exact-preserving fallback invariants: OK');
