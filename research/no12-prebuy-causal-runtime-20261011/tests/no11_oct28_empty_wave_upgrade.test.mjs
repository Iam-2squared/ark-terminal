import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Upgrade-No11Oct28EmptyWaveRetryReadOnly.ps1',import.meta.url));
const src=fs.readFileSync(file,'utf8');
test('bounded live RSS retry update is pinned and refuses running collector',()=>{
 for(const x of ['1c81294e8542043b1208c71d78e4583921088394',
  'bd8df4a0f40e0f2eafdf60958b9e1d63571eefb7',
  'RUNNING_COLLECTOR_MUST_FINISH','SOURCE_POWERSHELL_PARSE_FAILED',
  'DOWNLOADED_SOURCE_HASH_MISMATCH','POST_INSTALL_HASH_MISMATCH',
  'NO11_EMPTY_RETRY_UPGRADE_LIMIT=2_EMPTY_WAVE_RETRIES',
  'NO11_EMPTY_RETRY_UPGRADE_EXISTING_20_CAPTURED_SOURCES_RETAINED=True'])
  assert.ok(src.includes(x),x);
 assert.match(src,/\[IO.File\]::Copy\(\$backup,\$destination,\$true\)/);
});
test('does not open, save or stop Excel and has no order path',()=>{
 for(const re of [/GetActiveObject\s*\(/,/Excel.Application/,
  /RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Stop-Process|\.Kill\s*\(/])assert.doesNotMatch(src,re);
 assert.ok(src.includes('ORDER_TRANSMISSION=False'));
});
test('Windows offline selftest of incremental retry updater',{skip:process.platform!=='win32'},()=>{
 const result=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(result.status,0,(result.stdout||'')+'\n'+(result.stderr||''));
 assert.match(result.stdout,/NO11_EMPTY_RETRY_UPGRADE_OFFLINE_SELFTEST=PASS/);
});
