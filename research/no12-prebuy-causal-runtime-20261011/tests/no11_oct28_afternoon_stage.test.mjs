import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const p=fileURLToPath(new URL('../windows/Stage-No11Oct28AfternoonReadOnly.ps1',import.meta.url));
const c=fs.readFileSync(p,'utf8');
test('protects original bootstrap with pinned old/new hashes and never overwrites divergent local files',()=>{
 for(const x of ['298d3c2640547956836c0a5a9ace642cff7ebcb1',
 'ebb8a025294faecd32d5717c41719a767a94c700',
 '35cdeedc9151fcb57fde32c6373331afea43f05b',
 '7763beb8abbdf0935c96a66198ae498ef428df9b',
 'c1d8514fa17b8169576427403dd687acbf62b5f5',
 'LOCAL_SOURCE_DIVERGED_INSPECT_FIRST','STAGED_GIT_BLOB_MISMATCH',
 'INSTALLED_HASH_MISMATCH','NO11_TODAY_BRIDGE_STAGE=PASS'])assert.ok(c.includes(x),x);
});
test('stages sources only, restores backups and never sends orders',()=>{
 assert.ok(c.includes('[IO.File]::Copy($item.backup,$item.dest,$true)'));
 for(const bad of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Excel.Application|GetActiveObject\s*\(/,/orderTransmission\s*=\s*\$true/,
  /Stop-Process|\.Kill\s*\(/])assert.doesNotMatch(c,bad);
});
test('Windows offline installer needs no Excel', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',p,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_TODAY_STAGE_OFFLINE_SELFTEST=PASS/);
});
