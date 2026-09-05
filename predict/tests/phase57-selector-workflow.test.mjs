import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-selector-v123-historical-pilot.yml',import.meta.url),'utf8');

test('historical pilot is manual, read-only and cannot release outer OOS',()=>{
  assert.match(workflow,/workflow_dispatch:/);
  assert.match(workflow,/acknowledge_provider_terms:/);
  assert.match(workflow,/permissions:\n  contents: read/);
  assert.doesNotMatch(workflow,/\nschedule:/);
  assert.doesNotMatch(workflow,/\npush:/);
  assert.doesNotMatch(workflow,/--release-outer-oos true/);
  assert.match(workflow,/BENCHMARK_OOS_SEALED/);
  assert.match(workflow,/--sample-seed PHASE57_SELECTOR_V3_0_20260905/);
  assert.match(workflow,/phase57-selector-v123-selection-outcomes\.ndjson\.gz/);
  assert.match(workflow,/REDUCED_UNIVERSE_PIPELINE_PILOT/);
});

test('pilot is explicitly survivorship-limited and safety-guarded',()=>{
  assert.match(workflow,/SURVIVORSHIP_LIMITED_RECONSTRUCTION/);
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ])assert.match(workflow,new RegExp(key));
});
