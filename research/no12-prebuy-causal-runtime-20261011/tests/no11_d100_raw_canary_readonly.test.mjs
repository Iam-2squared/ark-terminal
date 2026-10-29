import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const script=fileURLToPath(new URL('../windows/Diagnose-No11D100RawRowCanaryReadOnly.ps1',import.meta.url));
const body=readFileSync(script,'utf8');
test('five canaries only, preserving full original daily source and original workbook identities',()=>{
 for(const marker of [
  'MALFORMED_SOURCE_ROWS=403|UNAVAILABLE=26',
  'SOURCE_SHA',
  'PLAN_NOT_OCT28_429',
  'EXISTING_RECEIPTS',
  'TWO_ORIGINAL_WORKBOOKS_REQUIRED',
  'EXCEL7_NOT_UNIQUE',
  'FORMULA_SCAN_LIMIT',
  "Start-Sleep -Seconds $WarmupSeconds",
  "Range('A3:J102').Value2",
  "invalidFuture",
  "invalidInWindowOrEarlier",
  "invalidDate",
  "full76",
  'NO11_RAW_CANARY_HISTORICAL_403_RECEIPTS=UNCHANGED_NOT_CERTIFIED',
  'NO11_RAW_CANARY_SHADOW=BLOCKED_PENDING_VERIFIED_SOURCE',
  'ORDER_TRANSMISSION=False'
 ])assert.ok(body.includes(marker),marker);
 assert.match(body,/\$idx=@\(0,101,201,301,402\)/);
 assert.doesNotMatch(body,/Remove-Item|Stop-Process|Kill\s*\(|RssStockOrder\s*\(|RssCancelOrder\s*\(|\.Save\(/i);
 assert.match(body,/\.Close\(\$false\)/);
});
test('Windows PowerShell 5.1 raw-row classification selftest uses synthetic data only',{
 skip:process.platform!=='win32'
},()=>{
 const p=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',script,'-OfflineSelfTest'],
  {encoding:'utf8',timeout:20000});
 assert.equal(p.status,0,(p.stdout??'')+'\n'+(p.stderr??''));
 assert.match(p.stdout,/NO11_RAW_CANARY_OFFLINE_SELFTEST=PASS/);
 assert.match(p.stdout,/NO11_RAW_CANARY_EXISTING_RECEIPTS_TOUCHED=False/);
 assert.match(p.stdout,/ORDER_TRANSMISSION=False/);
});
