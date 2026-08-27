import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';

const read=p=>fs.readFileSync(new URL(`../../${p}`,import.meta.url),'utf8');

test('EXIT v3 persistence adapter and research UI remain fail-closed',()=>{
  const script=read('scripts/persist_p25_exit_v3_home.mjs');
  const home=read('paper-equity-home.js');
  const page=read('paper-equity-page.js');
  const workflow=read('.github/workflows/phase57-p25-exit-v3-persist-home.yml');
  assert.match(script,/EXPECTED_SOURCE_RUN_ID=33037297017/);
  assert.match(script,/pairedCount:r\.summary\.pairedCount/);
  assert.match(script,/noV1V2ForwardPersistence:true/);
  assert.match(script,/freshHoldoutConsumed:false/);
  assert.match(home,/"EXIT_V3"/);
  assert.match(home,/EXIT v3 primary frozen candidate/);
  assert.match(page,/"EXIT_V3"/);
  assert.match(workflow,/automation\/p25-exit-v3-data/);
  assert.match(workflow,/No v1\/v2 forward persistence/);
  for(const p of ['scripts/persist_p25_exit_v3_home.mjs','paper-equity-home.js','paper-equity-page.js']){
    const r=spawnSync(process.execPath,['--check',new URL(`../../${p}`,import.meta.url).pathname],{encoding:'utf8'});
    assert.equal(r.status,0,`${p} syntax: ${r.stderr}`);
  }
});
