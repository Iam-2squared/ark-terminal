import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const win=path.join(root,'research/no12-prebuy-causal-runtime-20261011/windows');
const collector=path.join(win,'Probe-No11Chart50ContinuousReadOnly.ps1');
const runner=path.join(win,'Run-No11ReadOnlyConnectionCheck.ps1');
test('growing chart read retains the initial RSS formula, causal bar filter, and capacity guard',()=>{
 const s=fs.readFileSync(collector,'utf8');
 assert.ok(s.includes('$growing=ReadGrowingChart $item.sheet $HistoryBars'));
 assert.ok(s.includes('$z -lt $growing.rowLimit'));
 assert.ok(s.includes('$limit=$initialBars+390+2'));
 assert.ok(s.includes("throw 'NO11_C50_GROWING_CHART_OVERFLOW'"));
 assert.ok(s.includes('if($start.AddMinutes(1) -gt $chartSeen){continue}'));
 assert.ok(s.includes("throw 'NO11_C50_ACTUAL_CHART_CAP_EXCEEDED'"));
 assert.ok(!s.includes("$series=$item.sheet.Range(('A3:J{0}' -f ($HistoryBars+2))).Value2"));
 assert.ok(s.includes("return ('=RssChart($A$2:$J$2,\"{0}\",\"1M\",{1})' -f $s,$HistoryBars)"));
});
test('connection result is checkpointed; ZIP scan removed; zero Va cannot pass',()=>{
 const s=fs.readFileSync(runner,'utf8');
 assert.ok(!/ZipFile|zip\.Entries| -Wait\b/.test(s));
 assert.ok(s.includes('$p.WaitForExit(200)'));
 assert.ok(s.includes('NO11_CONNECTION_TIMEOUT='));
 assert.ok(s.includes('cleanup-required.json'));
 assert.ok(s.includes('NO11_CONNECTION_PREVIOUS_CLEANUP_REQUIRES_REVIEW'));
 assert.ok(s.includes('approximateMinuteVaRows -gt 0 -and $report.marketDiagnostic.newBarKeysObserved'));
 assert.ok(s.includes("accountCheck='SKIPPED_MARKET_ONLY_NOT_RETESTED'"));
 assert.ok(s.indexOf('WriteResult $share $report')<s.indexOf("$report.accountCheck='STARTED'"));
 assert.ok(!/RssStockOrder\s*\(|RssCancelOrder\s*\(|Stop-Process|\.Kill\(/i.test(s));
});
test('E2E relay emits collector output as it arrives and forwards stop/ready controls',()=>{
 const s=fs.readFileSync(path.join(win,'Run-No11Chart50ReadOnlyE2E.ps1'),'utf8');
 assert.ok(s.includes('& powershell.exe @arguments | ForEach-Object'));
 assert.ok(s.includes("$arguments+=@('-ReadyFile',$ReadyFile)"));
 assert.ok(s.includes("$arguments+=@('-StopFile',$StopFile)"));
 assert.ok(s.includes('NO11_C50_E2E_STOP_REQUESTED_NO_IMPORT'));
});
test('actual Windows PowerShell helper reads appended rows beyond the initial range and rejects overflow',
 {skip:process.platform!=='win32'},()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'no11 chart growth '));
 try{
  const file=path.join(temp,'test.ps1');
  fs.writeFileSync(file,'\ufeff'+String.raw`
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($env:NO11_GROWTH_COLLECTOR,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'COLLECTOR_PARSE_FAILED'}
$names=@('DateToken','ReadGrowingChart')
$fns=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$false))
if($fns.Count -ne 2){throw 'GROWING_HELPER_MISSING'}
foreach($f in $fns){. ([scriptblock]::Create($f.Extent.Text))}
foreach($initial in @(50,120,150)){
 $limit=$initial+392
 $data=[array]::CreateInstance([object],[int[]]@(($limit+1),10),[int[]]@(1,1))
 for($i=1;$i -le $initial+4;$i++){$data[$i,4]='2026/10/26';$data[$i,5]='10:40'}
 $sheet=[pscustomobject]@{Data=$data;Expected=('A3:J'+($limit+3))}
 $sheet|Add-Member -MemberType ScriptMethod -Name Range -Value {
  param($a)
  if($a -cne $this.Expected){throw 'WRONG_GROWING_RANGE'}
  return [pscustomobject]@{Value2=$this.Data}
 }
 $result=ReadGrowingChart $sheet $initial
 if($result.rowLimit -ne $limit -or $result.values.GetValue(($initial+4),4) -cne '2026/10/26'){
  throw 'APPENDED_ROWS_NOT_READ'
 }
 $count=0
 for($n=0;$n -lt $result.rowLimit;$n++){if($null -ne (DateToken $result.values.GetValue(($n+1),4))){$count++}}
 if($count -ne ($initial+4)){throw 'APPENDED_ROW_COUNT'}
 $data[$limit+1,4]='2026/10/26'
 $blocked=$false
 try{ReadGrowingChart $sheet $initial|Out-Null}catch{
  if($_.Exception.Message -ceq 'NO11_C50_GROWING_CHART_OVERFLOW'){$blocked=$true}else{throw}
 }
 if(-not $blocked){throw 'OVERFLOW_NOT_REJECTED'}
}
# Parse every changed PowerShell entry point, without loading Excel.
foreach($name in @('Run-No11Chart50ReadOnlyE2E.ps1','Run-No11ReadOnlyConnectionCheck.ps1')){
 $t=$null;$e=$null
 [void][Management.Automation.Language.Parser]::ParseFile((Join-Path (Split-Path -Parent $env:NO11_GROWTH_COLLECTOR) $name),[ref]$t,[ref]$e)
 if($e.Count){throw ('ENTRY_POINT_PARSE_FAILED_'+$name)}
}
Write-Host 'NO11_GROWING_CHART_MOCK_PS51=PASS'
`,'utf8');
  const r=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',file],
   {cwd:root,env:{...process.env,NO11_GROWTH_COLLECTOR:collector},encoding:'utf8',timeout:30000});
  assert.ifError(r.error);assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
  assert.match(r.stdout,/NO11_GROWING_CHART_MOCK_PS51=PASS/);
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});
test('real Windows runner selftest covers deadline, cooperative stop and persisted results without Excel',
 {skip:process.platform!=='win32'},()=>{
 const r=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',runner,'-OfflineSelfTest'],
  {cwd:root,encoding:'utf8',timeout:45000});
 assert.ifError(r.error);assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
 assert.match(r.stdout,/NO11_CONNECTION_TIMEOUT_OFFLINE_SELFTEST=PASS/);
});
