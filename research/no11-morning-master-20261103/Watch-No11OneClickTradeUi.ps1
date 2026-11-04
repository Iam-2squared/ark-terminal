# OneClick UI-only handoff watcher. The native Trade launcher already opens UI2.
# Observe the native result; retry the read-only UI helper only after an
# explicit native UI failure and confirmed SAME-DAY Trade launch marker.
# NEVER starts Trade, modifies a ledger/marker, or grants an order permission.
param(
 [string]$NativeLog='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_ONECLICK_UI2_'+$code)}
}
function Get-UiOutcome([string[]]$lines){
 $trade=@($lines|Where-Object{$_ -cmatch '^NO11_UNIFIED_TRADE_LAUNCHED_PID=[0-9]+$'})
 $ui=@($lines|Where-Object{$_ -clike 'NO11_UNIFIED_UI2_LIVE=*'})
 if($trade.Count -ne 1){return 'NO_CONFIRMED_TRADE_REQUEST'}
 if($ui.Count -gt 1){return 'AMBIGUOUS_UI_RESULT'}
 if($ui.Count -eq 0){return 'PENDING'}
 if($ui[0] -ceq 'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_BROWSER_REQUESTED'){
  return 'NATIVE_UI_OPEN_REQUESTED'
 }
 if($ui[0] -ceq 'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_FAILED_CHECK_BROKER_AND_LOGS'){
  return 'EXPLICIT_UI_FAILURE'
 }
 return 'UNRECOGNIZED_UI_RESULT'
}
if($OfflineSelfTest){
 Need ((Get-UiOutcome @('NO11_UNIFIED_TRADE_LAUNCHED_PID=123',
      'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_BROWSER_REQUESTED')) -ceq
      'NATIVE_UI_OPEN_REQUESTED') 'SELFTEST_NATIVE'
 Need ((Get-UiOutcome @('NO11_UNIFIED_TRADE_LAUNCHED_PID=123',
      'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_FAILED_CHECK_BROKER_AND_LOGS')) -ceq
      'EXPLICIT_UI_FAILURE') 'SELFTEST_FAILURE'
 Need ((Get-UiOutcome @('NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_FAILED_CHECK_BROKER_AND_LOGS')) -ceq
      'NO_CONFIRMED_TRADE_REQUEST') 'SELFTEST_NO_TRADE'
 Need ((Get-UiOutcome @('NO11_UNIFIED_TRADE_LAUNCHED_PID=123',
      'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_BROWSER_REQUESTED',
      'NO11_UNIFIED_UI2_LIVE=LIVE_ONLY_UI_FAILED_CHECK_BROKER_AND_LOGS')) -ceq
      'AMBIGUOUS_UI_RESULT') 'SELFTEST_AMBIGUOUS'
 Write-Host 'NO11_ONECLICK_UI2_WATCH_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try {
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $logDir=Join-Path $store 'oneclick-logs'
 $day=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 Need ([IO.Path]::IsPathRooted($NativeLog)) 'LOG_ABSOLUTE_REQUIRED'
 $path=[IO.Path]::GetFullPath($NativeLog)
 Need ([IO.Path]::GetDirectoryName($path) -ieq [IO.Path]::GetFullPath($logDir)) 'LOG_PATH_SCOPE'
 Need ([IO.Path]::GetFileName($path) -cmatch ('^Trade-'+$day+'-[a-f0-9]{32}[.]log$')) 'LOG_DATE_OR_NAME'
 # Native launcher must complete its own explicit same-day approval, order
 # preflights and one-shot receipt before the UI is ever retried.
 $outcome='PENDING'
 $deadline=(Get-Date).AddSeconds(90)
 while((Get-Date) -lt $deadline){
  $lines=@()
  if(Test-Path -LiteralPath $path -PathType Leaf){
   $lines=@(Get-Content -LiteralPath $path -Encoding UTF8 -ErrorAction SilentlyContinue)
  }
  $outcome=Get-UiOutcome $lines
  if($outcome -in @('NATIVE_UI_OPEN_REQUESTED','EXPLICIT_UI_FAILURE',
                  'AMBIGUOUS_UI_RESULT','UNRECOGNIZED_UI_RESULT')){break}
  Start-Sleep -Milliseconds 750
 }
 if($outcome -eq 'NATIVE_UI_OPEN_REQUESTED'){
  Write-Host 'NO11_ONECLICK_UI2_AUTOOPEN=NATIVE_BROWSER_REQUESTED'
  Write-Host 'UI_RETRY_COUNT=0'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 if($outcome -ne 'EXPLICIT_UI_FAILURE'){
  Write-Host ('NO11_ONECLICK_UI2_AUTOOPEN=BLOCKED|'+$outcome)
  Write-Host 'UI_RETRY_COUNT=0'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 2
 }
 # Only a read-only display retry. The original Trade is NEVER retried.
 $tradeReceipt=Join-Path $store ('TRADE-'+$day+'.launch.json')
 Need (Test-Path -LiteralPath $tradeReceipt -PathType Leaf) 'TRADE_RECEIPT_MISSING'
 $record=Get-Content -LiteralPath $tradeReceipt -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($record.kind -ceq 'TRADE' -and $record.asOfDate -ceq $day) 'TRADE_RECEIPT_NOT_SAME_DAY'
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
 $settings=Get-Content -LiteralPath (Join-Path $store 'settings.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.orderTransmission -eq $false -and
       $settings.sameDayApprovalRequired -eq $true) 'SETTINGS_UNSAFE'
 $helper=Join-Path ([string]$binding.engine) 'windows\Start-No11LiveUiReadOnly.ps1'
 $config=[string]$settings.bootstrapConfigFile
 Need ([IO.Path]::IsPathRooted($helper) -and
       [IO.Path]::IsPathRooted($config) -and
       (Test-Path -LiteralPath $helper -PathType Leaf) -and
       (Test-Path -LiteralPath $config -PathType Leaf)) 'READONLY_UI_HELPER_MISSING'
 Need (([DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')) -ceq $day) 'SESSION_DATE_CHANGED'
 # Native helper verifies actual-session broker identity and can only start
 # a loopback read-only browser. No approval flag or order command is passed.
 $uiLines=@(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -ConfigFile $config)
 $code=$LASTEXITCODE
 if($code -eq 0 -and
    $uiLines -contains 'NO11_UI2_LIVE_ONLY=LOCAL_BROWSER_OPEN_REQUESTED'){
  Write-Host 'NO11_ONECLICK_UI2_AUTOOPEN=READONLY_RETRY_BROWSER_REQUESTED'
  Write-Host 'UI_RETRY_COUNT=1'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Write-Host 'NO11_ONECLICK_UI2_AUTOOPEN=BLOCKED|READONLY_UI_RETRY_FAILED'
 Write-Host 'UI_RETRY_COUNT=1'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}catch {
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_ONECLICK_UI2_[A-Z0-9_]+$'){
  $reason='NO11_ONECLICK_UI2_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_ONECLICK_UI2_AUTOOPEN=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
