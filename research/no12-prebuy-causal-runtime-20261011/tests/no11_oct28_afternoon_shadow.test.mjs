import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Run-No11Oct28AfternoonShadowReadOnly.ps1',import.meta.url));
const body=fs.readFileSync(file,'utf8');
test('Oct28 afternoon uses actual Oct27 weekly G1 and original same-day Shadow runner',()=>{
 for(const token of [
  "SESSION_NOT_OCT28","weekly-refresh-2026-10-27-*",
  'no11_verified_weekly_shadow_scope.mjs','--weekly-source-run',
  'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED',
  'no11_previous_archive_context.py','Capture-No11SessionReferenceReadOnly.ps1',
  'no11_prepare_received_inputs.py','Run-No11ReceivedSessionReadOnly.ps1',
  'NO11_TODAY_SHADOW_RESULT=','MASTER_PREVIOUS_CONTEXT_ASSEMBLY_FAILED'
 ])assert.ok(body.includes(token),token);
 assert.doesNotMatch(body,/18:00|2026-10-29|Run-No11Oct29/);
});
test('no auto trading or fabricated external certification; explicit manual StartShadow',()=>{
 assert.ok(body.includes('$StartShadow'));
 assert.ok(body.includes('INDEPENDENT_SECURITY_EVIDENCE'));
 assert.ok(body.includes('REFERENCE=OBSERVED_NOT_EXTERNALLY_REVIEWED'));
 assert.ok(body.includes('ORDER_TRANSMISSION=False'));
 for(const re of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
  /orderTransmission\s*=\s*\$true/,/productionReady\s*=\s*\$true/,
  /Stop-Process|\.Kill\s*\(/])assert.doesNotMatch(body,re);
});
test('auto discovery never silently accepts arbitrary source or stale day',()=>{
 for(const marker of [
  'ResolveDailySource',
  "'daily-2026-10-26-*' '2026-10-26' 4328 'SEED_20261026'",
  "'weekly-refresh-2026-10-27-*' '2026-10-27' 429 'REFRESH_20261027'",
  "'WRONG_'+$role+'_SESSION_OR_SCOPE'",
  "NO11_TODAY_SHADOW_MISSING=",
  "NO11_TODAY_SHADOW_MISSING_PATH=",
  "NO11_TODAY_SHADOW_FOUND_",
  "AMBIGUOUS_REQUIRE_EXPLICIT_PATH=True",
 ])assert.ok(body.includes(marker),marker);
 assert.ok(body.includes('WEEKLY_G1_CHART_NOT_VERIFIED'));
});
test('Windows offline selftest is physical-source-free', {skip:process.platform!=='win32'},()=>{
 const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,
 '-OfflineSelfTest'],{encoding:'utf8',timeout:25000});
 assert.equal(p.status,0,(p.stdout||'')+'\n'+(p.stderr||''));
 assert.match(p.stdout,/NO11_TODAY_SHADOW_OFFLINE_SELFTEST=PASS/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
