import assert from 'node:assert/strict';
import {
  P23_10H_DIRECTION_SETUP_POLICY,
  PHASE57_P23_10H_SAFETY,
  simulateDirectionSetupManagedExit,
} from '../daytrade/phase57-direction-setup-management.js';
import { DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE } from '../daytrade/phase57-direction-setup-management-holdout-universe.js';
import { EXPANDED_UNIVERSE } from '../daytrade/phase57-expanded-universe.js';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-quality-holdout-universe.js';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-economic-holdout-universe.js';
import { CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-trade-management-holdout-universe.js';

for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) {
  assert.equal(PHASE57_P23_10H_SAFETY[key], false, `${key} must remain false`);
}
assert.equal(P23_10H_DIRECTION_SETUP_POLICY.longPolicy,'SETUP_STRUCTURAL_INVALIDATION_OVER_FROZEN_RATCHET');
assert.equal(P23_10H_DIRECTION_SETUP_POLICY.shortPolicy,'FROZEN_RATCHET_BASELINE_ONLY');
assert.equal(P23_10H_DIRECTION_SETUP_POLICY.numericExitParameterSearchAllowed,false);
assert.equal(P23_10H_DIRECTION_SETUP_POLICY.directionSpecificNumericParameterSearchAllowed,false);

const prior=new Set([...EXPANDED_UNIVERSE,...CHART_QUALITY_HOLDOUT_UNIVERSE,...CHART_ECONOMIC_HOLDOUT_UNIVERSE,...CHART_TRADE_MANAGEMENT_HOLDOUT_UNIVERSE]);
assert.equal(DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE.length,30);
assert.equal(new Set(DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE).size,30);
assert.equal(DIRECTION_SETUP_MANAGEMENT_HOLDOUT_UNIVERSE.some(symbol=>prior.has(symbol)),false,'P23.10H universe must be disjoint from prior 120 chart symbols');

const context=[];
for(let i=0;i<30;i+=1){const c=100+i*0.1;context.push({timestamp:new Date(Date.UTC(2026,7,3,0,i*5)).toISOString(),open:c,high:c+0.3,low:c-0.3,close:c+0.1,volume:1000});}
const future=[
  {timestamp:'2026-08-03T02:30:00.000Z',open:103,high:103.2,low:102.6,close:102.9,volume:1000},
  {timestamp:'2026-08-03T02:35:00.000Z',open:102.9,high:103,low:102.2,close:102.4,volume:1000},
  {timestamp:'2026-08-03T02:40:00.000Z',open:102.4,high:102.6,low:102,close:102.1,volume:1000},
];
const perception={timeframes:{'5m':{status:'CHART_PERCEPTION_READY',breakout:{level:102.5},scenario:{invalidationReference:101.5}}}};
const shortExit=simulateDirectionSetupManagedExit({setup:'BREAKOUT_CONTINUATION_DOWN',perception,entryPrice:103,direction:'DOWN',contextBars:context,futureBars:future,sessionDate:'2026-08-03'});
assert.ok(shortExit);
assert.equal(shortExit.directionArchitecture,'SHORT_BASELINE_ONLY');
assert.equal(shortExit.numericRetuningUsed,false);

console.log('P23.10H direction x setup management tests passed');
