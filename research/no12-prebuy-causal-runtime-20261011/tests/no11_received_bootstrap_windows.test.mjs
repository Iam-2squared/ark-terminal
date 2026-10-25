import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const collector=path.join(base,'windows/Probe-No11Chart50ContinuousReadOnly.ps1');
const launcher=path.join(base,'windows/Run-No11ReceivedSessionReadOnly.ps1');
const py=fs.readFileSync(path.join(base,'tools/no11_received_session_bootstrap.py'),'utf8');
const powershell=process.platform==='win32'?'powershell.exe':process.env.ARK_NO11_PWSH;

test('paired launch keeps original broker and workbook safety restrictions',()=>{
 const source=fs.readFileSync(collector,'utf8');
 assert.match(source,/NO11_C50_ACTUAL_CHART_CAP_EXCEEDED/);
 assert.match(source,/NO11_C50_ACTUAL_MARKET_CAP_EXCEEDED/);
 assert.match(source,/NO11_C50_TWO_ORIGINAL_WORKBOOKS_REQUIRED/);
 assert.match(source,/ARK_NO11_C50_COLLECTOR_READY_V1/);
 assert.match(source,/ARK_NO11_C50_COLLECTOR_CLOSED_V1/);
 assert.match(source,/planFileSha256=\$planBytesSha/);
 assert.match(source,/temporaryWorkbookClosed=\$temporaryClosed/);
 assert.match(source,/\$book\.Close\(\$false\)/);
 assert.match(source,/C50Wait \$delay/);
 assert.doesNotMatch(source,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.SaveAs\s*\(|\.Save\s*\(|\.Quit\s*\(|Stop-Process|taskkill/i);
 assert.match(py,/preflight-only/);
 assert.match(py,/COLLECTOR_CLEANUP_NOT_CONFIRMED/);
 assert.match(py,/PREVIOUS_CLEANUP_REQUIRES_REVIEW/);
 assert.doesNotMatch(py,/\.kill\(|\.terminate\(|shell\s*=\s*True|productionReady['"]?\s*:\s*True/);
 assert.ok([...source].every(c=>c.charCodeAt(0)<128));
});

test('Windows one-click launcher parses without models Excel or network',{skip:!powershell},()=>{
 const r=spawnSync(powershell,['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
  '-File',launcher,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
 assert.match(r.stdout,/NO11_BOOTSTRAP_WINDOWS_OFFLINE_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_BOOTSTRAP_COLLECTOR_STARTED=False/);
 assert.match(r.stdout,/NO11_BOOTSTRAP_ORDER_ID_ARGUMENT_SELFTEST=PASS/);
});

test('supplemental workbook and unsaved temporary identity have offline validation',{skip:!powershell},()=>{
 const r=spawnSync(powershell,['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
  '-File',collector,'-OfflineSelfTest'],{encoding:'utf8',timeout:25000});
 assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
 assert.match(r.stdout,/NO11_C50_SUPPLEMENTAL_BOOK_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_C50_TEMPORARY_IDENTITY_SELFTEST=PASS/);
 assert.match(r.stdout,/NO11_C50_BROKER_ACCESS=False/);
});

test('Windows collector stop interrupts minute wait and atomically publishes control receipt',{skip:process.platform!=='win32'},()=>{
 const code=String.raw`
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($env:ARK_TEST_COLLECTOR,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw 'PARSE_FAILED'}
$names=@('C50Stopped','C50Wait','WriteControl','CheckControlPath')
$functions=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true)
if($functions.Count -ne 4){throw 'CONTROL_FUNCTIONS_MISSING'}
foreach($f in $functions){Invoke-Expression $f.Extent.Text}
$repo=(Get-Location).Path
$temp=Join-Path $env:TEMP ('no11-control-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 $StopFile=Join-Path $temp 'stop'
 $ready=Join-Path $temp 'ready.json'
 CheckControlPath $StopFile
 CheckControlPath $ready
 [IO.File]::WriteAllText($StopFile,'STOP')
 $watch=[Diagnostics.Stopwatch]::StartNew()
 $continue=C50Wait 60000
 if($continue -or $watch.ElapsedMilliseconds -gt 5000){throw 'STOP_NOT_COOPERATIVE'}
 WriteControl $ready ([ordered]@{schemaId='TEST';orderTransmission=$false})
 $v=Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json
 if($v.schemaId -cne 'TEST' -or $v.orderTransmission -ne $false){throw 'CONTROL_CORRUPT'}
 if(Test-Path -LiteralPath ($ready+'.pending-'+$PID)){throw 'PENDING_NOT_RENAMED'}
 $blocked=$false;try{CheckControlPath $ready}catch{$blocked=$true}
 if(-not $blocked){throw 'EXISTING_CONTROL_WAS_ACCEPTED'}
 Write-Host 'NO11_BOOTSTRAP_CONTROL_OFFLINE=PASS'
}finally{Remove-Item -LiteralPath $temp -Force -Recurse}
`;
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-Command',code],
  {encoding:'utf8',timeout:20000,env:{...process.env,ARK_TEST_COLLECTOR:collector}});
 assert.equal(r.status,0,r.stderr+'\n'+r.stdout);
 assert.match(r.stdout,/NO11_BOOTSTRAP_CONTROL_OFFLINE=PASS/);
});
