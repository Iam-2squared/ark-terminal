import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const repo=fileURLToPath(new URL('../../../',import.meta.url));
const base=path.join(repo,'research/no12-prebuy-causal-runtime-20261011');
const observer=path.join(base,'windows/Observe-No11AccountReadOnly.ps1');
const collector=path.join(base,'windows/Probe-No11Chart50ContinuousReadOnly.ps1');
function powershell(script){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'no11 native io '));
 try{
  const file=path.join(dir,'test.ps1');
  fs.writeFileSync(file,'\ufeff'+script,'utf8');
  const result=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',file],{
   cwd:repo,encoding:'utf8',timeout:45000,
   env:{...process.env,NO11_TEST_REPO:repo,NO11_TEST_ROOT:dir,NO11_TEST_OBSERVER:observer,NO11_TEST_COLLECTOR:collector}
  });
  assert.ifError(result.error);
  assert.equal(result.status,0,result.stdout+'\n'+result.stderr);
  return result.stdout;
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
}

test('read-only native I/O fixes retain atomic replacement and the calendar guard',()=>{
 const a=fs.readFileSync(observer,'utf8'),c=fs.readFileSync(collector,'utf8');
 assert.ok(a.includes('[IO.File]::Replace($tmp,$file,[System.Management.Automation.Language.NullString]::Value)'));
 assert.ok(!a.includes('[IO.File]::Replace($tmp,$file,$null)'));
 assert.ok(c.includes('try{$isDay=@($calendar | & node --input-type=module - $session)}'));
 assert.ok(c.includes('isJpxCashTradingDay(process.argv[2])'));
 assert.ok(c.includes("throw 'NO11_C50_NOT_JPX_CASH_TRADING_DAY'"));
 assert.ok(c.includes("throw 'NO11_C50_ACTUAL_CHART_CAP_EXCEEDED'"));
});

test('Windows PowerShell 5.1 reproduces old second-write failure; fixed Publish preserves UTF-8 and last good snapshot on replacement failure',
 {skip:process.platform!=='win32'},()=>{
 const output=powershell(String.raw`
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -ne 5){throw 'WINDOWS_POWERSHELL_5_REQUIRED'}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($env:NO11_TEST_OBSERVER,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'OBSERVER_PARSE'}
$functions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Publish'},$false))
if($functions.Count -ne 1){throw 'PUBLISH_COUNT'}
$source=$functions[0].Extent.Text
. ([scriptblock]::Create($source))
$legacy=$source.Replace('function Publish(','function LegacyPublish(').Replace('[System.Management.Automation.Language.NullString]::Value','$null')
. ([scriptblock]::Create($legacy))
$dir=Join-Path $env:NO11_TEST_ROOT 'space 日本語'
[void][IO.Directory]::CreateDirectory($dir)
$old=Join-Path $dir 'legacy.json'
LegacyPublish $old @{sequence=1}
$reproduced=$false
try{LegacyPublish $old @{sequence=2}}catch{$reproduced=$true}
if(-not $reproduced){throw 'LEGACY_SECOND_WRITE_NOT_REPRODUCED'}
if((Get-Content -LiteralPath $old -Raw -Encoding UTF8|ConvertFrom-Json).sequence -ne 1){throw 'LEGACY_LAST_GOOD_LOST'}
$file=Join-Path $dir 'snapshot.json'
foreach($n in 1..3){
 Publish $file ([ordered]@{sequence=$n;label='特定';orderTransmission=$false})
 $data=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
 if($data.sequence -ne $n -or $data.label -cne '特定' -or $data.orderTransmission -ne $false){throw 'PUBLISH_CONTENT'}
}
$before=[Convert]::ToBase64String([IO.File]::ReadAllBytes($file))
$lock=[IO.File]::Open($file,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
$failed=$false
try{try{Publish $file @{sequence=4}}catch{$failed=$true}}finally{$lock.Dispose()}
if(-not $failed){throw 'LOCKED_DESTINATION_NOT_REJECTED'}
if([Convert]::ToBase64String([IO.File]::ReadAllBytes($file)) -cne $before){throw 'LAST_GOOD_CHANGED_ON_FAILURE'}
if(@(Get-ChildItem -LiteralPath $dir -Filter '*.tmp').Count -ne 0){throw 'TEMP_FILES_LEAKED'}
Publish $file @{sequence=4}
if((Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json).sequence -ne 4){throw 'RECOVERY_WRITE_FAILED'}
Write-Host 'NO11_PUBLISH_REAL_PS51_REGRESSION=PASS'
`);
 assert.match(output,/NO11_PUBLISH_REAL_PS51_REGRESSION=PASS/);
});

test('Windows PowerShell 5.1 executes the actual collector calendar block without Excel; old eval quoting fails and stdin retains weekday/weekend rejection',
 {skip:process.platform!=='win32'},()=>{
 const output=powershell(String.raw`
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -ne 5){throw 'WINDOWS_POWERSHELL_5_REQUIRED'}
$repo=$env:NO11_TEST_REPO
$text=[IO.File]::ReadAllText($env:NO11_TEST_COLLECTOR)
$first=$text.IndexOf('$calendar=')
$last=$text.IndexOf('if([string]::IsNullOrWhiteSpace($PreparedPlanFile))',$first)
if($first -lt 0 -or $last -le $first){throw 'CALENDAR_BOUNDARY'}
$body=$text.Substring($first,$last-$first)
$check=[scriptblock]::Create($body)
$session='2026-10-26'
& $check
$session='2026-10-24'
$weekendRejected=$false
try{& $check}catch{if($_.Exception.Message -ceq 'NO11_C50_NOT_JPX_CASH_TRADING_DAY'){$weekendRejected=$true}else{throw}}
if(-not $weekendRejected){throw 'WEEKEND_GUARD_REMOVED'}
$session='2026-10-26'
$legacy=$body.Replace('process.argv[2]','process.argv[1]').Replace('$calendar | & node --input-type=module - $session','& node --input-type=module -e $calendar $session')
$legacyFailed=$false
try{& ([scriptblock]::Create($legacy)) 2>$null}catch{$legacyFailed=$true}
if(-not $legacyFailed){throw 'LEGACY_EVAL_FAILURE_NOT_REPRODUCED'}
Write-Host 'NO11_CALENDAR_REAL_PS51_REGRESSION=PASS'
`);
 assert.match(output,/NO11_CALENDAR_REAL_PS51_REGRESSION=PASS/);
});
