import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const path=fileURLToPath(new URL('../windows/Stage-No11MarketSectionReadOnly.ps1',import.meta.url));
const text=fs.readFileSync(path,'utf8');
test('fullwidth RSS correction stages pinned exact source identities and backups',()=>{
 for(const token of [
  'ec4559b353db8e4c01874ba6dcb42b7cbbbe4452',
  '2c10c5c2d17ca1e4dff30d1437d207d368ecf8ce',
  'fd8acc72b4d1dbd7626a932baa8b1c2ff4d12be9',
  '3c52d1eb6930d7d4744176b0492754bc3ab88641',
  '1e3a8e3b7021bea04dd8cebeabe981fcadde61a2',
  'INSTALLED_SOURCE_DIVERGED_REVIEW_REQUIRED','DOWNLOADED_BLOB_MISMATCH',
  'PYTHON_SYNTAX','JAVASCRIPT_SYNTAX','INSTALLED_BLOB_MISMATCH',
  'NO11_SECTION_MARKET_LABEL_FIX=PASS'
 ])assert.ok(text.includes(token),token);
});
test('source-only patch is fail-closed: no Excel COM, trading, source fabrication or kill',()=>{
 for(const pattern of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Stop-Process|\.Kill\s*\(/,/GetActiveObject\s*\(/,/Excel.Application/,
  /orderTransmission\s*=\s*\$true/])assert.doesNotMatch(text,pattern);
 for(const token of ['NO11_SECTION_EXTERNAL_REVIEW=STILL_REQUIRED',
  'NO11_SECTION_SHADOW_PREFLIGHT=NOT_PASSED',
  'NO11_SECTION_RAW_RSS_REWRITTEN=False','ORDER_TRANSMISSION=False'])
  assert.ok(text.includes(token),token);
});
test('Windows installer validates offline without running Excel', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',path,
  '-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_SECTION_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
