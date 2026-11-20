import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
test('Entry Location Study: synthetic causality and saved evidence; no model or provider',()=>{
  const p=spawnSync('python3',['-m','unittest','scripts.test_phase57_entry_location_study','scripts.test_phase57_entry_location_audit','-v'],
    {cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},timeout:120000});
  assert.equal(p.status,0,p.stdout+p.stderr);
});
