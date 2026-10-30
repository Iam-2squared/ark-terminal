import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Repair-No11Oct28BridgeLocalPreserve.ps1',import.meta.url));
const code=fs.readFileSync(file,'utf8');
test('local-only bootstrap source is patched, not replaced with an assumed Git blob',()=>{
 for(const word of [
  'no11_patch_weekly_bootstrap_local.py',
  'no11_verified_weekly_shadow_scope.mjs',
  'Run-No11Oct28AfternoonShadowReadOnly.ps1',
  'GIT_HASH_FAILED',
  'DOWNLOADED_SOURCE_HASH_MISMATCH',
  'ALREADY_EXISTING_NEW_FILE_DIVERGED',
  'SHADOW_RUNNING_DO_NOT_PATCH',
  'NO11_TODAY_BRIDGE_STAGE=PASS_LOCAL_MODIFICATIONS_PRESERVED',
  'NO11_TODAY_BRIDGE_G1_ACTUAL=NOT_CHECKED_BY_INSTALLER'
 ])assert.ok(code.includes(word),word);
 assert.ok(!code.includes('ebb8a025294faecd32d5717c41719a767a94c700'));
 assert.ok(code.includes('NO11_BOOTSTRAP_PATCH_STAGED=')===false); // CLI owns this marker
});
test('backup and rollback retain local code, while Excel and orders stay untouched',()=>{
 assert.match(code,/\[IO\.File\]::Copy\(\$entry\.dest,\$entry\.backup,\$false\)/);
 assert.match(code,/\[IO\.File\]::Copy\(\$entry\.backup,\$entry\.dest,\$true\)/);
 for(const ban of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /GetActiveObject\s*\(/,/Excel\.Application/,
  /Stop-Process|\.Kill\s*\(/,/orderTransmission\s*=\s*\$true/])
  assert.doesNotMatch(code,ban);
});
test('Windows offline installation selftest does not touch physical Excel', {skip:process.platform!=='win32'},()=>{
 const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],
 {encoding:'utf8',timeout:30000});
 assert.equal(p.status,0,(p.stdout||'')+'\n'+(p.stderr||''));
 assert.match(p.stdout,/NO11_OCT28_LOCAL_BRIDGE_OFFLINE_SELFTEST=PASS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
