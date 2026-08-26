import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';

const yml=fs.readFileSync('.github/workflows/phase57-p25-data-driven-exit-paired.yml','utf8');

test('paired workflow is exact DYNAMIC_50 research-only persistence',()=>{
  for(const needle of [
    'run_p25_data_driven_exit_paired.mjs',
    'automation/p25-data-driven-exit-data',
    'data/p25-data-driven-exit/${EVIDENCE_DATE}.json',
    'exactDynamic50Only',
    'resultBasedRetuning',
    'executionAllowed',
    'freshHoldoutConsumed',
    'append-only conflict',
  ]) assert.ok(yml.includes(needle),`missing ${needle}`);
  assert.ok(!/executionAllowed\s*[:=]\s*true/.test(yml));
  assert.ok(!/liveTradingAllowed\s*[:=]\s*true/.test(yml));
  assert.ok(!/paperTradingAllowed\s*[:=]\s*true/.test(yml));
  assert.ok(!/freshHoldoutConsumed\s*[:=]\s*true/.test(yml));
});
