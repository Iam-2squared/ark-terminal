import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Run-No11Oct28QuickStartReadOnly.ps1',import.meta.url));
const s=fs.readFileSync(file,'utf8');
test('same-day helper reuses real Classic settings and only clones virtual account session',()=>{
 for(const token of [
  "shadow-oneclick-classic\\launcher-settings.json",
  'shadow-oneclick\\launcher-settings.json',
  'FULL_SYNTHETIC_H235_CAPITAL_EXIT_REQUIRED',
  'EXTERNAL_REVIEW_SOURCE_MISSING','EXTERNAL_DOCUMENTS_MISSING',
  'ARK_NO11_OBSERVED_SHADOW_ACCOUNT_V1',
  'NEXT_FRESH_RECEIVED_CLOSE_SIMULATION',
  'NO11_OCT28_QUICKSTART_SIMULATOR_SESSION=COPIED_SAME_FUNDS_SYNTHETIC_ONLY',
  'NO11_OCT28_QUICKSTART_SECURITY_EVIDENCE=SUPPLIED_NOT_CERTIFIED_BY_WRAPPER',
  'Run-No11Oct28AfternoonShadowReadOnly.ps1'
 ])assert.ok(s.includes(token),token);
 assert.ok(!s.includes('2026-10-29'));
});
test('never guesses real funds or promotes source review or sends orders',()=>{
 for(const pattern of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /orderTransmission\s*=\s*\$true/,/productionReady\s*=\s*\$true/,
  /Stop-Process|\.Kill\s*\(/,/Excel.Application|GetActiveObject\s*\(/])
  assert.doesNotMatch(s,pattern);
 assert.ok(s.includes('ORDER_TRANSMISSION=False'));
});
test('Windows helper offline source selftest', {skip:process.platform!=='win32'},()=>{
 const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(p.status,0,(p.stdout||'')+'\n'+(p.stderr||''));
 assert.match(p.stdout,/NO11_OCT28_QUICKSTART_OFFLINE_SELFTEST=PASS/);
});
