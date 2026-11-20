# Existing input preparation, optional prior archive capture, existing launcher.
# No new strategy, order transport, Excel order permission or source fabrication.
param([string]$ConfigFile,[string]$SecurityEvidence,[string]$EvidenceDocuments,
 [string]$PreviousCaptureDir,[string]$OutputRoot,[string]$PythonExecutable,
 [string]$AccountWorkbookPath,[switch]$StartShadow,[switch]$CheckOnly,
 [ValidateRange(1,20)][int]$BatchSize=20,
 [ValidateRange(5,60)][int]$WaitSeconds=25,
 [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function InputPaths([string]$WindowsDirectory){
 $base=Split-Path -Parent $WindowsDirectory
 $tools=Join-Path $base 'tools'
 return @{
  archive=Join-Path $tools 'no11_previous_archive_context.py'
  prerequisites=Join-Path $tools 'no11_input_prerequisites.py'
  prepare=Join-Path $tools 'no11_prepare_received_inputs.py'
  mask=Join-Path $tools 'no11_export_observed_pass_watch_mask.mjs'
  plan=Join-Path $tools 'no11_export_chart50_prescreen.mjs'
  collector=Join-Path $WindowsDirectory 'Capture-No11RssTrainingBatchReadOnly.ps1'
  reference=Join-Path $WindowsDirectory 'Capture-No11SessionReferenceReadOnly.ps1'
  runner=Join-Path $WindowsDirectory 'Run-No11ReceivedSessionReadOnly.ps1'
 }
}
function InputsToday {
 return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd')
}
function ResultPath($lines,[string]$prefix,[switch]$Directory){
 $matches=@($lines|Where-Object {([string]$_).StartsWith($prefix,[StringComparison]::Ordinal)})
 if($matches.Count -ne 1){throw 'NO11_INPUTS_RESULT_NOT_UNIQUE'}
 $p=([string]$matches[0]).Substring($prefix.Length)
 $kind='Leaf';if($Directory){$kind='Container'}
 if(-not [IO.Path]::IsPathRooted($p) -or -not (Test-Path -LiteralPath $p -PathType $kind)){
  throw 'NO11_INPUTS_RESULT_FILE_MISSING'
 }
 return $p
}
function InvokeInputsProcess([string]$Executable,[string[]]$Arguments,[string]$Failure){
 $lines=@(& $Executable @Arguments)
 if($LASTEXITCODE -ne 0){throw $Failure}
 return $lines
}
function InvokeInputSequence([hashtable]$Options,[hashtable]$Paths){
 if($Options.CheckOnly -and $Options.StartShadow){throw 'NO11_INPUTS_CHECK_AND_START_CONFLICT'}
 foreach($p in @($Options.ConfigFile,$Options.SecurityEvidence,$Options.PythonExecutable)){
  if([string]::IsNullOrWhiteSpace($p) -or -not [IO.Path]::IsPathRooted($p) -or
     -not (Test-Path -LiteralPath $p -PathType Leaf)){throw 'NO11_INPUTS_REQUIRED_FILE_MISSING'}
 }
 foreach($p in @($Options.EvidenceDocuments,$Options.OutputRoot)){
  if([string]::IsNullOrWhiteSpace($p) -or -not [IO.Path]::IsPathRooted($p) -or
     -not (Test-Path -LiteralPath $p -PathType Container)){throw 'NO11_INPUTS_REQUIRED_DIRECTORY_MISSING'}
 }
 $capture=[string]$Options.PreviousCaptureDir
 if(-not [string]::IsNullOrWhiteSpace($capture) -and
    (-not [IO.Path]::IsPathRooted($capture) -or -not (Test-Path -LiteralPath $capture -PathType Container))){
  # An explicitly wrong source never silently falls back to another capture.
  throw 'NO11_INPUTS_PREVIOUS_DIRECTORY_MISSING'
 }
 if((Get-Item -LiteralPath $Options.ConfigFile).Length -gt 100000){throw 'NO11_INPUTS_CONFIG_SIZE'}
 $config=Get-Content -LiteralPath $Options.ConfigFile -Raw -Encoding UTF8|ConvertFrom-Json
 $today=InputsToday;$session=[string]$config.sessionDate
 $date=[datetime]::MinValue
 if(-not [datetime]::TryParseExact($session,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture,
  [Globalization.DateTimeStyles]::None,[ref]$date)){throw 'NO11_INPUTS_SESSION_DATE_INVALID'}
 if($config.schemaId -cne 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -or
    $config.orderTransmission -ne $false -or $config.productionReady -ne $false){
  throw 'NO11_INPUTS_READONLY_CONFIG_REQUIRED'
 }
 if(((-not $Options.CheckOnly) -and $session -cne $today) -or $session -clt $today){
  throw 'NO11_INPUTS_ACTUAL_SESSION_REQUIRED'
 }
 $check="import sys;from importlib.metadata import version;assert sys.version_info[:2]==(3,12);assert all(version(k)==v for k,v in [('numpy','2.3.5'),('scipy','1.17.0'),('scikit-learn','1.8.0')])"
 [void](InvokeInputsProcess $Options.PythonExecutable @('-B','-c',$check) 'NO11_INPUTS_EXISTING_PINNED_RUNTIME_REQUIRED')
 $maskLines=@(InvokeInputsProcess 'node' @($Paths.mask,'--run',[string]$config.dailyRun) 'NO11_INPUTS_MASK_EXPORT_FAILED')
 $mask=ResultPath $maskLines 'NO11_DAILY_PASS_WATCH_FILE='
 $planArgs=@($Paths.plan,'--run',[string]$config.dailyRun,'--session',$session)
 if('pinsFile' -in $config.PSObject.Properties.Name){$planArgs+=@('--pins-file',[string]$config.pinsFile)}
 $planLines=@(InvokeInputsProcess 'node' $planArgs 'NO11_INPUTS_PLAN_EXPORT_FAILED')
 $plan=ResultPath $planLines 'NO11_CHART50_RECEIPT='
 $prereq=@('-B',$Paths.prerequisites,'--plan',$plan,'--mask',$mask,
  '--bootstrap-config',$Options.ConfigFile,'--security-evidence',$Options.SecurityEvidence,
  '--evidence-documents',$Options.EvidenceDocuments,'--output-root',$Options.OutputRoot)
 if(-not [string]::IsNullOrWhiteSpace($capture)){$prereq+=@('--previous-capture-dir',$capture)}
 if($Options.StartShadow){$prereq+=@('--require-full-shadow')}
 $checked=@(InvokeInputsProcess $Options.PythonExecutable $prereq 'NO11_INPUTS_PREREQUISITES_FAILED')
 $checkReport=ResultPath $checked 'NO11_INPUTS_PREREQUISITES_REPORT='
 Write-Host ('NO11_INPUTS_PREREQUISITES_REPORT='+$checkReport)
 if($Options.CheckOnly){
  Write-Host 'NO11_INPUTS_PREPARATION=DEPENDENCIES_CHECKED_NO_EXCEL_STARTED'
  Write-Host 'ORDER_TRANSMISSION=False'
  return
 }
 $symbolArgs=@('-B',$Paths.archive,'--plan',$plan,'--mask',$mask,'--output-root',$Options.OutputRoot,'--symbols-only')
 $symbolLines=@(InvokeInputsProcess $Options.PythonExecutable $symbolArgs 'NO11_INPUTS_SELECTED_SCOPE_FAILED')
 $symbols=ResultPath $symbolLines 'NO11_PREVIOUS_SYMBOLS_FILE='
 if([string]::IsNullOrWhiteSpace($capture)){
  # Reuse the existing read-only collector and EXACT already selected symbols.
  # Capture completes/closes its own temporary book before reference collection.
  $captureArgs=@('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$Paths.collector,
   '-SymbolsFile',$symbols,'-PrivateRoot',$Options.OutputRoot,
   '-BatchSize',[string]$Options.BatchSize,'-WaitSeconds',[string]$Options.WaitSeconds,
   '-Bars','3000','-Period','1M')
  $captured=@(InvokeInputsProcess 'powershell.exe' $captureArgs 'NO11_INPUTS_PREVIOUS_CAPTURE_FAILED')
  $capture=ResultPath $captured 'NO11_RSS_TRAINING_CAPTURE_DIR=' -Directory
 }
 Write-Host ('NO11_INPUTS_PREVIOUS_CAPTURE_DIR='+$capture)
 $refArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$Paths.reference,
  '-SymbolsFile',$symbols,'-ChartPlanFile',$plan,'-OutputRoot',$Options.OutputRoot)
 $referenceLines=@(InvokeInputsProcess 'powershell.exe' $refArgs 'NO11_INPUTS_RSS_REFERENCE_FAILED')
 $rawReference=ResultPath $referenceLines 'NO11_SESSION_REFERENCE_FILE='
 $prepareArgs=@('-B',$Paths.prepare,'--plan',$plan,'--mask',$mask,
  '--reference-file',$rawReference,'--security-evidence',$Options.SecurityEvidence,
  '--evidence-documents',$Options.EvidenceDocuments,'--previous-capture-dir',$capture,
  '--bootstrap-config',$Options.ConfigFile,'--output-root',$Options.OutputRoot)
 $preparedLines=@(InvokeInputsProcess $Options.PythonExecutable $prepareArgs 'NO11_INPUTS_SOURCE_ASSEMBLY_FAILED')
 $readyConfig=ResultPath $preparedLines 'NO11_INPUTS_PREPARED_CONFIG='
 Write-Host ('NO11_INPUTS_PREPARED_CONFIG='+$readyConfig)
 $launch=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$Paths.runner,
  '-ConfigFile',$readyConfig,'-PythonExecutable',$Options.PythonExecutable)
 if(-not $Options.StartShadow){$launch+=@('-PreflightOnly')}
 if(-not [string]::IsNullOrWhiteSpace($Options.AccountWorkbookPath)){
  $launch+=@('-AccountWorkbookPath',$Options.AccountWorkbookPath)
 }
 $launched=@(InvokeInputsProcess 'powershell.exe' $launch 'NO11_INPUTS_EXISTING_RUNNER_FAILED')
 $launched|ForEach-Object {Write-Host $_}
 Write-Host 'NO11_INPUTS_PREPARATION=COMPLETE_NOT_LIVE_CERTIFIED'
 Write-Host 'ORDER_TRANSMISSION=False'
}
$paths=InputPaths $PSScriptRoot
if($OfflineSelfTest){
 foreach($p in $paths.Values){if(-not (Test-Path -LiteralPath $p -PathType Leaf)){throw 'NO11_INPUTS_SCRIPT_MISSING'}}
 Write-Host 'NO11_INPUTS_WINDOWS_OFFLINE_SELFTEST=PASS';Write-Host 'ORDER_TRANSMISSION=False';exit 0
}
try{
 $options=@{ConfigFile=$ConfigFile;SecurityEvidence=$SecurityEvidence;EvidenceDocuments=$EvidenceDocuments;
  PreviousCaptureDir=$PreviousCaptureDir;OutputRoot=$OutputRoot;PythonExecutable=$PythonExecutable;
  AccountWorkbookPath=$AccountWorkbookPath;StartShadow=[bool]$StartShadow;CheckOnly=[bool]$CheckOnly;
  BatchSize=$BatchSize;WaitSeconds=$WaitSeconds}
 InvokeInputSequence $options $paths
}catch{
 $s=$_.Exception.Message
 if($s -notmatch '^NO11_[A-Z0-9_]+$'){$s='NO11_INPUTS_PRIVATE_SOURCE_FAILED'}
 Write-Host ('NO11_INPUTS_PREPARATION=BLOCKED|'+$s)
 Write-Host 'ORDER_TRANSMISSION=False';exit 2
}
exit 0
