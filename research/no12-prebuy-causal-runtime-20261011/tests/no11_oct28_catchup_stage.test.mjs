import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('../windows/Stage-No11Oct28CatchUpReadOnly.ps1',import.meta.url));
const src=fs.readFileSync(script,'utf8');
test('additive helper staging never overwrites the local originals',()=>{
 for(const line of [
  'no11_weekly_g1_catchup_20261028.mjs',
  'Run-No11WeeklyCandidateCatchUpReadOnly.ps1',
  'Run-No11Oct28CatchUpReadOnly.ps1',
  'a2421d4f4ad4d596f771c6732a3b38610496637a',
  '1c81294e8542043b1208c71d78e4583921088394',
  'a0b17c2a1dcceced006432cc7af29415fdf1244b',
  'EXISTING_HELPER_DIVERGED',
  'DOWNLOAD_HASH_MISMATCH',
  'RACE_DESTINATION_APPEARED',
  'NO11_OCT28_CATCHUP_STAGE_ORIGINAL_FILES_CHANGED=False',
  'NO11_OCT28_CATCHUP_STAGE_ORDER_TRANSMISSION=False'
 ])assert.ok(src.includes(line),line);
 assert.doesNotMatch(src,/\bCopy-Item\b|git\s+pull|git\s+reset|git\s+checkout|RssStockOrder\s*\(/);
});
test('Windows offline selftest never starts Excel or RSS', {skip:process.platform!=='win32'},()=>{
 const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:25000});
 assert.equal(p.status,0,(p.stdout||'')+'\n'+(p.stderr||''));
 assert.match(p.stdout,/NO11_CATCHUP_STAGE_OFFLINE_SELFTEST=PASS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
