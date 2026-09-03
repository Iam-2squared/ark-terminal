import assert from 'node:assert/strict';
import fs from 'node:fs';
import { EXPANDED_UNIVERSE } from '../daytrade/phase57-expanded-universe.js';
import { CHART_QUALITY_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-quality-holdout-universe.js';
import { CHART_ECONOMIC_HOLDOUT_UNIVERSE } from '../daytrade/phase57-chart-economic-holdout-universe.js';
import { P25_EXIT_V3_DUAL_GATE_POLICY, P25_EXIT_V3_DUAL_GATE_POLICY_SHA256 } from '../daytrade/phase57-p25-exit-v3-dual-gate.js';
import { P25_EXIT_V3_INDEPENDENT_PROTOCOL, P25_EXIT_V3_SAFETY } from '../daytrade/phase57-p25-exit-v3-independent-protocol.js';

const universe=[...new Set([...EXPANDED_UNIVERSE,...CHART_QUALITY_HOLDOUT_UNIVERSE,...CHART_ECONOMIC_HOLDOUT_UNIVERSE])];
assert.equal(EXPANDED_UNIVERSE.length,30);
assert.equal(CHART_QUALITY_HOLDOUT_UNIVERSE.length,30);
assert.equal(CHART_ECONOMIC_HOLDOUT_UNIVERSE.length,30);
assert.equal(universe.length,90,'stress universe must remain exactly 90 unique pre-existing symbols');
assert.equal(P25_EXIT_V3_DUAL_GATE_POLICY.developmentCutoff,'2026-08-12');
assert.equal(P25_EXIT_V3_INDEPENDENT_PROTOCOL.developmentCutoff,'2026-08-12');
assert.equal(P25_EXIT_V3_DUAL_GATE_POLICY.exactDynamic50Only,true,'v3 production research policy must stay exact-D50-only');
assert.match(P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,/^[a-f0-9]{64}$/);
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']) assert.equal(P25_EXIT_V3_SAFETY[k],false,`${k} must remain false`);
const runner=fs.readFileSync(new URL('../daytrade/run-phase57-p25-exit-v3-90symbol-historical-stress.mjs',import.meta.url),'utf8');
const reducer=fs.readFileSync(new URL('../daytrade/aggregate-phase57-p25-exit-v3-90symbol-historical-stress.mjs',import.meta.url),'utf8');
for(const text of [runner,reducer]){
  assert.match(text,/currentDynamic50Comparable:false/);
  assert.match(text,/formalOos:false/);
  assert.match(text,/promotionEligible:false/);
  assert.match(text,/retuningAllowed:false/);
  assert.match(text,/freshHoldoutConsumed:false/);
}
console.log('P25 EXIT v3 90-symbol historical stress guards: OK');
