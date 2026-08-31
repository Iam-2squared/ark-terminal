import test from 'node:test';
import assert from 'node:assert/strict';
import {PHASE57_US_CROSS_MARKET_POLICY as P,PHASE57_US_CROSS_MARKET_SAFETY as S,PHASE57_US_CROSS_MARKET_POLICY_SHA256 as H,assertPhase57UsCrossMarketSafety} from '../daytrade/phase57-us-cross-market-policy.js';

test('US cross-market remains separate from JPX formal OOS',()=>{
  assert.equal(P.market,'US');assert.equal(P.methodology.jpxEvidenceUntouched,true);assert.equal(P.methodology.jpxFormalOosSubstitution,false);assert.equal(P.purpose,'CROSS_MARKET_PROSPECTIVE_VALIDATION_NOT_JPX_OOS_SUBSTITUTE');
});
test('US regular session contract is 5m and excludes extended hours',()=>{
  assert.deepEqual(P.regularSession,{open:'09:30',close:'16:00',barMinutes:5,expectedBars:78});assert.equal(P.methodology.preMarketAndAfterHoursExcluded,true);
});
test('US lanes mirror current JPX research matrix',()=>{
  assert.equal(P.lanes.length,7);assert.ok(P.lanes.includes('US_D50_FIXED'));assert.ok(P.lanes.includes('US_DYNAMIC5M_V2_V4'));assert.equal(P.allocationProfiles.length,7);
});
test('policy is frozen and safety remains read only',()=>{
  assert.match(H,/^[a-f0-9]{64}$/);assert.equal(P.methodology.usOutcomeUsedForFitting,false);assert.equal(P.methodology.resultBasedRetuning,false);assert.equal(assertPhase57UsCrossMarketSafety(),true);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(S[k],false,k);
});
