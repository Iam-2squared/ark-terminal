import assert from 'node:assert/strict';
import {P23_35_POLICY,priorAgreementEvidence} from '../daytrade/phase57-prior-agreement-fallback-risk.js';
const model=(n,pols)=>({ready:true,n,features:Object.fromEntries(Object.entries(pols).map(([k,polarity])=>[k,{polarity,weight:1,midpoint:0,sd:1}]))});
const full=model(80,{a:1,b:-1,c:1}),recent=model(60,{a:1,b:-1,c:-1});
const ok=priorAgreementEvidence({fullModel:full,recentModel:recent,fullScore:.4,recentScore:.2});assert.equal(ok.trusted,true);assert.equal(ok.sharedFeatureCount,3);assert.equal(ok.polarityAgreeCount,2);assert.equal(ok.scoreSignAgreement,true);
const badSign=priorAgreementEvidence({fullModel:full,recentModel:recent,fullScore:.4,recentScore:-.2});assert.equal(badSign.trusted,false);assert.equal(badSign.scoreSignAgreement,false);
const badPol=priorAgreementEvidence({fullModel:full,recentModel:model(60,{a:-1,b:1,c:-1}),fullScore:.4,recentScore:.2});assert.equal(badPol.trusted,false);
for(const k of ['thresholdSearchAllowed','selectionAllowed','exitPolicyChangeAllowed','entryRetuningAllowed','symbolFilteringAllowed','freshHoldoutConsumed'])assert.equal(P23_35_POLICY[k],false);assert.equal(P23_35_POLICY.priorSessionsOnly,true);assert.equal(P23_35_POLICY.exactP2330Preserved,true);assert.equal(P23_35_POLICY.fallbackOnlyWhenExactUnavailable,true);assert.equal(P23_35_POLICY.requireFullRecentScoreSignAgreement,true);console.log('P23.35 prior agreement fallback invariants: OK');
