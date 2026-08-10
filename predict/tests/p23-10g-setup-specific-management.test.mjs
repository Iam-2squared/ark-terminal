import assert from 'node:assert/strict';
import {
  P23_10G_SETUP_MANAGEMENT_POLICY,
  PHASE57_P23_10G_SAFETY,
  deriveSetupInvalidationReference,
  firstSetupInvalidation,
  summarizePairedExitDelta,
} from '../daytrade/phase57-setup-specific-trade-management.js';
import { CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-trade-management-holdout-universe.js';
import { EXPANDED_UNIVERSE } from '../daytrade/phase57-expanded-universe.js';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-quality-holdout-universe.js';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-economic-holdout-universe.js';

for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_10G_SAFETY[key], false, `${key} must remain false`);
}
assert.equal(P23_10G_SETUP_MANAGEMENT_POLICY.noOutcomeThresholdSearch,true);
assert.equal(P23_10G_SETUP_MANAGEMENT_POLICY.noSetupSpecificNumericParameterSearch,true);
assert.equal(P23_10G_SETUP_MANAGEMENT_POLICY.entrySetMustRemainPairedWithBaseline,true);

const prior=new Set([...EXPANDED_UNIVERSE,...CHART_QUALITY_HOLDOUT_UNIVERSE,...CHART_ECONOMIC_HOLDOUT_UNIVERSE]);
assert.equal(CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE.length,30);
assert.equal(new Set(CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE).size,30);
assert.equal(CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE.some(symbol=>prior.has(symbol)),false,'P23.10G universe must be disjoint from prior 90 chart symbols');

const perception={timeframes:{'5m':{
  status:'CHART_PERCEPTION_READY',
  breakout:{state:'BREAKOUT_UP',level:100},
  scenario:{invalidationReference:96},
}}};
assert.deepEqual(deriveSetupInvalidationReference({setup:'BREAKOUT_CONTINUATION_UP',perception}),{
  reference:100,source:'SIGNAL_TIME_5M_BREAKOUT_LEVEL',rule:'CLOSE_BREACH_INVALIDATES',
});
assert.deepEqual(deriveSetupInvalidationReference({setup:'TREND_PULLBACK_UP',perception}),{
  reference:96,source:'SIGNAL_TIME_5M_SCENARIO_INVALIDATION',rule:'CLOSE_BREACH_INVALIDATES',
});

const bars=[
  {timestamp:'2026-08-03T00:05:00.000Z',open:101,high:102,low:99.5,close:100.4,volume:1},
  {timestamp:'2026-08-03T00:10:00.000Z',open:100.4,high:101,low:99.2,close:99.8,volume:1},
  {timestamp:'2026-08-03T00:15:00.000Z',open:99.8,high:100.2,low:98.8,close:99.1,volume:1},
];
const invalidation=firstSetupInvalidation({setup:'BREAKOUT_CONTINUATION_UP',perception,direction:'UP',futureBars:bars,sessionDate:'2026-08-03'});
assert.equal(invalidation.timestamp,'2026-08-03T00:10:00.000Z');
assert.equal(invalidation.reference,100);
assert.equal(invalidation.causalCloseOnly,true);

const pairs=[
  {baseline:{netReturnPct:0.1},managed:{netReturnPct:0.2,structuralInvalidationTriggeredBeforeBaseline:true}},
  {baseline:{netReturnPct:-0.2},managed:{netReturnPct:-0.1,structuralInvalidationTriggeredBeforeBaseline:true}},
  {baseline:{netReturnPct:0.3},managed:{netReturnPct:0.3,structuralInvalidationTriggeredBeforeBaseline:false}},
];
const delta=summarizePairedExitDelta(pairs);
assert.equal(delta.pairCount,3);
assert.equal(delta.improvedTradeCount,2);
assert.equal(delta.worsenedTradeCount,0);
assert.equal(delta.unchangedTradeCount,1);
assert.equal(delta.structuralInvalidationEarlierCount,2);
assert.ok(Math.abs(delta.averageNetDeltaPctPoints-(0.2/3))<1e-12);

console.log('P23.10G setup-specific management tests passed');
