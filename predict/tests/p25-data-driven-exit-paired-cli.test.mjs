import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const cli=fs.readFileSync(new URL('../../scripts/run_p25_data_driven_exit_paired.mjs',import.meta.url),'utf8');
test('paired CLI invokes exact data-driven multisession evaluator and emits safety',()=>{
  assert.match(cli,/runP25DataDrivenExitMultisession/);
  assert.match(cli,/P25_DATA_DRIVEN_PAIRED_SAFETY/);
  assert.match(cli,/resultBasedRetuning:false/);
});
