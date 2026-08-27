import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('historical EXIT v2 replay workflow is five-session sharded and diagnostic-only',()=>{
  const y=fs.readFileSync('.github/workflows/phase57-p25-exit-v2-historical-replay.yml','utf8');
  for(const d of ['2026-08-19','2026-08-20','2026-08-21','2026-08-24','2026-08-25'])assert.match(y,new RegExp(d));
  assert.match(y,/max-parallel:\s*5/);
  assert.match(y,/run_p25_exit_v2_historical_replay\.mjs/);
  assert.match(y,/reduce_p25_exit_v2_historical_replay_shards\.mjs/);
  assert.match(y,/formalOos/);
  assert.match(y,/promotionEligible/);
  assert.match(y,/freshHoldoutConsumed/);
});

test('historical replay runner and reducer preserve explicit research boundaries',()=>{
  const runner=fs.readFileSync('scripts/run_p25_exit_v2_historical_replay.mjs','utf8');
  const reducer=fs.readFileSync('scripts/reduce_p25_exit_v2_historical_replay_shards.mjs','utf8');
  assert.match(runner,/runP25ExitV2HistoricalReplay/);
  assert.match(runner,/diagnosticOnly:true/);
  assert.match(reducer,/formalOosEvidence:false/);
  assert.match(reducer,/promotionEligible:false/);
  assert.match(reducer,/resultBasedRetuning:false/);
  assert.match(reducer,/freshHoldoutConsumed:false/);
  assert.match(reducer,/deterministicReduce:true/);
});
