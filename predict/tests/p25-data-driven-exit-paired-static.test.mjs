import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source=fs.readFileSync(new URL('../daytrade/phase57-p25-data-driven-exit-multisession.js',import.meta.url),'utf8');

test('paired evaluator is hard-wired to DYNAMIC_50 and does not retune Entry',()=>{
  assert.match(source,/includes\('DYNAMIC_50'\)/);
  assert.match(source,/exactDynamic50Only:true/);
  assert.match(source,/sameFrozenEntryAsFixed:true/);
  assert.match(source,/fixedBaselineUntouched:true/);
  assert.match(source,/resultBasedRetuning:false/);
  assert.match(source,/fixedHorizonUsedAsDecisionInput:false/);
});
