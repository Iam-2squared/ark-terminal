# No.1.1: one-shot ACTUAL same-day selected RSS reference for Shadow input.
# No multi-hour Chart50, NO account reads or live/paper orders.
# Reuses byte-pinned original selected chart plan/mask and ORIGINAL collector.
# Reports per-field RSS omissions without promoting an unreviewed master.
# No dated master, reviewed evidence or trading readiness is fabricated.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$DailyRun='',
 [string]$ChartPlanFile='',
 [string]$MaskFile='',
 [string]$OutputRoot='',
 [string]$PythonExecutable='',
 [ValidateRange(5,60)][int]$WarmupSeconds=20,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(-not $OutputRoot){
 $OutputRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\session-reference\2026-10-29'
}
if(-not $PythonExecutable){
 $PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
}

$archive=Join-Path $EngineRoot 'tools\no11_previous_archive_context.py'
$collector=Join-Path $EngineRoot 'windows\Capture-No11SessionReferenceReadOnly.ps1'
$diagnostic=Join-Path $EngineRoot 'tools\no11_reference_fields_diagnostic.mjs'

function AssertPath([string]$p,[string]$role,[bool]$directory){
 if([string]::IsNullOrWhiteSpace($p) -or -not [IO.Path]::IsPathRooted($p)){
  throw ('NO11_ONESHOT_'+$role+'_ABSOLUTE_REQUIRED')
 }
 $resolved=[IO.Path]::GetFullPath($p)
 $item=Get-Item -LiteralPath $resolved -ErrorAction Stop
 if([bool]$item.PSIsContainer -ne $directory){
  throw ('NO11_ONESHOT_'+$role+'_TYPE_INVALID')
 }
 $cur=$resolved
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  $x=Get-Item -LiteralPath $cur -Force -ErrorAction Stop
  if(($x.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
   throw ('NO11_ONESHOT_'+$role+'_REPARSE_FORBIDDEN')
  }
  $next=Split-Path -Parent $cur
  if($next -ceq $cur){break}
  $cur=$next
 }
 return $resolved
}
function PathFromOutput([object[]]$lines,[string]$token){
 $m=@($lines|Where-Object {([string]$_).StartsWith($token,[StringComparison]::Ordinal)})
 if($m.Count -ne 1){throw 'NO11_ONESHOT_OUTPUT_PATH_NOT_UNIQUE'}
 $p=([string]$m[0]).Substring($token.Length)
 [void](AssertPath $p 'RECEIPT' $false)
 return $p
}
function AssertNoConcurrentCollector{
 $forbidden='(?i)(Probe-No11Chart50ContinuousReadOnly|Probe-No11Chart50DiagnosedReadOnly|Run-No11ReceivedSessionReadOnly|Capture-No11RssTrainingBatchReadOnly|Capture-No11SessionReferenceReadOnly|Run-No11Chart50ReadOnlyE2E)\.ps1'
 $other=@(Get-CimInstance -ClassName Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {
   $_.ProcessId -ne $PID -and
   -not [string]::IsNullOrWhiteSpace($_.CommandLine) -and
   $_.CommandLine -match $forbidden
  })
 if($other.Count -ne 0){throw 'NO11_ONESHOT_OTHER_EXCEL_COLLECTOR_RUNNING'}
}
try{
 if($OfflineSelfTest){
  # When this launcher is downloaded into TEMP, use the original engine-root
  # collector. CI source checkout has an adjacent original collector instead.
  # Only the ORIGINAL test entrypoint is called, no Excel session is accessed.
  $installedCollector=Join-Path $EngineRoot 'windows\Capture-No11SessionReferenceReadOnly.ps1'
  $adjacentCollector=Join-Path $PSScriptRoot 'Capture-No11SessionReferenceReadOnly.ps1'
  $testCollector=''
  if(Test-Path -LiteralPath $installedCollector -PathType Leaf){
   $testCollector=$installedCollector
  }elseif(Test-Path -LiteralPath $adjacentCollector -PathType Leaf){
   $testCollector=$adjacentCollector
  }else{
   throw 'NO11_ONESHOT_ORIGINAL_COLLECTOR_SELFTEST_SOURCE_MISSING'
  }
  [void](AssertPath $testCollector 'ORIGINAL_COLLECTOR_SELFTEST' $false)
  Write-Host 'NO11_ONESHOT_SELFTEST_COLLECTOR=ORIGINAL_AVAILABLE'
  $t=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $testCollector -OfflineSelfTest)
  if($LASTEXITCODE -ne 0 -or $t -notcontains 'NO11_REFERENCE_OFFLINE_SELFTEST=PASS'){
   throw 'NO11_ONESHOT_ORIGINAL_COLLECTOR_SELFTEST_FAILED'
  }
  Write-Host 'NO11_ONESHOT_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_ONESHOT_EXCEL_STARTED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 foreach($x in @($archive,$collector,$diagnostic)){[void](AssertPath $x 'PINNED_CODE' $false)}
 $date=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 if($date -cne '2026-10-29'){throw 'NO11_ONESHOT_SESSION_DATE_CHANGED'}
 [void](AssertPath $EngineRoot 'ENGINE' $true)
 [void](AssertPath $DailyRun 'G1_RUN' $true)
 [void](AssertPath $ChartPlanFile 'CHART' $false)
 [void](AssertPath $MaskFile 'MASK' $false)
 [void](AssertPath $PythonExecutable 'PYTHON' $false)
 $root=[IO.Path]::GetFullPath($OutputRoot)
 $allowed=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'))
 if(-not $root.StartsWith($allowed+'\',[StringComparison]::OrdinalIgnoreCase)){
  throw 'NO11_ONESHOT_OUTPUT_MUST_BE_PRIVATE_NO12'
 }
 [void][IO.Directory]::CreateDirectory($root)
 [void](AssertPath $root 'OUTPUT' $true)

 $c=Get-Content -LiteralPath $ChartPlanFile -Raw -Encoding UTF8|ConvertFrom-Json
 $m=Get-Content -LiteralPath $MaskFile -Raw -Encoding UTF8|ConvertFrom-Json
 if($c.schemaId -cne 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' -or
    $c.currentRefreshAsOfSession -cne '2026-10-28' -or
    $c.orderTransmission -ne $false -or $c.productionReady -ne $false -or
    $c.chartPlan.sessionDate -cne $date -or
    $c.chartPlan.asOfSession -cne '2026-10-28' -or
    $c.chartPlan.orderTransmission -ne $false -or
    $c.chartPlan.productionReady -ne $false -or
    @($c.chartPlan.selectorInputSymbols).Count -lt 1 -or
    @($c.chartPlan.selectorInputSymbols).Count -gt 47 -or
    $m.asOfSession -cne '2026-10-28' -or
    $m.weeklyOriginalAsOfSession -cne '2026-10-26' -or
    $m.observedPassCount -lt 1 -or $m.observedPassCount -gt 500 -or
    $m.orderTransmission -ne $false){
  throw 'NO11_ONESHOT_OCT29_CHART_SCOPE_INVALID'
 }
 # Source, mask and chart must be from the one explicitly selected refresh run.
 $runPath=[IO.Path]::GetFullPath($DailyRun)
 foreach($sameRunFile in @($ChartPlanFile,$MaskFile)){
  $parent=[IO.Path]::GetFullPath((Split-Path -Parent $sameRunFile))
  if(-not $parent.Equals($runPath,[StringComparison]::OrdinalIgnoreCase)){
   throw 'NO11_ONESHOT_OCT29_REFRESH_RUN_IDENTITY_MISMATCH'
  }
 }
 AssertNoConcurrentCollector
 if(@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -ne 1){
  throw 'NO11_ONESHOT_EXCEL_PROCESS_NOT_UNIQUE'
 }
 if(@(Get-Process MarketSpeed2 -ErrorAction SilentlyContinue).Count -lt 1){
  throw 'NO11_ONESHOT_MARKETSPEED_NOT_RUNNING'
 }

 # Existing original adapter validates calendar, plan/mask hashes and scope.
 $scopeArgs=@('-B',$archive,'--plan',$ChartPlanFile,'--mask',$MaskFile,
  '--output-root',$root,'--symbols-only')
 $names=@(& $PythonExecutable @scopeArgs)
 if($LASTEXITCODE -ne 0){throw 'NO11_ONESHOT_ORIGINAL_SCOPE_EXPORT_FAILED'}
 $symbols=PathFromOutput $names 'NO11_PREVIOUS_SYMBOLS_FILE='
 Write-Host 'NO11_ONESHOT_SCOPE=47_SELECTED_FROM_ORIGINAL_PLAN'
 Write-Host 'NO11_ONESHOT_MARKET_RSS=CAPTURING_TODAY_REFERENCE'

 # Existing collector creates ONE unsaved Excel workbook and closes without saving.
 $captureArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$collector,
  '-SymbolsFile',$symbols,'-ChartPlanFile',$ChartPlanFile,
  '-OutputRoot',$root,'-WarmupSeconds',[string]$WarmupSeconds)
 $out=@(& powershell.exe @captureArgs)
 $code=$LASTEXITCODE
 $out|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'} |
   ForEach-Object {Write-Host $_}
 if($code -ne 0){throw 'NO11_ONESHOT_ORIGINAL_REFERENCE_CAPTURE_FAILED'}
 $receipt=PathFromOutput $out 'NO11_SESSION_REFERENCE_FILE='
 $expectedCount='NO11_SESSION_REFERENCE_ROWS='+[string]@($c.chartPlan.selectorInputSymbols).Count
 $count=@($out | Where-Object {$_ -ceq $expectedCount})
 if($count.Count -ne 1){throw 'NO11_ONESHOT_REFERENCE_ROW_COUNT_NOT_47'}

 [void](Get-Command node -ErrorAction Stop)
 $diagLines=@(& node $diagnostic --reference $receipt --session $date)
 $diagCode=$LASTEXITCODE
 $diagLines|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'} |
   ForEach-Object {Write-Host $_}
 if($diagCode -ne 0){throw 'NO11_ONESHOT_REFERENCE_DIAGNOSTIC_FAILED'}
 Write-Host 'NO11_ONESHOT_REVIEW_QUEUE=NOT_REVIEWED_NOT_CREATED'
 Write-Host 'NO11_ONESHOT=OBSERVED_RSS_REFERENCE_CAPTURED_UNREVIEWED'
 Write-Host 'NO11_ONESHOT_INTEGRATED_SHADOW=BLOCKED_UNTIL_REAL_EXTERNAL_REVIEW'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_ONESHOT_[A-Z0-9_]+$'){
  $reason='NO11_ONESHOT_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_ONESHOT=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
exit 0
