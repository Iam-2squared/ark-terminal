import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const file=fileURLToPath(new URL('../windows/Stage-No11FutureRssAutoGroupsReadOnly.ps1',import.meta.url));
const src=fs.readFileSync(file,'utf8');

test('future-only auto-group stage uses exact two-file old/new Git pins and guarded install',()=>{
 for(const marker of [
  'Run-No11WeeklyCandidateRefreshReadOnly.ps1',
  'Prepare-No11WeeklyAfterCloseReadOnly.ps1',
  'b4dfbc4556e3cc54002d5d16c62f465b4f463975',
  '78eee12cefa77abb37ec3f442c21efe3ca1ed7f2',
  '9b2d6f4e5876c1692406f4a2dcff3000dbd515b3',
  '3b18343f05043108af328863aa02fde5f8428a19',
  'COLLECTOR_STILL_RUNNING_FINISH_TODAY_FIRST',
  'LOCAL_SOURCE_DIVERGED_INSPECT_FIRST',
  'PINNED_DOWNLOAD_HASH_FAILED',
  'POWERSHELL_SOURCE_PARSE',
  'NO11_RSS_AUTOGROUP_DEFAULT=100_SYMBOL_GROUPS_30_PHYSICAL_MAX',
  'NO11_RSS_AUTOGROUP_CHART_FUNCTIONS=MAX50_WITH_3_RESERVED',
  'NO11_RSS_AUTOGROUP_TODAY_SOURCE_MODIFIED=False',
  'NO11_RSS_AUTOGROUP_INSTALL=PASS'
 ])assert.ok(src.includes(marker),marker);
 assert.ok(src.includes('[IO.File]::Copy($file.backup,$file.src,$true)'));
});
test('installer never executes real RSS, changes Frozen, sends orders, or shuts down Excel',()=>{
 for(const bad of [
  /Rss(?:StockOrder|CancelOrder|MarginOpenOrder)\s*\(/,
  /Excel\.Application|GetActiveObject\s*\(/,
  /Stop-Process|\.Kill\s*\(/,
  /git\s+(?:reset|checkout)/,
  /orderTransmission\s*=\s*\$true/,
 ])assert.doesNotMatch(src,bad);
 assert.ok(src.includes('ORDER_TRANSMISSION=False'));
});
test('Windows future installer selftest is offline and source-only', {skip:process.platform!=='win32'},()=>{
 const run=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',file,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(run.status,0,(run.stdout||'')+'\n'+(run.stderr||''));
 assert.match(run.stdout,/NO11_RSS_AUTOGROUP_INSTALL_OFFLINE_SELFTEST=PASS/);
 assert.match(run.stdout,/ORDER_TRANSMISSION=False/);
});
