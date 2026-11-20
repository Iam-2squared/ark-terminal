# Automated after-close G1 -> next-session previous-minute staging, orders OFF.
# This does not manufacture externally reviewed corporate action evidence, and
# never launches Selector, a portfolio, account orders or a trading service.
# Run in the same interactive Windows Excel session as the two original workbooks.
param(
 [string]$SessionDate='2026-10-27',
 [string]$AsOfSession='2026-10-26',
 [string]$SymbolsFile='',
 [string]$DailyRoot='',
 [string]$OutputRoot='',
 [string]$PythonExecutable='',
 [string]$PinsFile='',
 [switch]$WeekendFriday,
 [ValidateRange(1,20)][int]$DailyBatchSize=20,
 [ValidateRange(5,60)][int]$DailyWaitSeconds=15,
 [ValidateRange(1,20)][int]$MinuteBatchSize=5,
 [ValidateRange(5,60)][int]$MinuteWaitSeconds=20,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$base=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$dailyScript=Join-Path $PSScriptRoot 'Run-No11RssDailyTrendCensusReadOnly.ps1'
$previousScript=Join-Path $PSScriptRoot 'Prepare-No11PreviousArchiveReadOnly.ps1'
$maskTool=Join-Path $base 'tools\no11_export_observed_pass_watch_mask.mjs'
$planTool=Join-Path $base 'tools\no11_export_chart50_prescreen.mjs'

function Need([bool]$ok,[string]$code) {
 if(-not $ok){throw ('NO11_NIGHTLY_'+$code)}
}
function Get-ReceiptPath([object[]]$lines,[string]$prefix) {
 $matched=@($lines|Where-Object {([string]$_).StartsWith($prefix,[StringComparison]::Ordinal)})
 Need ($matched.Count -eq 1) 'RECEIPT_NOT_UNIQUE'
 $value=([string]$matched[0]).Substring($prefix.Length)
 Need ([IO.Path]::IsPathRooted($value) -and (Test-Path -LiteralPath $value -PathType Leaf)) 'RECEIPT_FILE_MISSING'
 return $value
}
function TodayJst {
 return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
}
function AbsoluteOutsideRepo([string]$value,[string]$code) {
 Need ([IO.Path]::IsPathRooted($value)) ($code+'_NOT_ABSOLUTE')
 $resolved=[IO.Path]::GetFullPath($value)
 $repository=[IO.Path]::GetFullPath((Join-Path $base '..\..\..'))
 Need (-not $resolved.Equals($repository,[StringComparison]::OrdinalIgnoreCase) -and
  -not $resolved.StartsWith($repository+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) ($code+'_IN_REPOSITORY')
 return $resolved
}
try {
 foreach($s in @($dailyScript,$previousScript,$maskTool,$planTool)){
  Need (Test-Path -LiteralPath $s -PathType Leaf) 'SOURCE_SCRIPT_MISSING'
 }
 $date=[datetime]::MinValue
 $prior=[datetime]::MinValue
 Need ([datetime]::TryParseExact($SessionDate,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture,
  [Globalization.DateTimeStyles]::None,[ref]$date)) 'SESSION_DATE_INVALID'
 Need ([datetime]::TryParseExact($AsOfSession,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture,
  [Globalization.DateTimeStyles]::None,[ref]$prior)) 'ASOF_DATE_INVALID'
 Need ($date -gt $prior -and ($date-$prior).TotalDays -le 5) 'SESSION_ASOF_RELATION_INVALID'
 if($OfflineSelfTest){
  Write-Host 'NO11_NIGHTLY_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_NIGHTLY_EXCEL_STARTED=False'
  Write-Host 'NO11_NIGHTLY_TRADE_ENGINE_STARTED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 if([string]::IsNullOrWhiteSpace($SymbolsFile)){
  $SymbolsFile=Join-Path $env:USERPROFILE 'Downloads\rss_symbols_to_acquire.txt'
 }
 if([string]::IsNullOrWhiteSpace($DailyRoot)){
  $DailyRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture'
 }
 if([string]::IsNullOrWhiteSpace($OutputRoot)){
  $OutputRoot=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\previous-source\'+$SessionDate)
 }
 if([string]::IsNullOrWhiteSpace($PythonExecutable)){
  $PythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 }
 $DailyRoot=AbsoluteOutsideRepo $DailyRoot 'DAILY_ROOT'
 $OutputRoot=AbsoluteOutsideRepo $OutputRoot 'OUTPUT_ROOT'
 Need ([IO.Path]::IsPathRooted($SymbolsFile) -and (Test-Path -LiteralPath $SymbolsFile -PathType Leaf)) 'SYMBOLS_FILE_MISSING'
 Need ([IO.Path]::IsPathRooted($PythonExecutable) -and (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) 'PINNED_PYTHON_MISSING'
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){
  Need ([IO.Path]::IsPathRooted($PinsFile) -and (Test-Path -LiteralPath $PinsFile -PathType Leaf)) 'PINS_FILE_MISSING'
 }

 $now=TodayJst
 # The actual underlying G1/D100 collector uses real current receipts and
 # requires the same real previous Friday as-of source. On Sat/Sun we can
 # explicitly resume the prior-Friday scan when RSS remains connected.
 # Do not pretend any new market close exists on the weekend.
 if($WeekendFriday){
  $weekday=$now.DayOfWeek
  Need ($weekday -eq [DayOfWeek]::Saturday -or
        $weekday -eq [DayOfWeek]::Sunday) 'WEEKEND_MODE_SAT_SUN_ONLY'
  $prior=if($weekday -eq [DayOfWeek]::Saturday){$now.AddDays(-1)}else{$now.AddDays(-2)}
  Need ($prior.ToString('yyyy-MM-dd') -ceq $AsOfSession -and
        $prior.DayOfWeek -eq [DayOfWeek]::Friday) 'ACTUAL_PRIOR_FRIDAY_REQUIRED'
  Write-Host ('NO11_NIGHTLY_WEEKEND_ACTUAL_FRIDAY_ASOF='+$AsOfSession)
  Write-Host 'NO11_NIGHTLY_WEEKEND_RSS_NOT_GUARANTEED=True'
 }else{
  Need ($now.ToString('yyyy-MM-dd') -ceq $AsOfSession -and
        $now.ToString('HH:mm') -cge '18:00') 'DAILY_NOT_YET_ELIGIBLE'
 }
 [void][IO.Directory]::CreateDirectory($DailyRoot)
 [void][IO.Directory]::CreateDirectory($OutputRoot)

 Write-Host '=== NIGHTLY STAGE 1: FULL-UNIVERSE DAILY G1 ==='
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dailyScript `
  -SymbolsFile $SymbolsFile -PrivateRoot $DailyRoot `
  -BatchSize $DailyBatchSize -WaitSeconds $DailyWaitSeconds
 Need ($LASTEXITCODE -eq 0) 'DAILY_G1_CAPTURE_FAILED'

 # Resolve the same immutable, code-pinned run used by the daily collector.
 # Historical as-of folders may coexist after code revisions; their mere
 # existence must not make a successfully resumed G1 capture unusable.
 $identityTool=Join-Path $base 'tools\no11_rss_daily_trend_census.mjs'
 Need (Test-Path -LiteralPath $identityTool -PathType Leaf) 'DAILY_IDENTITY_TOOL_MISSING'
 $identityLines=@(& node $identityTool plan --symbols $SymbolsFile --root $DailyRoot)
 Need ($LASTEXITCODE -eq 0 -and $identityLines.Count -eq 1) 'DAILY_IDENTITY_RESOLUTION_FAILED'
 $identity=([string]$identityLines[0] | ConvertFrom-Json)
 $run=[string]$identity.run
 Need ([IO.Path]::IsPathRooted($run) -and
  (Test-Path -LiteralPath (Join-Path $run 'plan.json') -PathType Leaf) -and
  $identity.plan.asOfSession -ceq $AsOfSession -and
  $identity.plan.schemaId -ceq 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1' -and
  @($identity.remaining).Count -eq 0) 'DAILY_G1_RESOLVED_PLAN_INCOMPLETE'

 Write-Host '=== NIGHTLY STAGE 2: OBSERVED PASS AND CHART50 PLAN ==='
 $mask=@(& node $maskTool --run $run)
 Need ($LASTEXITCODE -eq 0) 'G1_MASK_FAILED'
 $mask|ForEach-Object {Write-Host $_}
 $maskFile=Get-ReceiptPath $mask 'NO11_DAILY_PASS_WATCH_FILE='

 $planArgs=@('--run',$run,'--session',$SessionDate)
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$planArgs+=@('--pins-file',$PinsFile)}
 $chart=@(& node $planTool @planArgs)
 Need ($LASTEXITCODE -eq 0) 'CHART50_PLAN_FAILED'
 $chart|ForEach-Object {Write-Host $_}
 $chartFile=Get-ReceiptPath $chart 'NO11_CHART50_RECEIPT='
 $receipt=Get-Content -LiteralPath $chartFile -Raw -Encoding UTF8|ConvertFrom-Json
 $eligible=@($receipt.chartPlan.selectorInputSymbols)
 Need ($eligible.Count -ge 1 -and $eligible.Count -le 50) 'NO_ELIGIBLE_CHART_SYMBOLS'
 if([string]::IsNullOrWhiteSpace($PinsFile)){
  Write-Host 'NO11_NIGHTLY_PINS_STATUS=CAPACITY_ONLY_NO_BROKER_POSITION_CERTIFICATION'
 }else{
  Write-Host 'NO11_NIGHTLY_PINS_STATUS=USER_SUPPLIED_NOT_BROKER_CERTIFIED'
 }

 Write-Host '=== NIGHTLY STAGE 3: ORIGINAL PREVIOUS-SESSION 1M ARCHIVE ==='
 $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$previousScript,
  '-SessionDate',$SessionDate,'-RunDir',$run,
  '-PrivateRoot',$OutputRoot,'-PythonExecutable',$PythonExecutable,
  '-BatchSize',[string]$MinuteBatchSize,
  '-WaitSeconds',[string]$MinuteWaitSeconds)
 if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$args+=@('-PinsFile',$PinsFile)}
 & powershell.exe @args
 Need ($LASTEXITCODE -eq 0) 'PREVIOUS_1M_ARCHIVE_FAILED'

 Write-Host ('NO11_NIGHTLY_DAILY_RUN='+$run)
 Write-Host ('NO11_NIGHTLY_MASK='+$maskFile)
 Write-Host ('NO11_NIGHTLY_CHART50='+$chartFile)
 Write-Host ('NO11_NIGHTLY_PREVIOUS_OUTPUT='+$OutputRoot)
 Write-Host 'NO11_NIGHTLY_STAGE=DAILY_AND_PREVIOUS_ARCHIVE_PREPARED'
 Write-Host 'NO11_NIGHTLY_NOT_YET_READY=DATED_MASTER_SECURITY_EVIDENCE_AND_BOOTSTRAP'
 Write-Host 'NO11_NIGHTLY_SELECTOR_OR_PORTFOLIO_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
} catch {
 $message=$_.Exception.Message
 if($message -cnotmatch '^NO11_NIGHTLY_[A-Z0-9_]+$'){$message='NO11_NIGHTLY_PRIVATE_INPUT_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_NIGHTLY_STAGE=BLOCKED|'+$message)
 Write-Host 'NO11_NIGHTLY_SELECTOR_OR_PORTFOLIO_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
