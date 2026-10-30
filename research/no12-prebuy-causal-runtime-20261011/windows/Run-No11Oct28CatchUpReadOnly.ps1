# Oct28 explicit catch-up of the real Oct27 weekly G1 (429 source scope).
# Vendor D100 fetched today; any Oct28 partial candle is NOT admitted to G1.
# Same-day prior 1M history is collected separately for Oct28 Shadow.
# No orders, fake reviews, generated future sessions or Frozen model changes.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$LocalRoot='',
 [string]$SeedRun='',
 [ValidateRange(1,20)][int]$BatchSize=20,
 [ValidateRange(5,60)][int]$WaitSeconds=15,
 [ValidateRange(1,20)][int]$PreviousBatchSize=20,
 [ValidateRange(5,60)][int]$PreviousWaitSeconds=25,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_OCT28_CATCHUP_'+$reason)}}
function Source([string]$path,[bool]$dir=$false){
 Need (-not [string]::IsNullOrWhiteSpace($path) -and [IO.Path]::IsPathRooted($path)) 'ABSOLUTE_PATH_REQUIRED'
 $full=[IO.Path]::GetFullPath($path)
 Need (Test-Path -LiteralPath $full -PathType $(if($dir){'Container'}else{'Leaf'})) 'SOURCE_MISSING'
 $p=$full
 while(-not [string]::IsNullOrEmpty($p)){
  $item=Get-Item -LiteralPath $p -Force
  Need (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'SOURCE_LINK_FORBIDDEN'
  $parent=Split-Path -Parent $p;if($parent -ceq $p){break};$p=$parent
 }
 return $full
}
function UniqueOutput([object[]]$rows,[string]$prefix){
 $matches=@($rows|Where-Object {([string]$_).StartsWith($prefix,[StringComparison]::Ordinal)})
 Need ($matches.Count -eq 1) 'RECEIPT_OUTPUT_NOT_UNIQUE'
 return Source (([string]$matches[0]).Substring($prefix.Length))
}
function UniqueFile([string]$dir,[string]$pattern,[string]$status){
 $list=@(Get-ChildItem -LiteralPath (Source $dir $true) -File -Filter $pattern -ErrorAction Stop)
 Need ($list.Count -eq 1) $status
 return Source $list[0].FullName
}
if($OfflineSelfTest){
 Need ($BatchSize -le 20 -and $WaitSeconds -ge 5) 'SELFTEST_BOUNDS'
 Write-Host 'NO11_OCT28_CATCHUP_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OCT28_CATCHUP_EXCEL_OPENED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $stamp=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
 Need ($stamp.StartsWith('2026-10-28T') -and $stamp.Substring(11,5) -ge '08:30' -and
  $stamp.Substring(11,5) -lt '18:00') 'OCT27_HISTORICAL_RECOVERY_WINDOW_REQUIRED'
 if(-not $LocalRoot){$LocalRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'}
 $local=Source $LocalRoot $true
 $engine=Source $EngineRoot $true
 if(-not $SeedRun){
  $SeedRun=Join-Path $local 'daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
 }
 $seed=Source $SeedRun $true
 [void](Get-Command node -ErrorAction Stop)
 $py=Source (Join-Path $local 'frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe')
 $tool=Source (Join-Path $engine 'tools\no11_weekly_g1_catchup_20261028.mjs')
 $collector=Source (Join-Path $engine 'windows\Run-No11WeeklyCandidateCatchUpReadOnly.ps1')
 $preparer=Source (Join-Path $engine 'windows\Prepare-No11PreviousArchiveReadOnly.ps1')
 $verify=Source (Join-Path $engine 'tools\no11_verified_weekly_shadow_scope.mjs')
 $refreshRoot=Join-Path $local 'weekly-pool-refresh'
 if(-not (Test-Path -LiteralPath $refreshRoot)){[void][IO.Directory]::CreateDirectory($refreshRoot)}
 $refreshRoot=Source $refreshRoot $true
 Write-Host ('NO11_OCT28_CATCHUP_SOURCE='+$seed)
 Write-Host 'NO11_OCT28_CATCHUP_ASOF=2026-10-27'
 Write-Host 'NO11_OCT28_CATCHUP_RECEIPT_DAY=2026-10-28'
 Write-Host 'NO11_OCT28_CATCHUP_FUTURE_2026_10_28_BARS=EXCLUDED_FROM_G1'
 $planOutput=@(& node $tool plan --weekly-run $seed --root $refreshRoot --catch-up-asof '2026-10-27')
 Need ($LASTEXITCODE -eq 0 -and $planOutput.Count -eq 1) 'WEEKLY_429_PLAN_FAILED'
 $job=([string]$planOutput[0]|ConvertFrom-Json)
 Need ($job.weeklyRestrictedUniverse -eq $true -and
  [string]$job.plan.asOfSession -ceq '2026-10-27' -and
  @($job.plan.symbols).Count -eq 429 -and
  @($job.remaining).Count -le 429) 'PLAN_SCOPE_UNEXPECTED'
 $run=Source ([string]$job.run) $true
 Write-Host ('NO11_OCT28_CATCHUP_REMAINING='+@($job.remaining).Count+'/429')
 if(@($job.remaining).Count -gt 0){
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$collector,
   '-WeeklyRun',$seed,'-PrivateRoot',$refreshRoot,'-CatchUpAsOf','2026-10-27',
   '-BatchSize',[string]$BatchSize,'-WaitSeconds',[string]$WaitSeconds)
  & powershell.exe @args
  Need ($LASTEXITCODE -eq 0) 'ACTUAL_RSS_429_CAPTURE_INCOMPLETE'
 }else{
  Write-Host 'NO11_OCT28_CATCHUP_G1=COMPLETE_SOURCE_ALREADY_PRESENT'
 }
 $report=@(& node $tool report --run $run --weekly-run $seed --catch-up-asof '2026-10-27')
 $report|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'} | ForEach-Object {Write-Host $_}
 Need ($LASTEXITCODE -eq 0 -and $report -contains 'NO11_WEEKLY_REFRESH=COMPLETE_SHADOW_CAPACITY_ONLY') 'DAILY_G1_REPORT_INCOMPLETE'
 $chart=UniqueOutput $report 'NO11_WEEKLY_REFRESH_CHART50='
 $mask=UniqueOutput $report 'NO11_WEEKLY_REFRESH_MASK='
 $v=@(& node $verify --run-dir $run --weekly-source-run $seed --mask $mask --chart $chart --session '2026-10-28')
 $v|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'} | ForEach-Object {Write-Host $_}
 Need ($LASTEXITCODE -eq 0 -and $v -contains 'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED') 'G1_CHART_SOURCE_VERIFIER_FAILED'
 Write-Host 'NO11_OCT28_CATCHUP_G1=VERIFIED_REAL_D100_429_SELECTED'
 $prevRoot=Join-Path $local 'previous-source\2026-10-28'
 if(-not (Test-Path -LiteralPath $prevRoot)){[void][IO.Directory]::CreateDirectory($prevRoot)}
 $prevRoot=Source $prevRoot $true
 $existing=@(Get-ChildItem -LiteralPath $prevRoot -File -Filter 'previous-archive-stage-*.json' -ErrorAction Stop)
 $reuse=$false
 if($existing.Count -eq 1){
  $stage=Get-Content -LiteralPath (Source $existing[0].FullName) -Raw -Encoding UTF8|ConvertFrom-Json
  $chartObj=Get-Content -LiteralPath $chart -Raw -Encoding UTF8|ConvertFrom-Json
  $reuse=$stage.schemaId -ceq 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1' -and
   $stage.sessionDate -ceq '2026-10-28' -and $stage.previousSession -ceq '2026-10-27' -and
   $stage.chartPlanSha256 -ceq $chartObj.chartPlan.planSha256 -and
   $stage.orderTransmission -eq $false
 }
 if($existing.Count -gt 1){Need $false 'MULTIPLE_PREVIOUS_STAGE_RECEIPTS_REQUIRE_REVIEW'}
 if($reuse){
  Write-Host 'NO11_OCT28_CATCHUP_PREVIOUS_1M=REUSED_EXISTING_MATCHING_STAGE'
 }else{
  # Full 1M capture is strictly AFTER G1 collector closes its temporary book.
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$preparer,
   '-SessionDate','2026-10-28','-RunDir',$run,
   '-PrivateRoot',$prevRoot,'-PythonExecutable',$py,
   '-PrecomputedChartPlanFile',$chart,'-PrecomputedMaskFile',$mask,
   '-BatchSize',[string]$PreviousBatchSize,'-WaitSeconds',[string]$PreviousWaitSeconds)
  & powershell.exe @args
  Need ($LASTEXITCODE -eq 0) 'ACTUAL_RSS_OCT27_PREVIOUS_MINUTES_INCOMPLETE'
 }
 $stageFile=UniqueFile $prevRoot 'previous-archive-stage-*.json' 'PREVIOUS_STAGE_REQUIRED'
 $stage=Get-Content -LiteralPath $stageFile -Raw -Encoding UTF8|ConvertFrom-Json
 $chartData=Get-Content -LiteralPath $chart -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($stage.sessionDate -ceq '2026-10-28' -and
  $stage.previousSession -ceq '2026-10-27' -and
  $stage.chartPlanSha256 -ceq $chartData.chartPlan.planSha256 -and
  $stage.orderTransmission -eq $false) 'PREVIOUS_STAGE_WRONG_PLAN_OR_DAY'
 $valid=@($stage.symbols.PSObject.Properties).Count
 $unavailable=@($stage.omittedSymbols.PSObject.Properties).Count
 Write-Host ('NO11_OCT28_CATCHUP_PREVIOUS_MINUTES='+$valid+'|MISSING='+$unavailable)
 Write-Host ('NO11_OCT28_CATCHUP_G1_RUN='+$run)
 Write-Host ('NO11_OCT28_CATCHUP_CHART='+$chart)
 Write-Host ('NO11_OCT28_CATCHUP_MASK='+$mask)
 Write-Host 'NO11_OCT28_CATCHUP_INDEPENDENT_REVIEW=STILL_REQUIRED'
 Write-Host 'NO11_OCT28_CATCHUP_FROZEN_MODELS_CHANGED=False'
 Write-Host 'NO11_OCT28_CATCHUP=REAL_RSS_SOURCE_STAGED_NOT_SHADOW_AUTHORIZED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_OCT28_CATCHUP_[A-Z0-9_]+$'){
  $reason='NO11_OCT28_CATCHUP_SOURCE_OR_RUNTIME_FAILURE'
 }
 Write-Host ('NO11_OCT28_CATCHUP=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
