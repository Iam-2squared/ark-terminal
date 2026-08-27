import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const repoRoot=path.resolve(here,'../..');
const read=p=>fs.readFileSync(path.join(repoRoot,p),'utf8');

test('historical EXIT v2 replay workflow is five-session sharded and diagnostic-only',()=>{
  const y=read('.github/workflows/phase57-p25-exit-v2-historical-replay.yml');
  for(const d of ['2026-08-19','2026-08-20','2026-08-21','2026-08-24','2026-08-25'])assert.match(y,new RegExp(d));
  assert.match(y,/max-parallel:\s*5/);
  assert.match(y,/run_p25_exit_v2_historical_replay\.mjs/);
  assert.match(y,/reduce_p25_exit_v2_historical_replay_shards\.mjs/);
  assert.match(y,/formalOos/);
  assert.match(y,/promotionEligible/);
  assert.match(y,/freshHoldoutConsumed/);
});

test('historical replay runner and reducer preserve explicit research boundaries',()=>{
  const runner=read('scripts/run_p25_exit_v2_historical_replay.mjs');
  const reducer=read('scripts/reduce_p25_exit_v2_historical_replay_shards.mjs');
  assert.match(runner,/runP25ExitV2HistoricalReplay/);
  assert.match(runner,/diagnosticOnly:true/);
  assert.match(reducer,/formalOosEvidence:false/);
  assert.match(reducer,/promotionEligible:false/);
  assert.match(reducer,/resultBasedRetuning:false/);
  assert.match(reducer,/freshHoldoutConsumed:false/);
  assert.match(reducer,/deterministicReduce:true/);
});
