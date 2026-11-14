import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const file=fileURLToPath(new URL('../windows/Run-No11ReadOnlyConnectionCheck.ps1',import.meta.url));
test('connection check is finite, requires manual order-off confirmation, and does not claim Shadow or recovery',()=>{
 const text=fs.readFileSync(file,'utf8');
 assert.ok(text.includes("if(-not $ConfirmOrderOff){throw 'NO11_CONNECTION_CONFIRM_EXCEL_ORDER_OFF_REQUIRED'}"));
 assert.ok(text.includes("'-Samples','3'"));
 assert.ok(text.includes("'-Samples','4'"));
 assert.ok(text.includes('shadowTested=$false;recoveryTested=$false;liveOrdersTested=$false'));
 assert.ok(!/RssStockOrder\s*\(|RssCancelOrder\s*\(|Invoke-No11MsiiOrder\.ps1|Stop-Process|\.Kill\(/i.test(text));
});
test('connection check preserves multiline native stderr and nonzero exit code in real Windows PowerShell 5.1',
 {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],{
  encoding:'utf8',cwd:path.dirname(file),timeout:45000
 });
 assert.ifError(r.error);
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
 assert.match(r.stdout,/NO11_CONNECTION_LOGGING_OFFLINE_SELFTEST=PASS/);
});
