import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const p=fileURLToPath(new URL('../windows/Repair-No11MarketSectionLocalPreserve.ps1',import.meta.url));
const s=fs.readFileSync(p,'utf8');
test('recognizes observed local-only source and exact two GitHub source pins',()=>{
 for(const m of [
  'e03b6fc28aa5fba793aacc243002de89afa2a8d5',
  '2c10c5c2d17ca1e4dff30d1437d207d368ecf8ce',
  'c463f5d3a59c893acc062161eabb11f131565e6b',
  '3c52d1eb6930d7d4744176b0492754bc3ab88641',
  '1957469b17a7aa68799282706ecadad07c9156e3',
  '1e3a8e3b7021bea04dd8cebeabe981fcadde61a2',
  'LOCAL_DICTIONARY_UNEXPECTED','LOCAL_SOURCE_HAS_CHANGED','PINNED_FILE_CHANGED',
  'INSTALLED_HASH_MISMATCH','NO11_SECTION_LOCAL_PRESERVED=PASS'
 ])assert.ok(s.includes(m),m);
});
test('retains unrelated local code with rollback and never touches Excel or orders',()=>{
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /Excel.Application|GetActiveObject\s*\(/,/Stop-Process|\.Kill\s*\(/,
  /orderTransmission\s*=\s*\$true/])assert.doesNotMatch(s,re);
 for(const token of ['NO11_SECTION_RAW_REFERENCE_UNCHANGED=True',
  'NO11_SECTION_EXTERNAL_REVIEW=STILL_REQUIRED',
  'NO11_SECTION_SHADOW_PREFLIGHT=NOT_PASSED','ORDER_TRANSMISSION=False'])
  assert.ok(s.includes(token),token);
});
test('Windows offline one-line-patch self-test has no Excel access', {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass',
  '-File',p,'-OfflineSelfTest'],{encoding:'utf8',timeout:25000});
 assert.equal(r.status,0,(r.stdout||'')+'\n'+(r.stderr||''));
 assert.match(r.stdout,/NO11_SECTION_LOCAL_PRESERVE_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/ORDER_TRANSMISSION=False/);
});
