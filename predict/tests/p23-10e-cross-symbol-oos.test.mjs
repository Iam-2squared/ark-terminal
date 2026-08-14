import assert from 'node:assert/strict';
import { EXPANDED_UNIVERSE } from '../daytrade/phase57-expanded-universe.js';
import {
  CHART_QUALITY_HOLDOUT_UNIVERSE,
  CHART_QUALITY_HOLDOUT_POLICY,
} from '../daytrade/phase57-chart-quality-holdout-universe.js';
import { PHASE57_CHART_PERCEPTION_SAFETY } from '../daytrade/phase57-chart-perception-2.js';

assert.equal(CHART_QUALITY_HOLDOUT_UNIVERSE.length, 30);
assert.equal(new Set(CHART_QUALITY_HOLDOUT_UNIVERSE).size, 30);
assert.deepEqual(
  CHART_QUALITY_HOLDOUT_UNIVERSE.filter(symbol => EXPANDED_UNIVERSE.includes(symbol)),
  [],
  'holdout symbols must be disjoint from the P23.10 development 30',
);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.frozenBeforeOutcomeMeasurement, true);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.disjointFromP23_10Development30, true);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.selectedFromP23_10Outcomes, false);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.qualityScoreRetuningAllowed, false);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.qualityBandRetuningAllowed, false);
assert.equal(CHART_QUALITY_HOLDOUT_POLICY.setupRuleRetuningAllowed, false);

for (const key of [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
]) assert.equal(PHASE57_CHART_PERCEPTION_SAFETY[key], false, `${key} must stay false`);

console.log('P23.10E cross-symbol OOS holdout tests passed');
