import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=fileURLToPath(new URL('../windows/Prepare-No11ReceivedInputsReadOnly.ps1',import.meta.url));
const windows={skip:process.platform!=='win32'};

test('input sequence uses existing selected collector and cannot transmit orders',()=>{
 const text=fs.readFileSync(file,'utf8');
 assert.match(text,/Capture-No11RssTrainingBatchReadOnly/);
 assert.match(text,/NO11_INPUTS_PREREQUISITES_FAILED/);
 assert.match(text,/--require-full-shadow/);
 assert.match(text,/NO11_INPUTS_PREVIOUS_DIRECTORY_MISSING/);
 assert.doesNotMatch(text,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.Formula\s*=|\.Value2\s*=|Stop-Process|\.Quit\(/i);
 assert.ok([...text].every(c=>c.charCodeAt(0)<128));
});

test('Windows input orchestrator selftest parses with no market access',windows,()=>{
 const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File',file,'-OfflineSelfTest'],{encoding:'utf8',timeout:20000});
 assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
 assert.match(r.stdout,/NO11_INPUTS_WINDOWS_OFFLINE_SELFTEST=PASS/);
});

const harness=String.raw`
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($env:ARK_TEST_INPUT_SCRIPT,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw 'PARSE_FAILED'}
$functions=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)
foreach($f in $functions){Invoke-Expression $f.Extent.Text}
function InputsToday {return $script:today}
$script:today='2026-10-26'
$script:case=$env:ARK_TEST_CASE
$root=Join-Path $env:TEMP ('no11 inputs test '+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($root)
try{
 $script:paths=InputPaths (Split-Path -Parent $env:ARK_TEST_INPUT_SCRIPT)
 $script:outputs=@{}
 foreach($name in @('mask','plan','prereq','symbols','reference','prepared','evidence','python')){
  $p=Join-Path $root ($name+'.json');[IO.File]::WriteAllText($p,'{}');$script:outputs[$name]=$p
 }
 $capture=Join-Path $root 'captured prior';[void][IO.Directory]::CreateDirectory($capture)
 $script:returnedCapture=$capture
 $configFile=Join-Path $root 'config.json'
 $config=@{schemaId='ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1';sessionDate='2026-10-26';dailyRun=$root;productionReady=$false;orderTransmission=$false}
 [IO.File]::WriteAllText($configFile,($config|ConvertTo-Json))
 $options=@{ConfigFile=$configFile;SecurityEvidence=$outputs.evidence;EvidenceDocuments=$root;
  PreviousCaptureDir='';OutputRoot=$root;PythonExecutable=$outputs.python;AccountWorkbookPath='';
  CheckOnly=$false;StartShadow=$false;BatchSize=20;WaitSeconds=25}
 $script:calls=@()
 function InvokeInputsProcess([string]$Executable,[string[]]$Arguments,[string]$Failure){
  $script:calls+=@([pscustomobject]@{Executable=$Executable;Arguments=@($Arguments);Failure=$Failure})
  if(($script:case -eq 'prereq-failure' -and $Failure -eq 'NO11_INPUTS_PREREQUISITES_FAILED') -or
     ($script:case -eq 'capture-failure' -and $Failure -eq 'NO11_INPUTS_PREVIOUS_CAPTURE_FAILED')){throw $Failure}
  if($Arguments -contains $script:paths.mask){return ('NO11_DAILY_PASS_WATCH_FILE='+$script:outputs.mask)}
  if($Arguments -contains $script:paths.plan){return ('NO11_CHART50_RECEIPT='+$script:outputs.plan)}
  if($Arguments -contains $script:paths.prerequisites){return ('NO11_INPUTS_PREREQUISITES_REPORT='+$script:outputs.prereq)}
  if($Arguments -contains $script:paths.archive){return ('NO11_PREVIOUS_SYMBOLS_FILE='+$script:outputs.symbols)}
  if($Arguments -contains $script:paths.collector){return ('NO11_RSS_TRAINING_CAPTURE_DIR='+$script:returnedCapture)}
  if($Arguments -contains $script:paths.reference){return ('NO11_SESSION_REFERENCE_FILE='+$script:outputs.reference)}
  if($Arguments -contains $script:paths.prepare){return ('NO11_INPUTS_PREPARED_CONFIG='+$script:outputs.prepared)}
  return @()
 }
 switch($script:case){
  'preday' {$script:today='2026-10-25';$options.CheckOnly=$true}
  'reuse' {$options.PreviousCaptureDir=$capture}
  'start' {$options.StartShadow=$true;$options.AccountWorkbookPath=Join-Path $root 'account book.xlsx'}
  'missing-explicit' {$options.PreviousCaptureDir=Join-Path $root 'absent'}
  'future-start' {$script:today='2026-10-25'}
  'conflicting-switches' {$options.CheckOnly=$true;$options.StartShadow=$true}
 }
 $caught=$null
 try{InvokeInputSequence $options $paths}catch{$caught=$_.Exception.Message}
 $expectedError=switch($script:case){
  'prereq-failure' {'NO11_INPUTS_PREREQUISITES_FAILED'}
  'capture-failure' {'NO11_INPUTS_PREVIOUS_CAPTURE_FAILED'}
  'missing-explicit' {'NO11_INPUTS_PREVIOUS_DIRECTORY_MISSING'}
  'future-start' {'NO11_INPUTS_ACTUAL_SESSION_REQUIRED'}
  'conflicting-switches' {'NO11_INPUTS_CHECK_AND_START_CONFLICT'}
  default {$null}
 }
 if($null -ne $expectedError){if($caught -cne $expectedError){throw ('WRONG_ERROR:'+ $caught)}}
 elseif($null -ne $caught){throw $caught}
 $tags=@($script:calls|ForEach-Object {$_.Failure})
 $prefix=@('NO11_INPUTS_EXISTING_PINNED_RUNTIME_REQUIRED','NO11_INPUTS_MASK_EXPORT_FAILED',
  'NO11_INPUTS_PLAN_EXPORT_FAILED','NO11_INPUTS_PREREQUISITES_FAILED')
 if($script:case -in @('missing-explicit','future-start','conflicting-switches')){
  if($tags.Count -ne 0){throw 'PROCESS_STARTED_DESPITE_BAD_OPTIONS'}
 }elseif($script:case -in @('preday','prereq-failure')){
  if(($tags -join '|') -cne ($prefix -join '|')){throw 'EXCEL_STARTED_BEFORE_PREREQUISITES'}
 }else{
  $expected=@($prefix)+@('NO11_INPUTS_SELECTED_SCOPE_FAILED')
  if($script:case -ne 'reuse'){$expected+=@('NO11_INPUTS_PREVIOUS_CAPTURE_FAILED')}
  if($script:case -ne 'capture-failure'){
   $expected+=@('NO11_INPUTS_RSS_REFERENCE_FAILED','NO11_INPUTS_SOURCE_ASSEMBLY_FAILED','NO11_INPUTS_EXISTING_RUNNER_FAILED')
  }
  if(($tags -join '|') -cne ($expected -join '|')){throw ('WRONG_SEQUENCE:'+($tags -join '|'))}
 }
 $collector=@($script:calls|Where-Object {$_.Failure -eq 'NO11_INPUTS_PREVIOUS_CAPTURE_FAILED'})
 if($collector.Count -eq 1){
  $a=$collector[0].Arguments
  if($a[$a.IndexOf('-SymbolsFile')+1] -cne $outputs.symbols -or
     $a[$a.IndexOf('-Bars')+1] -cne '3000' -or $a[$a.IndexOf('-Period')+1] -cne '1M'){
   throw 'SELECTED_SYMBOLS_OR_ARCHIVE_ARGUMENTS_CHANGED'
  }
 }
 $assembly=@($script:calls|Where-Object {$_.Failure -eq 'NO11_INPUTS_SOURCE_ASSEMBLY_FAILED'})
 if($assembly.Count -eq 1){
  $a=$assembly[0].Arguments
  if($a[$a.IndexOf('--previous-capture-dir')+1] -cne $capture){throw 'CAPTURE_NOT_PASSED_TO_ASSEMBLY'}
 }
 $launch=@($script:calls|Where-Object {$_.Failure -eq 'NO11_INPUTS_EXISTING_RUNNER_FAILED'})
 if($launch.Count -eq 1){
  $a=$launch[0].Arguments
  if($a[$a.IndexOf('-ConfigFile')+1] -cne $outputs.prepared){throw 'WRONG_CONFIG_LAUNCHED'}
  if($script:case -eq 'start'){
   if($a -contains '-PreflightOnly' -or $a -notcontains '-AccountWorkbookPath'){throw 'START_ARGUMENTS_CHANGED'}
   $p=@($script:calls|Where-Object {$_.Failure -eq 'NO11_INPUTS_PREREQUISITES_FAILED'})[0].Arguments
   if($p -notcontains '--require-full-shadow'){throw 'FULL_PATH_NOT_REQUIRED'}
  }elseif($a -notcontains '-PreflightOnly'){throw 'SHADOW_STARTED_WITHOUT_REQUEST'}
 }
 Write-Host ('NO11_INPUT_SEQUENCE_TEST='+$script:case+'|PASS')
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
`;
for(const name of ['preday','capture','reuse','start','prereq-failure','capture-failure','missing-explicit','future-start','conflicting-switches']){
 test(`Windows actual input sequence / ${name} / mocked IO only`,windows,()=>{
  const r=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-Command',harness],
   {encoding:'utf8',timeout:25000,env:{...process.env,ARK_TEST_INPUT_SCRIPT:file,ARK_TEST_CASE:name}});
  assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
  assert.ok(r.stdout.includes(`NO11_INPUT_SEQUENCE_TEST=${name}|PASS`),r.stdout);
 });
}
