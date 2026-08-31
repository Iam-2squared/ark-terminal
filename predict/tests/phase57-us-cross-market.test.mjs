import test from 'node:test';
import assert from 'node:assert/strict';
import {PHASE57_US_CROSS_MARKET_POLICY as P,PHASE57_US_CROSS_MARKET_SAFETY as S,PHASE57_US_CROSS_MARKET_POLICY_SHA256 as H,assertPhase57UsCrossMarketSafety} from '../daytrade/phase57-us-cross-market-policy.js';

test('US cross-market remains separate from JPX formal OOS',()=>{
  assert.equal(P.market,'US');assert.equal(P.methodology.jpxEvidenceUntouched,true);assert.equal(P.methodology.jpxFormalOosSubstitution,false);assert.equal(P.purpose,'CROSS_MARKET_ACCURACY_VALIDATION_NOT_JPX_OOS_SUBSTITUTE');
});
test('US regular session and selection mirror JPX research structure',()=>{
  assert.deepEqual(P.regularSession,{open:'09:30',close:'16:00',barMinutes:5,expectedBars:78});assert.equal(P.selection.preOpenFrozenD50,true);assert.equal(P.selection.d50Size,50);assert.equal(P.selection.dynamic5mMarketwideRescan,true);assert.equal(P.selection.dynamic5mEveryMinutes,5);assert.equal(P.selection.d50AndDynamic5mAreSeparate,true);
});
test('US validation is accuracy-only with no capital or FX layer',()=>{
  assert.equal(P.lanes.length,7);assert.equal('allocationProfiles' in P,false);assert.equal(P.methodology.capitalAllocationExcluded,true);assert.equal(P.methodology.fxModelExcluded,true);assert.equal(P.reporting.returnUnit,'PERCENT');assert.deepEqual(P.reporting.metrics,['n','netReturnPct','meanReturnPctPerTrade','medianReturnPctPerTrade','winRatePct','profitFactor','maxDrawdownPct']);
});
test('policy is frozen and safety remains read only',()=>{
  assert.match(H,/^[a-f0-9]{64}$/);assert.equal(P.methodology.usOutcomeUsedForFitting,false);assert.equal(P.methodology.resultBasedRetuning,false);assert.equal(assertPhase57UsCrossMarketSafety(),true);
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(S[k],false,k);
});
