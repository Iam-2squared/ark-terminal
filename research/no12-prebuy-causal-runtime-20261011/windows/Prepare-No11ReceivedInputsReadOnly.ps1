# Existing daily scope -> RSS reference -> master/prior context/config -> preflight.
# Optional StartShadow delegates to the existing same-run read-only launcher.
param([string]$ConfigFile,[string]$SecurityEvidence,[string]$EvidenceDocuments,
 [string]$PreviousCaptureDir,[string]$OutputRoot,[string]$PythonExecutable,
 [string]$AccountWorkbookPath,[switch]$StartShadow,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$base=Split-Path -Parent $PSScriptRoot
$tools=Join-Path $base 'tools'
$archive=Join-Path $tools 'no11_previous_archive_context.py'
$prepare=Join-Path $tools 'no11_prepare_received_inputs.py'
$reference=Join-Path $PSScriptRoot 'Capture-No11SessionReferenceReadOnly.ps1'
$runner=Join-Path $PSScriptRoot 'Run-No11ReceivedSessionReadOnly.ps1'
function ResultPath($lines,[string]$prefix){
 $matches=@($lines|Where-Object {([string]$_).StartsWith($prefix,[StringComparison]::Ordinal)})
 if($matches.Count -ne 1){throw 'NO11_INPUTS_RESULT_NOT_UNIQUE'}
 $p=([string]$matches[0]).Substring($prefix.Length)
 if(-not [IO.Path]::IsPathRooted($p) -or -not (Test-Path -LiteralPath $p -PathType Leaf)){
  throw 'NO11_INPUTS_RESULT_FILE_MISSING'
 }
 return $p
}
if($OfflineSelfTest){
 foreach($p in @($archive,$prepare,$reference,$runner)){
  if(-not (Test-Path -LiteralPath $p -PathType Leaf)){throw 'NO11_INPUTS_SCRIPT_MISSING'}
 }
 Write-Host 'NO11_INPUTS_WINDOWS_OFFLINE_SELFTEST=PASS';Write-Host 'ORDER_TRANSMISSION=False';exit 0
}
try{
 foreach($p in @($ConfigFile,$SecurityEvidence,$PythonExecutable)){
  if([string]::IsNullOrWhiteSpace($p) -or -not [IO.Path]::IsPathRooted($p) -or
     -not (Test-Path -LiteralPath $p -PathType Leaf)){throw 'NO11_INPUTS_REQUIRED_FILE_MISSING'}
 }
 foreach($p in @($EvidenceDocuments,$PreviousCaptureDir,$OutputRoot)){
  if([string]::IsNullOrWhiteSpace($p) -or -not [IO.Path]::IsPathRooted($p) -or
     -not (Test-Path -LiteralPath $p -PathType Container)){throw 'NO11_INPUTS_REQUIRED_DIRECTORY_MISSING'}
 }
 if((Get-Item -LiteralPath $ConfigFile).Length -gt 100000){throw 'NO11_INPUTS_CONFIG_SIZE'}
 $config=Get-Content -LiteralPath $ConfigFile -Raw -Encoding UTF8|ConvertFrom-Json
 $session=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd')
 if($config.schemaId -cne 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -or
    $config.sessionDate -cne $session -or $config.orderTransmission -ne $false -or $config.productionReady -ne $false){
  throw 'NO11_INPUTS_ACTUAL_SESSION_READONLY_CONFIG_REQUIRED'
 }
 $check="import sys;from importlib.metadata import version;assert sys.version_info[:2]==(3,12);assert all(version(k)==v for k,v in [('numpy','2.3.5'),('scipy','1.17.0'),('scikit-learn','1.8.0')])"
 & $PythonExecutable -B -c $check
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_EXISTING_PINNED_RUNTIME_REQUIRED'}
 $maskLines=@(& node (Join-Path $tools 'no11_export_observed_pass_watch_mask.mjs') --run $config.dailyRun)
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_MASK_EXPORT_FAILED'}
 $mask=ResultPath $maskLines 'NO11_DAILY_PASS_WATCH_FILE='
 $planArgs=@('--run',[string]$config.dailyRun,'--session',$session)
 if('pinsFile' -in $config.PSObject.Properties.Name){$planArgs+=@('--pins-file',[string]$config.pinsFile)}
 $planLines=@(& node (Join-Path $tools 'no11_export_chart50_prescreen.mjs') @planArgs)
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_PLAN_EXPORT_FAILED'}
 $plan=ResultPath $planLines 'NO11_CHART50_RECEIPT='
 $symbolLines=@(& $PythonExecutable -B $archive --plan $plan --mask $mask --output-root $OutputRoot --symbols-only)
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_SELECTED_SCOPE_FAILED'}
 $symbols=ResultPath $symbolLines 'NO11_PREVIOUS_SYMBOLS_FILE='
 $referenceLines=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reference `
  -SymbolsFile $symbols -ChartPlanFile $plan -OutputRoot $OutputRoot)
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_RSS_REFERENCE_FAILED'}
 $rawReference=ResultPath $referenceLines 'NO11_SESSION_REFERENCE_FILE='
 $preparedLines=@(& $PythonExecutable -B $prepare --plan $plan --mask $mask `
  --reference-file $rawReference --security-evidence $SecurityEvidence --evidence-documents $EvidenceDocuments `
  --previous-capture-dir $PreviousCaptureDir --bootstrap-config $ConfigFile --output-root $OutputRoot)
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_SOURCE_ASSEMBLY_FAILED'}
 $readyConfig=ResultPath $preparedLines 'NO11_INPUTS_PREPARED_CONFIG='
 Write-Host ('NO11_INPUTS_PREPARED_CONFIG='+$readyConfig)
 $launch=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-ConfigFile',$readyConfig,'-PythonExecutable',$PythonExecutable)
 if(-not $StartShadow){$launch+=@('-PreflightOnly')}
 if(-not [string]::IsNullOrWhiteSpace($AccountWorkbookPath)){$launch+=@('-AccountWorkbookPath',$AccountWorkbookPath)}
 & powershell.exe @launch
 if($LASTEXITCODE -ne 0){throw 'NO11_INPUTS_EXISTING_RUNNER_FAILED'}
 Write-Host 'NO11_INPUTS_PREPARATION=COMPLETE_NOT_LIVE_CERTIFIED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $s=$_.Exception.Message
 if($s -notmatch '^NO11_[A-Z0-9_]+$'){$s='NO11_INPUTS_PRIVATE_SOURCE_FAILED'}
 Write-Host ('NO11_INPUTS_PREPARATION=BLOCKED|'+$s)
 Write-Host 'ORDER_TRANSMISSION=False';exit 2
}
exit 0
