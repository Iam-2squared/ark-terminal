import assert from 'node:assert/strict';
import test from 'node:test';
import {classifyP25ExitV4Date,P25_EXIT_V4_PROSPECTIVE_SAFETY} from '../daytrade/phase57-p25-exit-v4-prospective-replay.js';

test('8/31 cannot become EXIT v4 fresh performance evidence',()=>{
  const x=classifyP25ExitV4Date('2026-08-31');
  assert.equal(x.bucket,'AUG31_FAILURE_ANALYSIS_ONLY');
  assert.equal(x.freshEligible,false);
  assert.equal(x.promotionEligible,false);
});

test('9/1 and later are fresh challenger prospective only, never auto-promotion',()=>{
  const x=classifyP25ExitV4Date('2026-09-01');
  assert.equal(x.bucket,'FRESH_CHALLENGER_PROSPECTIVE');
  assert.equal(x.freshEligible,true);
  assert.equal(x.formalOos,false);
  assert.equal(x.promotionEligible,false);
});

test('all execution and promotion surfaces stay disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(P25_EXIT_V4_PROSPECTIVE_SAFETY[key],false,key);
});
