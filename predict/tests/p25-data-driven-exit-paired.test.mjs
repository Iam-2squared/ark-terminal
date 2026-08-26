import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeP25DataDrivenPairs,P25_DATA_DRIVEN_PAIRED_SAFETY} from '../daytrade/phase57-p25-data-driven-exit-multisession.js';

test('data-driven paired summary compounds fixed and data-driven returns independently',()=>{
  const pairs=[
    {fixed:{netReturnPct:10},dataDriven:{netReturnPct:5,barsHeld:4,givebackPct:1,captureRatio:0.5},deltaNetReturnPct:-5},
    {fixed:{netReturnPct:-5},dataDriven:{netReturnPct:2,barsHeld:6,givebackPct:0.5,captureRatio:0.8},deltaNetReturnPct:7},
  ];
  const s=summarizeP25DataDrivenPairs(pairs);
  assert.equal(s.pairedCount,2);
  assert.ok(Math.abs(s.fixed.netReturnPct-4.5)<1e-12);
  assert.ok(Math.abs(s.dataDriven.netReturnPct-7.1)<1e-12);
  assert.equal(s.delta.dataDrivenBetterCount,1);
  assert.equal(s.delta.dataDrivenWorseCount,1);
  assert.equal(s.delta.meanBarsHeld,5);
});

test('paired evaluator safety is research-only and fail-closed for trading',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']) assert.equal(P25_DATA_DRIVEN_PAIRED_SAFETY[key],false,key);
});
