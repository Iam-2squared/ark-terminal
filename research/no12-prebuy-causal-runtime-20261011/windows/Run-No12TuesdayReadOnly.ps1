# Ark Terminal No.1.1 Tuesday READ ONLY preflight, one sequential entrypoint.
# Does NOT write to an existing workbook, authorize RSS orders or unlock Safety.
param([switch]$OfflineSelfTest,[switch]$PhysicalReadOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OfflineSelfTest -eq $PhysicalReadOnly){
 throw 'NO12_RUNNER_SELECT_EXACTLY_ONE_MODE'
}
$root=Split-Path -Parent $PSScriptRoot
$repoRoot=Split-Path -Parent (Split-Path -Parent $root)
$branch='research/no12-prebuy-causal-runtime-20261011'
$lock=$null
function Invoke-No12Child([string]$script,[string[]]$arguments,[string]$expected) {
 if(-not (Test-Path -LiteralPath $script -PathType Leaf)){
   throw 'NO12_RUNNER_SCRIPT_MISSING'
 }
 $ps=(Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
 $lines=@(& $ps -NoProfile -ExecutionPolicy Bypass -File $script @arguments)
 if($LASTEXITCODE -ne 0){throw 'NO12_RUNNER_CHILD_BLOCKED'}
 if(@($lines | Where-Object { $_ -ceq $expected }).Count -ne 1){
   throw 'NO12_RUNNER_CHILD_RECEIPT_NOT_VERIFIED'
 }
 if(@($lines | Where-Object { $_ -ceq 'ORDER_TRANSMISSION=False' }).Count -ne 1){
   throw 'NO12_RUNNER_ORDER_LOCK_NOT_VERIFIED'
 }
 Write-Host $expected
 Write-Host 'ORDER_TRANSMISSION=False'
}
try{
 $git=(Get-Command git -CommandType Application -ErrorAction Stop).Source
 $actualRoot=(& $git -C $repoRoot rev-parse --show-toplevel)
 if($LASTEXITCODE -ne 0 -or -not $actualRoot){throw 'NO12_RUNNER_GIT_WORKTREE_REQUIRED'}
 if($PhysicalReadOnly){
   $actualBranch=(& $git -C $repoRoot symbolic-ref --quiet --short HEAD)
   if($LASTEXITCODE -ne 0 -or $actualBranch -cne $branch){
     throw 'NO12_RUNNER_WRONG_BRANCH_OR_DETACHED'
   }
   & $git -C $repoRoot diff --quiet
   if($LASTEXITCODE -ne 0){throw 'NO12_RUNNER_DIRTY_TRACKED_WORKTREE'}
   & $git -C $repoRoot diff --cached --quiet
   if($LASTEXITCODE -ne 0){throw 'NO12_RUNNER_DIRTY_STAGED_WORKTREE'}
   if([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)){
     throw 'NO12_RUNNER_PRIVATE_LOCALAPPDATA_REQUIRED'
   }
   $privateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
   [void](New-Item -ItemType Directory -Force -Path $privateRoot -ErrorAction Stop)
   $lockFile=Join-Path $privateRoot 'tuesday-readonly-runner.lock'
   $lock=[System.IO.File]::Open(
      $lockFile,[System.IO.FileMode]::OpenOrCreate,
      [System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
 }
 $five=Join-Path $PSScriptRoot 'Probe-No12MarketRssChartReadOnly.ps1'
 $one=Join-Path $PSScriptRoot 'Probe-No12MarketRss1mReadOnly.ps1'
 $seconds=Join-Path $PSScriptRoot 'Probe-No12RssMarketSecondsReadOnly.ps1'
 if($OfflineSelfTest){
   Invoke-No12Child -script $five -arguments @('-OfflineSelfTest') -expected 'NO12_RSS_CHART_FORMULA_SELFTEST_PASS=True'
   Invoke-No12Child -script $one -arguments @('-OfflineSelfTest') -expected 'NO12_RSS_CHART_FORMULA_SELFTEST_PASS=True'
   Invoke-No12Child -script $seconds -arguments @('-OfflineSelfTest') -expected 'NO12_SECONDS_RSS_FORMULA_SELFTEST_PASS=True'
   Write-Host 'NO12_TUESDAY_OFFLINE_SELFTEST_PASS=True'
 }else{
   # Each child opens one UNSAVED temporary Excel workbook and closes it.
   # Stop immediately on first failure. Never run market probes concurrently.
   Invoke-No12Child -script $five -arguments @('-WaitSeconds','20','-HistoryBars','500') -expected 'NO12_RSS_CHART_PRIVATE_READ_ONLY_RECEIPT=True'
   Invoke-No12Child -script $one -arguments @('-WaitSeconds','20','-HistoryBars','2000') -expected 'NO12_1M_PRIVATE_READ_ONLY_RECEIPT=True'
   Invoke-No12Child -script $seconds -arguments @('-Samples','5','-IntervalSeconds','2','-WarmupSeconds','5') -expected 'NO11_RSS_SECONDS_ASOF_STATUS=LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY'
   Write-Host 'NO12_TUESDAY_MARKET_OBSERVATIONS_COMPLETE_READ_ONLY=True'
 }
 Write-Host 'NO11_NATIVE_SELECTOR_READY=False'
 Write-Host 'NO11_NATIVE_H2H3H5_READY=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 # Only fixed NO12_* error codes; never log private paths or account data.
 $reason=$_.Exception.Message
 if($reason -cmatch '^NO12_[A-Z0-9_]+
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 throw 'NO12_TUESDAY_READ_ONLY_RUNNER_STOPPED_SAFELY'
}finally{
 if($null -ne $lock){$lock.Dispose()}
}
){Write-Host ('NO12_TUESDAY_RUNNER_REASON='+$reason)}
 Write-Host 'NO12_TUESDAY_RUNNER_BLOCKED=True'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 throw 'NO12_TUESDAY_READ_ONLY_RUNNER_STOPPED_SAFELY'
}finally{
 if($null -ne $lock){$lock.Dispose()}
}
