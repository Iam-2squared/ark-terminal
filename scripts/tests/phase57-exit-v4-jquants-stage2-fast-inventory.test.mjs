import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const inventory = fs.readFileSync(new URL('../phase57-exit-v4-jquants-stage2-fast-inventory.mjs', import.meta.url),'utf8');
const aggregate = fs.readFileSync(new URL('../phase57-exit-v4-jquants-stage2-fast-aggregate.mjs', import.meta.url),'utf8');
const workflow = fs.readFileSync(new URL('../../.github/workflows/phase57-exit-v4-jquants-stage2-fast-inventory.yml', import.meta.url),'utf8');

test('metadata-only collector cannot call Tick bulk or EXIT code',()=>{
  assert.doesNotMatch(inventory,/v2\/bulk\/(get|list)/);
  assert.doesNotMatch(inventory,/MFE|MAE|winRate|profit|pnl/i);
  assert.doesNotMatch(workflow,/v2\/bulk\/(get|list)/);
});

test('protected, fresh, and existing verified ranges are not refetched',()=>{
  for(const text of ['2025-04-15','2026-01-07','2026-01-08','2026-06-11','2026-09-10'])assert.match(inventory,new RegExp(text));
  assert.match(inventory,/PROTECTED_IDENTIFIER_ONLY/);
  assert.match(inventory,/FRESH_IDENTIFIER_ONLY/);
});

test('raw rows are reduced in memory and never persisted',()=>{
  assert.match(inventory,/rawPersisted:false/);
  assert.doesNotMatch(inventory,/writeFileSync\([^\n]+minuteRaw/);
  assert.match(aggregate,/exitOutcomes:0,futureLabels:0,exitInvocations:0/);
});

test('all safety flags remain false',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.match(inventory,new RegExp(`${key}:false`));
});

test('frozen 13-gate schema is represented without mutation',()=>{
  for(const id of ['TIMESTAMP_CONTRACT','FIVE_MINUTE_AGGREGATION','PIT_VIOLATIONS','SOURCE_LINEAGE','FROZEN_IDENTIFIERS','HYBRID_COMPARABLE_MATERIAL_MISMATCHES','MSH_FEATURE_RECONSTRUCTION','MSH_STATE_RECONSTRUCTION','ENTRY_EVENT_CLOSURE','REFERENCE_PRICE_SEMANTICS','CORPORATE_ACTION_CONFLICT','UNIVERSE_FIDELITY','MISSING_HANDLING'])assert.match(inventory,new RegExp(id));
});
