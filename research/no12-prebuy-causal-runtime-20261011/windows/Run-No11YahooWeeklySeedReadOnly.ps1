# Optional weekly Yahoo G1 universe seed. Only daily history is Yahoo.
# Yahoo automated access is DISABLED absent explicit prior permission.
# Never install Python packages, open Excel, access broker, certify master,
# change Frozen G1/Selector/P1/H235/V5/EXIT, or enable order transmission.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$OriginalSeedRun='',
 [string]$YahooRoot='',
 [string]$YahooSourceRun='',
 [string]$AsOfSession='',
 [string]$YahooPythonExecutable='',
 [switch]$FetchYahoo,
 [switch]$PersonalResearchTermsAcknowledged,
 [switch]$YahooAutomatedAccessPermissionConfirmed,
 [ValidateRange(1,32)][int]$BatchSize=16,
 [ValidateRange(3,60)][double]$PauseSeconds=5,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$value,[string]$code){if(-not $value){throw ('NO11_YAHOO_WEEKLY_RUN_'+$code)}}
function SafePrivate([string]$candidate,[bool]$dir){
 Need ([IO.Path]::IsPathRooted($candidate)) 'ABSOLUTE_PRIVATE_PATH_REQUIRED'
 $path=[IO.Path]::GetFullPath($candidate)
 $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
 Need (-not $path.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -and
  -not $path.StartsWith($repo+'\', [StringComparison]::OrdinalIgnoreCase)) 'REPOSITORY_PRIVATE_BOUNDARY'
 Need (Test-Path -LiteralPath $path -PathType $(if($dir){'Container'}else{'Leaf'})) 'PRIVATE_SOURCE_NOT_FOUND'
 $p=$path
 while(-not [string]::IsNullOrEmpty($p)){
  $entry=Get-Item -LiteralPath $p -Force
  Need (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  $next=Split-Path -Parent $p;if($next -ceq $p){break};$p=$next
 }
 return $path
}
if($OfflineSelfTest){
 Need ($BatchSize -ge 1 -and $BatchSize -le 32) 'SELFTEST_BATCH_BOUND'
 Write-Host 'NO11_YAHOO_WEEKLY_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_YAHOO_WEEKLY_YFINANCE_FETCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $date=[datetime]::MinValue
 Need ([datetime]::TryParseExact($AsOfSession,'yyyy-MM-dd',
  [Globalization.CultureInfo]::InvariantCulture,
  [Globalization.DateTimeStyles]::None,[ref]$date) -and
  $date.DayOfWeek -eq [DayOfWeek]::Friday) 'FRIDAY_ASOF_REQUIRED'
 Need ([IO.Path]::IsPathRooted($EngineRoot) -and
  (Test-Path -LiteralPath $EngineRoot -PathType Container)) 'ENGINE_ROOT_MISSING'
 $engine=[IO.Path]::GetFullPath($EngineRoot)
 $original=if($OriginalSeedRun){$OriginalSeedRun}else{
  Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-26-e84a2ec53b0fdf41'
 }
 $original=SafePrivate $original $true
 $sourcePlan=SafePrivate (Join-Path $original 'plan.json') $false
 [void](Get-Command node -ErrorAction Stop)
 $seedTool=Join-Path $engine 'tools\no11_yahoo_weekly_seed.mjs'
 Need (Test-Path -LiteralPath $seedTool -PathType Leaf) 'WEEKLY_SEED_VALIDATOR_MISSING'
 if(-not $YahooRoot){$YahooRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\yahoo-weekly-cache'}
 $YahooRoot=[IO.Path]::GetFullPath($YahooRoot)
 if($FetchYahoo){
  Need ($PersonalResearchTermsAcknowledged -and
   $YahooAutomatedAccessPermissionConfirmed) 'EXPRESS_YAHOO_AUTOMATED_PERMISSION_REQUIRED'
  if(-not $YahooPythonExecutable){
   $YahooPythonExecutable=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\yahoo-isolated-venv\Scripts\python.exe'
  }
  $python=SafePrivate $YahooPythonExecutable $false
  Need (-not $python.StartsWith((Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay')+'\',
    [StringComparison]::OrdinalIgnoreCase)) 'YAHOO_MUST_NOT_USE_FROZEN_MODEL_VENV'
  $fetchTool=Join-Path $engine 'tools\no11_yahoo_weekly_history.py'
  Need (Test-Path -LiteralPath $fetchTool -PathType Leaf) 'UNOFFICIAL_IMPORTER_MISSING'
  $args=@('-B',$fetchTool,'--original-plan',$sourcePlan,'--asof',$AsOfSession,
   '--private-root',$YahooRoot,'--personal-research-terms-acknowledged',
   '--yahoo-automated-access-permission-confirmed',
   '--batch-size',[string]$BatchSize,'--pause-seconds',[string]$PauseSeconds)
  $output=@(& $python @args)
  $code=$LASTEXITCODE
  $output|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'}|
   ForEach-Object {Write-Host $_}
  Need ($code -eq 0) 'YAHOO_DAILY_SOURCE_CAPTURE_INCOMPLETE'
  $found=@($output|Where-Object {([string]$_).StartsWith('NO11_YAHOO_WEEKLY_SOURCE_DIR=')})
  Need ($found.Count -eq 1) 'SOURCE_DIR_OUTPUT_REQUIRED'
  $YahooSourceRun=([string]$found[0]).Substring('NO11_YAHOO_WEEKLY_SOURCE_DIR='.Length)
 }
 if(-not $YahooSourceRun){
  Need (Test-Path -LiteralPath $YahooRoot -PathType Container) 'YAHOO_SOURCE_ROOT_REQUIRED'
  $runs=@(Get-ChildItem -LiteralPath $YahooRoot -Directory -Filter ('yahoo-weekly-'+$AsOfSession+'-*'))
  Need ($runs.Count -eq 1) 'YAHOO_SOURCE_RUN_MISSING_OR_AMBIGUOUS'
  $YahooSourceRun=$runs[0].FullName
 }
 $run=SafePrivate $YahooSourceRun $true
 Need ($run.StartsWith($YahooRoot.TrimEnd('\')+'\',
   [StringComparison]::OrdinalIgnoreCase)) 'YAHOO_SOURCE_RUN_WRONG_PRIVATE_ROOT'
 $lines=@(& node $seedTool build --source-run $run --original-rss-seed $original)
 $exit=$LASTEXITCODE
 $lines|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'}|
  ForEach-Object {Write-Host $_}
 Need ($exit -eq 0 -and
  $lines -contains 'NO11_YAHOO_WEEKLY_SEED=PASS_PROVISIONAL_NOT_TRADE_CERTIFIED') 'WEEKLY_G1_NOT_VERIFIED'
 Write-Host 'NO11_YAHOO_WEEKLY_NEXT_STEP=DAILY_RSS_POOL_CONFIRMATION'
 Write-Host 'NO11_YAHOO_WEEKLY_NO_FULL_MARKET_RSS_SWEEP=True'
 Write-Host 'NO11_YAHOO_WEEKLY_TRADE_AUTHORIZED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $msg=$_.Exception.Message
 if($msg -cnotmatch '^NO11_YAHOO_WEEKLY_RUN_[A-Z0-9_]+$'){$msg='NO11_YAHOO_WEEKLY_RUN_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_YAHOO_WEEKLY_RUN=BLOCKED|'+$msg)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
