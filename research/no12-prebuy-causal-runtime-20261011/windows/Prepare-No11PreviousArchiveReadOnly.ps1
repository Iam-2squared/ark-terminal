# Reuse the existing selected-symbol plan and RSS archive collector.
# No model fitting, account values, order functions or live permission changes.
param(
 [string]$SessionDate='2026-10-26',
 [string]$RunDir,
 [string]$PrivateRoot,
 [string]$PinsFile,
 [string]$CaptureDir,
 [string]$DatedMaster,
 [string]$BootstrapConfig,
 [string]$PythonExecutable,
 [string]$PrecomputedChartPlanFile,
 [string]$PrecomputedMaskFile,
 [ValidateRange(1,20)][int]$BatchSize=20,
 [ValidateRange(5,60)][int]$WaitSeconds=25,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$base=Split-Path -Parent $PSScriptRoot
$repo=[IO.Path]::GetFullPath((Join-Path $base '..\..'))
$adapter=Join-Path $base 'tools\no11_previous_archive_context.py'
$collector=Join-Path $PSScriptRoot 'Capture-No11RssTrainingBatchReadOnly.ps1'
function UniquePath([object[]]$Lines,[string]$Prefix){
 $matches=@($Lines | Where-Object {([string]$_).StartsWith($Prefix,[StringComparison]::Ordinal)})
 if($matches.Count -ne 1){throw 'NO11_PREVIOUS_EXPORT_PATH_REQUIRED'}
 $file=([string]$matches[0]).Substring($Prefix.Length)
 if(-not [IO.Path]::IsPathRooted($file) -or -not (Test-Path -LiteralPath $file)){
  throw 'NO11_PREVIOUS_EXPORTED_PATH_MISSING'
 }
 return $file
}
function CaptureArguments([string]$Symbols,[string]$Destination){
 return @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$collector,
   '-SymbolsFile',$Symbols,'-PrivateRoot',$Destination,
   '-BatchSize',[string]$BatchSize,'-WaitSeconds',[string]$WaitSeconds,
   '-Bars','3000','-Period','1M')
}
if($OfflineSelfTest){
 if(-not (Test-Path -LiteralPath $adapter -PathType Leaf) -or
    -not (Test-Path -LiteralPath $collector -PathType Leaf)){
  throw 'NO11_PREVIOUS_SOURCE_FILES_MISSING'
 }
 $test=@(CaptureArguments 'C:\private path\symbols.txt' 'C:\private path\capture')
 if($test.Count -ne 18 -or $test[7] -cne 'C:\private path\symbols.txt' -or
    $test[15] -cne '3000' -or $test[17] -cne '1M'){
  throw 'NO11_PREVIOUS_CAPTURE_ARGUMENT_TEST_FAILED'
 }
 Write-Host 'NO11_PREVIOUS_PREPARE_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 if($SessionDate -cnotmatch '^20\d\d-\d\d-\d\d$'){throw 'NO11_PREVIOUS_SESSION_INVALID'}
 if([string]::IsNullOrWhiteSpace($RunDir)){
  $RunDir=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d'
 }
 if([string]::IsNullOrWhiteSpace($PrivateRoot)){
  $PrivateRoot=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\previous-source\'+$SessionDate)
 }
 foreach($file in @($RunDir,$PrivateRoot)){
  if(-not [IO.Path]::IsPathRooted($file)){throw 'NO11_PREVIOUS_ABSOLUTE_PATH_REQUIRED'}
  $full=[IO.Path]::GetFullPath($file)
  if($full.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or
     $full.StartsWith($repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
   throw 'NO11_PREVIOUS_OUTPUT_MUST_BE_PRIVATE'
  }
 }
 if(-not (Test-Path -LiteralPath $RunDir -PathType Container)){throw 'NO11_PREVIOUS_DAILY_RUN_REQUIRED'}
 [void][IO.Directory]::CreateDirectory($PrivateRoot)
 $py='';$prefix=@()
 if(-not [string]::IsNullOrWhiteSpace($PythonExecutable)){
  if(-not [IO.Path]::IsPathRooted($PythonExecutable) -or
     -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)){
   throw 'NO11_PREVIOUS_PYTHON_EXECUTABLE_INVALID'
  }
  $py=$PythonExecutable
 }else{
  $venv=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
  if(Test-Path -LiteralPath $venv -PathType Leaf){$py=$venv}
  elseif(Get-Command py -ErrorAction SilentlyContinue){$py='py';$prefix=@('-3.12')}
 }
 if([string]::IsNullOrWhiteSpace($py)){throw 'NO11_PREVIOUS_EXISTING_PYTHON_REQUIRED'}
 if(-not [string]::IsNullOrWhiteSpace($BootstrapConfig) -and [string]::IsNullOrWhiteSpace($DatedMaster)){
  throw 'NO11_PREVIOUS_MASTER_REQUIRED_FOR_CONFIG'
 }
 # Weekday 429-pool refresh has a DIFFERENT plan schema from the
 # 4328-member Friday full-market daily census. The original full-market
 # exporters are incapable of exporting its mask/Chart50 receipt. Accept
 # explicitly pinned, immutable weekly refresh receipts, then let the shipped
 # Python scope(...) validator re-check original Chart50 hashes, session,
 # previous cash date and G1 membership before ANY Excel collector starts.
 $usingPrecomputed=(-not [string]::IsNullOrWhiteSpace($PrecomputedChartPlanFile) -or
                    -not [string]::IsNullOrWhiteSpace($PrecomputedMaskFile))
 if($usingPrecomputed){
  if([string]::IsNullOrWhiteSpace($PrecomputedChartPlanFile) -or
     [string]::IsNullOrWhiteSpace($PrecomputedMaskFile) -or
     -not [string]::IsNullOrWhiteSpace($PinsFile)){
   throw 'NO11_PREVIOUS_PRECOMPUTED_BOTH_RECEIPTS_REQUIRED'
  }
  foreach($inputFile in @($PrecomputedChartPlanFile,$PrecomputedMaskFile)){
   if(-not [IO.Path]::IsPathRooted($inputFile) -or
      -not (Test-Path -LiteralPath $inputFile -PathType Leaf) -or
      ([IO.File]::GetAttributes($inputFile) -band [IO.FileAttributes]::ReparsePoint) -ne 0){
    throw 'NO11_PREVIOUS_PRECOMPUTED_PRIVATE_FILE_INVALID'
   }
   $f=[IO.Path]::GetFullPath($inputFile)
   if(-not $f.StartsWith(([IO.Path]::GetFullPath($RunDir)).TrimEnd('\')+'\',
     [StringComparison]::OrdinalIgnoreCase)){
    throw 'NO11_PREVIOUS_PRECOMPUTED_WRONG_SOURCE_RUN'
   }
  }
  $mask=[IO.Path]::GetFullPath($PrecomputedMaskFile)
  $plan=[IO.Path]::GetFullPath($PrecomputedChartPlanFile)
  Write-Host 'NO11_PREVIOUS_INPUT_SCOPE=WEEKLY_PINNED_RECEIPTS_VALIDATION_REQUIRED'
 }else{
  $maskLines=@(& node (Join-Path $base 'tools\no11_export_observed_pass_watch_mask.mjs') --run $RunDir)
  if($LASTEXITCODE -ne 0){throw 'NO11_PREVIOUS_MASK_EXPORT_FAILED'}
  $mask=UniquePath $maskLines 'NO11_DAILY_PASS_WATCH_FILE='
  $planArgs=@('--run',$RunDir,'--session',$SessionDate)
  if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$planArgs+=@('--pins-file',$PinsFile)}
  $planLines=@(& node (Join-Path $base 'tools\no11_export_chart50_prescreen.mjs') @planArgs)
  if($LASTEXITCODE -ne 0){throw 'NO11_PREVIOUS_PLAN_EXPORT_FAILED'}
  $plan=UniquePath $planLines 'NO11_CHART50_RECEIPT='
 }
 $common=@('-B',$adapter,'--plan',$plan,'--mask',$mask,'--output-root',$PrivateRoot)
 $symbolLines=@(& $py @prefix @common --symbols-only)
 if($LASTEXITCODE -ne 0){throw 'NO11_PREVIOUS_SYMBOL_EXPORT_FAILED'}
 $symbolLines | ForEach-Object {Write-Host $_}
 $symbols=UniquePath $symbolLines 'NO11_PREVIOUS_SYMBOLS_FILE='
 if([string]::IsNullOrWhiteSpace($CaptureDir)){
  $captureArgs=@(CaptureArguments $symbols $PrivateRoot)
  $captureLines=@(& powershell.exe @captureArgs)
  $captureExit=$LASTEXITCODE
  $captureLines | ForEach-Object {Write-Host $_}
  if($captureExit -ne 0){throw 'NO11_PREVIOUS_CAPTURE_FAILED'}
  $CaptureDir=UniquePath $captureLines 'NO11_RSS_TRAINING_CAPTURE_DIR='
 }
 $build=@($common)+@('--capture-dir',$CaptureDir)
 if(-not [string]::IsNullOrWhiteSpace($DatedMaster)){$build+=@('--dated-master',$DatedMaster)}
 if(-not [string]::IsNullOrWhiteSpace($BootstrapConfig)){$build+=@('--bootstrap-config',$BootstrapConfig)}
 & $py @prefix @build
 if($LASTEXITCODE -ne 0){throw 'NO11_PREVIOUS_CONTEXT_BUILD_FAILED'}
 Write-Host ('NO11_PREVIOUS_CAPTURE_DIR='+$CaptureDir)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $message=$_.Exception.Message
 if($message -cnotmatch '^NO11_[A-Z0-9_]+$'){$message='NO11_PREVIOUS_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_PREVIOUS_PREPARE=BLOCKED|'+$message)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
