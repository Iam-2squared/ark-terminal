# No.1.1 nightly orchestration: FRIDAY full universe, Mon-Thu weekly-pool
# candidates only. Fully observed daily close still required for each of the
# pool candidates; all other symbols remain OUTSIDE the weekly scan.
# Does not start Selector/portfolio or send orders. Excel RSS permissions OFF.
param(
 [string]$FullSymbolsFile='',
 [string]$DailyRoot='',
 [string]$RefreshRoot='',
 [string]$OutputRoot='',
 [string]$PythonExecutable='',
 [string]$WeeklyRun='',
 [string]$PinsFile='',
 [ValidateRange(1,20)][int]$FullBatchSize=10,
 [ValidateRange(5,60)][int]$FullWaitSeconds=15,
 [ValidateRange(1,20)][int]$RefreshBatchSize=10,
 [ValidateRange(5,60)][int]$RefreshWaitSeconds=15,
 [ValidateRange(1,20)][int]$MinuteBatchSize=5,
 [ValidateRange(5,60)][int]$MinuteWaitSeconds=20,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest

$base=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$tool=Join-Path $base 'tools\no11_weekly_g1_refresh.mjs'
$full=Join-Path $PSScriptRoot 'Prepare-No11NextSessionNightlyReadOnly.ps1'
$refresh=Join-Path $PSScriptRoot 'Run-No11WeeklyCandidateRefreshReadOnly.ps1'
$previous=Join-Path $PSScriptRoot 'Prepare-No11PreviousArchiveReadOnly.ps1'
function Need([bool]$value,[string]$code) {if(-not $value){throw ('NO11_WEEKLY_NIGHTLY_'+$code)}}
function PathOutsideRepo([string]$p,[string]$code) {
 Need ([IO.Path]::IsPathRooted($p)) ($code+'_ABSOLUTE_REQUIRED')
 $p=[IO.Path]::GetFullPath($p)
 $repo=[IO.Path]::GetFullPath((Join-Path $base '..\..\..'))
 Need (-not $p.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -and
  -not $p.StartsWith($repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) ($code+'_INSIDE_REPOSITORY')
 return $p
}
try{
 foreach($p in @($tool,$full,$refresh,$previous)){
  Need (Test-Path -LiteralPath $p -PathType Leaf) 'SOURCE_SCRIPT_MISSING'
 }
 if($OfflineSelfTest){
  Write-Host 'NO11_WEEKLY_NIGHTLY_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_WEEKLY_NIGHTLY_EXCEL_STARTED=False'
  Write-Host 'NO11_WEEKLY_NIGHTLY_FULL_SCAN_EXECUTED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 if([string]::IsNullOrWhiteSpace($FullSymbolsFile)){
  $FullSymbolsFile=Join-Path $env:USERPROFILE 'Downloads\rss_symbols_to_acquire.txt'
 }
 if([string]::IsNullOrWhiteSpace($DailyRoot)){
  $DailyRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture'
 }
 if([string]::IsNullOrWhiteSpace($RefreshRoot)){
  $RefreshRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\weekly-pool-refresh'
 }
 if([string]::IsNullOrWhiteSpace($PythonExecutable)){
  $PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 }
 $DailyRoot=PathOutsideRepo $DailyRoot 'DAILY_ROOT'
 $RefreshRoot=PathOutsideRepo $RefreshRoot 'REFRESH_ROOT'
 Need ([IO.Path]::IsPathRooted($PythonExecutable) -and
  (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) 'PINNED_PYTHON_MISSING'
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){
  Need ([IO.Path]::IsPathRooted($PinsFile) -and
   (Test-Path -LiteralPath $PinsFile -PathType Leaf)) 'PINS_FILE_MISSING'
 }

 $scheduleLines=@(& node $tool schedule)
 Need ($LASTEXITCODE -eq 0 -and $scheduleLines.Count -eq 1) 'SCHEDULE_FAILED'
 $schedule=([string]$scheduleLines[0] | ConvertFrom-Json)
 Need ($schedule.schemaId -ceq 'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1' -and
  $schedule.orderTransmission -eq $false) 'SCHEDULE_CONTRACT_INVALID'
 $mode=[string]$schedule.mode
 $session=[string]$schedule.sessionDate
 $asOf=[string]$schedule.asOfSession
 if([string]::IsNullOrWhiteSpace($OutputRoot)){
  $OutputRoot=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\previous-source\'+$session)
 }
 $OutputRoot=PathOutsideRepo $OutputRoot 'OUTPUT_ROOT'

 Write-Host ('NO11_WEEKLY_NIGHTLY_ASOF='+$asOf)
 Write-Host ('NO11_WEEKLY_NIGHTLY_NEXT_SESSION='+$session)
 Write-Host ('NO11_WEEKLY_NIGHTLY_MODE='+$mode)

 if($mode -ceq 'FULL_MARKET_FRIDAY'){
 Need ([IO.Path]::IsPathRooted($FullSymbolsFile) -and
  (Test-Path -LiteralPath $FullSymbolsFile -PathType Leaf)) 'FULL_SYMBOL_LIST_MISSING'

  # The unchanged full-market path still checks exact source hashes and RSS.
  $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$full,
   '-SessionDate',$session,'-AsOfSession',$asOf,
   '-SymbolsFile',$FullSymbolsFile,
   '-DailyRoot',$DailyRoot,
   '-OutputRoot',$OutputRoot,
   '-PythonExecutable',$PythonExecutable,
   '-DailyBatchSize',[string]$FullBatchSize,
   '-DailyWaitSeconds',[string]$FullWaitSeconds,
   '-MinuteBatchSize',[string]$MinuteBatchSize,
   '-MinuteWaitSeconds',[string]$MinuteWaitSeconds)
  if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$arguments+=@('-PinsFile',$PinsFile)}
  Write-Host 'NO11_WEEKLY_NIGHTLY_FULL_SCAN=FRIDAY_ONLY'
  & powershell.exe @arguments
  Need ($LASTEXITCODE -eq 0) 'FRIDAY_FULL_SCAN_FAILED'
  Write-Host 'NO11_WEEKLY_NIGHTLY_STAGE=FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need ($mode -ceq 'WEEKLY_POOL_CANDIDATES_ONLY') 'UNKNOWN_SCHEDULE_MODE'

 # Use an explicit pinned source if supplied. Otherwise choose the most recent
 # complete Friday full sweep; Monday 2026-10-26 seed is a one-time exception.
 if([string]::IsNullOrWhiteSpace($WeeklyRun)){
  $choices=@(
   foreach($dir in @(Get-ChildItem -LiteralPath $DailyRoot -Directory -Filter 'daily-*' -ErrorAction SilentlyContinue)){
    $planPath=Join-Path $dir.FullName 'plan.json'
    $sourceDir=Join-Path $dir.FullName 'sources'
    if(-not (Test-Path -LiteralPath $planPath -PathType Leaf) -or
       -not (Test-Path -LiteralPath $sourceDir -PathType Container)){continue}
    try {
     $plan=Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
     $date=[datetime]::MinValue
     if(-not [datetime]::TryParseExact([string]$plan.asOfSession,'yyyy-MM-dd',
       [Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$date)){continue}
     if(($date.DayOfWeek -ne [DayOfWeek]::Friday -and
        [string]$plan.asOfSession -cne '2026-10-26') -or
        $plan.schemaId -cne 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1'){continue}
     $count=@(Get-ChildItem -LiteralPath $sourceDir -File -Filter '*.json').Count
     if($count -ne @($plan.symbols).Count){continue}
     [pscustomobject]@{run=$dir.FullName;date=[string]$plan.asOfSession}
    } catch {continue}
   }
  )
  Need ($choices.Count -gt 0) 'COMPLETE_FULL_SWEEP_NOT_FOUND'
  $latest=@($choices|Sort-Object date -Descending|Select-Object -First 1)
  Need ($latest.Count -eq 1) 'FULL_SWEEP_SELECTION_AMBIGUOUS'
  $WeeklyRun=[string]$latest[0].run
 }
 $WeeklyRun=PathOutsideRepo $WeeklyRun 'WEEKLY_RUN'
 Need (Test-Path -LiteralPath $WeeklyRun -PathType Container) 'WEEKLY_SOURCE_DIRECTORY_MISSING'

 Write-Host ('NO11_WEEKLY_NIGHTLY_POOL_SOURCE='+$WeeklyRun)
 $rargs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$refresh,
  '-WeeklyRun',$WeeklyRun,
  '-PrivateRoot',$RefreshRoot,
  '-BatchSize',[string]$RefreshBatchSize,
  '-WaitSeconds',[string]$RefreshWaitSeconds)
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$rargs+=@('-PinsFile',$PinsFile)}
 & powershell.exe @rargs
 Need ($LASTEXITCODE -eq 0) 'DAILY_POOL_REFRESH_FAILED'

 # Return to the exact code-pinned, immutable daily refresh run we just wrote.
 $details=@(& node $tool plan --weekly-run $WeeklyRun --root $RefreshRoot)
 Need ($LASTEXITCODE -eq 0 -and $details.Count -eq 1) 'REFRESH_RUN_IDENTITY_FAILED'
 $result=([string]$details[0]|ConvertFrom-Json)
 Need ($result.plan.asOfSession -ceq $asOf -and
  @($result.remaining).Count -eq 0 -and
  $result.weeklyRestrictedUniverse -eq $true) 'REFRESH_CAPTURE_INCOMPLETE'

 $pargs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$previous,
  '-SessionDate',$session,
  '-RunDir',[string]$result.run,
  '-PrivateRoot',$OutputRoot,
  '-PythonExecutable',$PythonExecutable,
  '-BatchSize',[string]$MinuteBatchSize,
  '-WaitSeconds',[string]$MinuteWaitSeconds)
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$pargs+=@('-PinsFile',$PinsFile)}
 & powershell.exe @pargs
 Need ($LASTEXITCODE -eq 0) 'SELECTED_PREVIOUS_1M_FAILED'

 Write-Host ('NO11_WEEKLY_NIGHTLY_REFRESH_RUN='+[string]$result.run)
 Write-Host 'NO11_WEEKLY_NIGHTLY_STAGE=CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE'
 Write-Host 'NO11_WEEKLY_NIGHTLY_NEW_BREAKOUTS_OUTSIDE_POOL=NOT_SCANNED'
 Write-Host 'NO11_WEEKLY_NIGHTLY_STILL_REQUIRED=DATED_MASTER_SECURITY_REVIEW_AND_SHADOW_PREFLIGHT'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_WEEKLY_NIGHTLY_[A-Z0-9_]+$'){$reason='NO11_WEEKLY_NIGHTLY_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_WEEKLY_NIGHTLY_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
