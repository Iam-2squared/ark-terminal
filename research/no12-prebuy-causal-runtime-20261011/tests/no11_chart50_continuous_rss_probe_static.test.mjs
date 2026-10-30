import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const script=path.resolve(path.dirname(fileURLToPath(import.meta.url)),
 '../windows/Probe-No11Chart50ContinuousReadOnly.ps1');
const source=fs.readFileSync(script,'utf8');
test('G1 Chart50 probe uses only permitted market/chart reads, no account or order writes',()=>{
 assert.match(source,/NO11_C50_ACTUAL_CHART_CAP_EXCEEDED/);
 assert.match(source,/NO11_C50_ACTUAL_MARKET_CAP_EXCEEDED/);
 assert.match(source,/ValidateRange\(2,390\)/);
 assert.match(source,/NO11_C50_ACCOUNT_UI_MUST_BE_STOPPED/);
 assert.match(source,/NO11_C50_PRESCREEN_RECEIPT_MISSING/);
 assert.match(source,/No11C50Attach/);
 assert.match(source,/RssChart/);
 assert.match(source,/RssMarket/);
 assert.match(source,/SaveSnapshot/);
 assert.match(source,/chartPlanSha256=\$plan\.planSha256/);
 assert.match(source,/shadowOnly=\$true;productionReady=\$false;orderTransmission=\$false/);
 assert.match(source,/\.Close\(\$false\)/);
 assert.doesNotMatch(source,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.SaveAs\s*\(|\.Save\s*\(|\.Quit\s*\(/);
 assert.equal([...source].every(c=>c.charCodeAt(0)<=127),true);
});
test('PowerShell 5.1 offline formula parse, timestamp and injection selftests',()=>{
 if(process.platform!=='win32')return;
 const result=spawnSync('powershell.exe',
  ['-NoProfile','-ExecutionPolicy','Bypass','-File',script,
   '-OfflineSelfTest'],
  {encoding:'utf8',timeout:25000,windowsHide:true});
 assert.equal(result.status,0,result.stderr+'\n'+result.stdout);
 assert.match(result.stdout,/NO11_C50_CONTINUOUS_OFFLINE_SELFTEST=PASS/);
 assert.match(result.stdout,/NO11_C50_BROKER_ACCESS=False/);
 assert.match(result.stdout,/ORDER_TRANSMISSION=False/);
});
