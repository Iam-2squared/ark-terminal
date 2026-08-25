import assert from 'node:assert/strict';
import {summarizeP253ALPairs,runP253ALDynamicManagementMultisession,PHASE57_P25_3AL_POLICY,PHASE57_P25_3AL_SAFETY} from '../daytrade/phase57-p25-3al-dynamic-management-multisession.js';

const pairs=[
  {fixed:{netReturnPct:1,barsHeld:3},dynamic:{netReturnPct:1.5,barsHeld:4,givebackPct:0.2,captureRatio:0.8},deltaNetReturnPct:0.5,deltaBarsHeld:1},
  {fixed:{netReturnPct:-1,barsHeld:2},dynamic:{netReturnPct:-0.5,barsHeld:1,givebackPct:0.4,captureRatio:0.5},deltaNetReturnPct:0.5,deltaBarsHeld:-1},
  {fixed:{netReturnPct:0.2,barsHeld:5},dynamic:{netReturnPct:-0.1,barsHeld:3,givebackPct:0.3,captureRatio:0.6},deltaNetReturnPct:-0.3,deltaBarsHeld:-2},
];
const out=summarizeP253ALPairs(pairs);
assert.equal(out.pairedCount,3);
assert.equal(out.fixed.n,3);
assert.equal(out.dynamic.n,3);
assert.equal(out.delta.dynamicBetterCount,2);
assert.equal(out.delta.dynamicWorseCount,1);
assert.equal(out.delta.equalCount,0);
assert.ok(Math.abs(out.delta.meanNetReturnPct-(0.7/3))<1e-12);
assert.ok(Math.abs(out.delta.meanBarsHeldDelta-(-2/3))<1e-12);
assert.ok(out.fixed.maxDrawdownPct>=0);
assert.ok(out.dynamic.maxDrawdownPct>=0);
assert.equal(PHASE57_P25_3AL_POLICY.sameFrozenEvidenceChainAsP253D,true);
assert.equal(PHASE57_P25_3AL_POLICY.fixedBaselineMutationAllowed,false);
assert.equal(PHASE57_P25_3AL_POLICY.computeCachedScorePrefixAllowed,true);
assert.equal(PHASE57_P25_3AL_POLICY.resultBasedRuleSelectionAllowed,false);
assert.equal(PHASE57_P25_3AL_POLICY.performanceConclusionAllowed,false);
assert.throws(()=>runP253ALDynamicManagementMultisession({scorePrefix:'not-a-function'}),/scorePrefix must be a function/);
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']) assert.equal(PHASE57_P25_3AL_SAFETY[key],false,key);
console.log('P25.3AL dynamic management multisession regression test passed');
