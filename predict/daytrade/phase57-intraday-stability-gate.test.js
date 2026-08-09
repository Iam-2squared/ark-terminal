import test from 'node:test';
import assert from 'node:assert/strict';
import { passesInnerStabilityGate, PHASE57_P20_5_SAFETY } from './phase57-intraday-stability-gate.js';

test('stability gate accepts only sufficiently strong inner evidence',()=>{
  assert.equal(passesInnerStabilityGate({signalCount:40,hitRate:0.60,netAverageReturn:0.01}),true);
  assert.equal(passesInnerStabilityGate({signalCount:10,hitRate:0.90,netAverageReturn:0.10}),false);
  assert.equal(passesInnerStabilityGate({signalCount:40,hitRate:0.54,netAverageReturn:0.10}),false);
  assert.equal(passesInnerStabilityGate({signalCount:40,hitRate:0.60,netAverageReturn:-0.01}),false);
});

test('thresholds are configurable without looking at outer outcomes',()=>{
  const selected={signalCount:25,hitRate:0.55,netAverageReturn:-0.005};
  assert.equal(passesInnerStabilityGate(selected,{minStableInnerSignals:20,minStableInnerHitRate:0.54,minStableInnerNetReturn:-0.01}),true);
});

test('P20.5 remains research only',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_P20_5_SAFETY[key],false);
});
