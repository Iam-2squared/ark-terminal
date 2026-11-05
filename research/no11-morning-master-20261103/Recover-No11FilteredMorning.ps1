# One explicit same-day pre-order recovery for 2026-11-05 morning rejection.
# Does not delete PREOPEN / TRADE markers, approve a new day, patch source
# receipts, change the white UI, cancel or resend any old broker order.
param([switch]$UseTodayApprovedStandby,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_MORNING_RECOVERY_'+$reason)}
}
function Quote([string]$s){
 Need ([IO.Path]::IsPathRooted($s) -and
       -not $s.Contains('"') -and -not $s.Contains([char]10) -and
       -not $s.Contains([char]13)) 'UNSAFE_ARGUMENT'
 return '"'+[IO.Path]::GetFullPath($s)+'"'
}
if($OfflineSelfTest){
 Need (-not $UseTodayApprovedStandby) 'SELFTEST_FLAGS'
 Write-Host 'NO11_MORNING_RECOVERY_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXISTING_MARKERS_CLEARED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need $UseTodayApprovedStandby.IsPresent 'EXPLICIT_SAME_DAY_RECOVERY_ACTION_REQUIRED'
 $clock=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
 $day=$clock.ToString('yyyy-MM-dd')
 Need ($day -ceq '2026-11-05' -and
       $clock.ToString('HH:mm:ss') -ge '09:00:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'ONLY_20261105_LIVE_SESSION'
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $reservation=Join-Path $store ('PREOPEN-'+$day+'.request.json')
 $claim=Join-Path $store ('PREOPEN-'+$day+'.execution-claimed')
 $marker=Join-Path $store ('TRADE-'+$day+'.launch.json')
 $bindingPath=Join-Path $store 'automatic-inputs.json'
 $settingsPath=Join-Path $store 'settings.json'
 foreach($path in @($reservation,$claim,$bindingPath,$settingsPath)){
  Need (Test-Path -LiteralPath $path -PathType Leaf) 'SAVED_APPROVAL_OR_SETTINGS_MISSING'
 }
 Need (-not (Test-Path -LiteralPath $marker)) 'TRADE_MARKER_PRESENT_DO_NOT_RESTART'
 $r=Get-Content -LiteralPath $reservation -Raw -Encoding UTF8|ConvertFrom-Json
 $savedClaim=(Get-Content -LiteralPath $claim -Raw -Encoding UTF8).Trim()
 Need ($r.schemaId -ceq 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1' -and
       $r.sessionDate -ceq $day -and
       $r.sameDayExplicitOrderApproval -eq $true -and
       $r.tradeLaunchedAtArm -eq $false -and
       $r.orderTransmissionAtArm -eq $false -and
       [string]$r.nonce -cmatch '^[a-f0-9]{32}$' -and
       $savedClaim -ceq ('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|'+$day+'|'+[string]$r.nonce)) 'PREOPEN_APPROVAL_OR_CLAIM_NOT_VERIFIED'
 $tradeLog=Join-Path $store ('oneclick-logs\Trade-'+$day+'-'+[string]$r.nonce+'.log')
 Need (Test-Path -LiteralPath $tradeLog -PathType Leaf) 'ORIGINAL_FAILED_NATIVE_LOG_MISSING'
 $log=[IO.File]::ReadAllText($tradeLog)
 foreach($expected in @('AUTOMATIC_INPUTS=DATA_UNAVAILABLE_OR_INCONSISTENT',
                        'BLOCKED_SYMBOL_COUNT=2',
                        'TRADE_LAUNCHED=False','ORDER_TRANSMISSION=False',
                        'ORDER_SENT_BY_BRIDGE=False',
                        'NO11_UNIFIED=BLOCKED|NO11_UNIFIED_AUTOMATIC_INPUTS_OR_INITIAL_BROKER_CONNECTION_INCOMPLETE')){
  Need ($log.Contains($expected)) 'PREVIOUS_ATTEMPT_NOT_PROVEN_BEFORE_ORDER'
 }
 $reportLine=@($log.Split([char]10)|Where-Object{$_ -like 'AUTOMATIC_INPUT_REPORT=*'})
 Need ($reportLine.Count -eq 1) 'FAILED_SOURCE_REPORT_AMBIGUOUS'
 $reportFile=([string]$reportLine[0]).Trim().Substring('AUTOMATIC_INPUT_REPORT='.Length)
 Need ([IO.Path]::IsPathRooted($reportFile) -and
       (Test-Path -LiteralPath $reportFile -PathType Leaf)) 'SOURCE_REPORT_MISSING'
 $report=Get-Content -LiteralPath $reportFile -Raw -Encoding UTF8|ConvertFrom-Json
 $bad=@($report.blockedSymbols)
 Need ($report.schemaId -ceq 'ARK_NO11_AUTOMATIC_OPERATIONAL_INPUT_RESULT_V1' -and
       $report.sessionDate -ceq $day -and
       [int]$report.selectedCount -eq 41 -and
       [int]$report.passedCount -eq 39 -and
       $bad.Count -eq 2 -and
       @($bad|Where-Object{$_.reason -cne 'NO11_AUTO_INPUT_UNADJUSTED_PRICE_MISMATCH'}).Count -eq 0 -and
       @($bad|ForEach-Object{$_.symbol}|Sort-Object) -join ',' -ceq '3003.T,7616.T' -and
       $report.orderTransmission -eq $false) 'EXPECTED_TWO_PRICE_MISMATCHES_NOT_PROVEN'
 $settings=Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8|ConvertFrom-Json
 $binding=Get-Content -LiteralPath $bindingPath -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false -and
       $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.sessionDate -ceq $day -and
       $binding.orderTransmission -eq $false) 'INSTALLED_RUNTIME_UNSAFE'
 $bridgePath=[string]$binding.bridge
 $automaticPath=[string]$binding.automatic
 foreach($path in @($bridgePath,$automaticPath)){
  Need ([IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType Leaf)) 'AUTOMATIC_SOURCE_MISSING'
 }
 Need ((Get-FileHash -LiteralPath $bridgePath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$binding.bridgeSha256 -and
       (Get-FileHash -LiteralPath $automaticPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$binding.automaticSha256) 'PATCHED_SOURCE_NOT_PINNED'
 $native=Join-Path ([string]$binding.engine) 'windows\Start-No11UnifiedLauncher.ps1'
 Need (Test-Path -LiteralPath $native -PathType Leaf) 'NATIVE_LAUNCHER_MISSING'
 $active=@(Get-CimInstance Win32_Process | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($active.Count -eq 0) 'LIVE_PROCESS_OR_ORDER_DISPATCH_MAY_BE_RUNNING'
 $retryClaim=Join-Path $store ('MORNING-FILTERED-RETRY-'+$day+'.claim.json')
 $body=[ordered]@{
  schemaId='ARK_NO11_SAME_DAY_PREORDER_FILTERED_RETRY_V1'
  sessionDate=$day
  originalRequestNonce=[string]$r.nonce
  blockedSymbols=@('3003.T','7616.T')
  selectedPassed=39
  previousAttemptProvenNoOrder=$true
  humanRetryActionApproved=$true
  claimAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $body -Compress)+[char]10)
 $handle=[IO.File]::Open($retryClaim,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}
 finally{$handle.Dispose()}
 $logs=Join-Path $store 'oneclick-logs'
 [void][IO.Directory]::CreateDirectory($logs)
 $stdout=Join-Path $logs ('MorningFilteredRetry-'+$day+'.log')
 $stderr=Join-Path $logs ('MorningFilteredRetry-'+$day+'.err')
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
         (Quote $native),'-Mode','Trade','-IApproveOrdersForToday')
 $process=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory (Split-Path -Parent $native) -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 Need ($null -ne $process -and $process.Id -gt 0) 'RETRY_NOT_STARTED'
 Write-Host 'NO11_MORNING_FILTERED_RETRY=REQUESTED_ONCE'
 Write-Host 'PREVIOUS_SUCCESSFUL_SOURCE_SCOPE=39'
 Write-Host 'PREVIOUS_BLOCKED_SYMBOLS=3003.T,7616.T'
 Write-Host ('NATIVE_RETRY_PID='+$process.Id)
 Write-Host ('NATIVE_RETRY_LOG='+$stdout)
 Write-Host 'THIS_IS_NOT_BROKER_ORDER_ACK=True'
 Write-Host 'PREOPEN_AND_TRADE_MARKERS_DELETED=False'
 Write-Host 'OLD_ORDER_RESENT=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_MORNING_RECOVERY_[A-Z0-9_]+$'){
  $reason='NO11_MORNING_RECOVERY_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_MORNING_FILTERED_RETRY=BLOCKED|'+$reason)
 Write-Host 'MARKERS_CLEARED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
