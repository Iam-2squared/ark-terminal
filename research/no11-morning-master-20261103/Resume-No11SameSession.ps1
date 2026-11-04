# OneClick SAME-DAY continuation of a stopped LIVE Chart50 collector.
# Invoked only after operator confirms the actual account, orders and holdings.
# Reuses the *original* Trade marker, broker database and ResumeRun path.
# NEVER replays or auto-resends a prior order.
param(
 [switch]$Apply,
 [switch]$IConfirmSameDayBrokerOrdersAndPositions,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_ONECLICK_RESUME_'+$reason)}
}
function Quote([string]$p){
 Need ([IO.Path]::IsPathRooted($p) -and -not $p.Contains('"') -and
       -not $p.Contains([char]10) -and -not $p.Contains([char]13)) 'ARG_UNSAFE'
 return '"'+[IO.Path]::GetFullPath($p)+'"'
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $IConfirmSameDayBrokerOrdersAndPositions) 'SELFTEST_FLAGS'
 Write-Host 'NO11_ONECLICK_RESUME_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_RESENT=False'
 Write-Host 'ORIGINAL_LEDGER_REPLACED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'APPLY_EXPLICITLY_REQUIRED'
Need $IConfirmSameDayBrokerOrdersAndPositions.IsPresent 'MANUAL_BROKER_CONFIRMATION_REQUIRED'
$day=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
$clock=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('HH:mm:ss')
Need ($clock -ge '09:00:00' -and $clock -lt '15:20:00') 'RECOVERY_WITHIN_ENTRY_WINDOW'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settingsFile=Join-Path $store 'settings.json'
$bindingFile=Join-Path $store 'automatic-inputs.json'
$settings=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
      $settings.sameDayApprovalRequired -eq $true -and
      $settings.automaticOrderAuthorization -eq $false -and
      $settings.orderTransmission -eq $false -and
      $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
$bootstrap=[string]$settings.bootstrapConfigFile
$engine=[string]$binding.engine
$python=[string]$binding.python
foreach($p in @($bootstrap,$engine,$python)){
 Need ([IO.Path]::IsPathRooted($p) -and (Test-Path -LiteralPath $p)) 'RUNTIME_PATH_MISSING'
}
$cfg=Get-Content -LiteralPath $bootstrap -Raw -Encoding UTF8|ConvertFrom-Json
Need ($cfg.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
      $cfg.sessionDate -ceq $day -and $cfg.orderTransmission -eq $false -and
      $cfg.productionReady -eq $false -and
      [IO.Path]::IsPathRooted([string]$cfg.privateRoot)) 'LIVE_SESSION_INVALID'
$root=[IO.Path]::GetFullPath([string]$cfg.privateRoot)
$pointer=Join-Path $root ('received-session-'+$day+'.active.json')
Need (Test-Path -LiteralPath $pointer -PathType Leaf) 'NO_OLD_LIVE_SESSION'
$active=Get-Content -LiteralPath $pointer -Raw -Encoding UTF8|ConvertFrom-Json
$run=[string]$active.runRoot
Need ($active.schemaId -ceq 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1' -and
      $active.sessionDate -ceq $day -and
      [IO.Path]::IsPathRooted($run) -and
      [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($run)) -ieq $root -and
      [IO.Path]::GetFileName($run) -cmatch ('^session-'+$day+'-[a-f0-9]{32}$')) 'RUN_ROOT_UNVERIFIED'
$activeProcesses=@(Get-CimInstance Win32_Process|Where-Object{
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
 [string]$_.CommandLine -match 'Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
})
Need ($activeProcesses.Count -eq 0) 'OLD_LIVE_STILL_RUNNING'
$native=Join-Path $engine 'windows\Run-No11ReceivedSessionOperatorLive.ps1'
$observer=Join-Path $engine 'windows\Observe-No11AccountReadOnly.ps1'
$closeTool=Join-Path $PSScriptRoot 'Close-No11OwnedC50Temporary.ps1'
$finalizer=Join-Path $PSScriptRoot 'no11_finalize_owned_collector_cleanup.py'
$rearmTool=Join-Path $PSScriptRoot 'no11_same_session_rearm.py'
foreach($p in @($native,$observer,$closeTool,$finalizer,$rearmTool)){
 Need (Test-Path -LiteralPath $p -PathType Leaf) 'RESUME_COMPONENT_MISSING'
}
$attempts=@(Get-ChildItem -LiteralPath $run -Directory -Filter 'attempt-*'|Sort-Object Name)
Need ($attempts.Count -ge 1 -and $attempts.Count -le 16) 'ATTEMPTS_MISSING'
$attemptPath=$attempts[-1].FullName
$attempt=Get-Content -LiteralPath (Join-Path $attemptPath 'attempt.json') -Raw -Encoding UTF8|ConvertFrom-Json
if($attempt.status -ceq 'CONNECTED'){
 # Fail-closed until the uniquely tokened ARK-owned unsaved workbook is
 # closed and the original failure ack is preserved alongside new proof.
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $closeTool -Bootstrap $bootstrap -RunRoot $run -Python $python -Finalizer $finalizer -Apply
 Need ($LASTEXITCODE -eq 0) 'OWNED_TEMP_CLEANUP_INCOMPLETE'
}elseif($attempt.status -cne 'CLOSED'){
 throw 'NO11_ONECLICK_RESUME_COLLECTOR_NOT_SAFELY_CLOSED'
}
# Fresh broker observation happens AFTER any workbook cleanup, once only.
$id=[guid]::NewGuid().ToString('N')
$observation=Join-Path $root ('oneclick-reconnect-'+$day+'-'+$id+'.json')
$stop=Join-Path $root ('oneclick-reconnect-'+$day+'-'+$id+'.stop')
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $observer -WorkbookPath ([string]$settings.accountWorkbookPath) -OrderIdWorkbookPath ([string]$settings.orderIdWorkbookPath) -OutputFile $observation -StopFile $stop -Samples 1 | Out-Null
Need ($LASTEXITCODE -eq 0 -and
      (Test-Path -LiteralPath $observation -PathType Leaf)) 'BROKER_OBSERVATION_FAILED'
# Separate read-only preview and comparison, then immutable ledger proof &
# source-only CAS rearm. Never delete/rewrite the original ledger/start marker.
$arguments=@('--engine',$engine,'--bootstrap',$bootstrap,
             '--observation',$observation,'--launcher-store',$store,
             '--run',$run,'--manual-confirmed')
$preflight=@(& $python -B -X utf8 $rearmTool @arguments)
Need ($LASTEXITCODE -eq 0 -and $preflight.Count -eq 1) 'BROKER_COMPARISON_NOT_ELIGIBLE'
$review=$preflight[0]|ConvertFrom-Json
Need ($review.schemaId -ceq 'ARK_NO11_SAME_RUN_SOURCE_REARM_V1' -and
      $review.status -ceq 'READ_ONLY_ELIGIBLE' -and
      $review.orderResent -eq $false -and
      $review.tradeRelaunched -eq $false) 'PREVIEW_REJECTED'
$applyResult=@(& $python -B -X utf8 $rearmTool @arguments --apply)
Need ($LASTEXITCODE -eq 0 -and $applyResult.Count -eq 1) 'REARM_NOT_COMMITTED'
$applied=$applyResult[0]|ConvertFrom-Json
Need ($applied.schemaId -ceq 'ARK_NO11_SAME_RUN_SOURCE_REARM_V1' -and
      $applied.status -ceq 'SOURCE_HALT_REARMED_FOR_NATIVE_RESUME' -and
      $applied.orderResent -eq $false -and
      $applied.entryHaltClearedAfterReconciliation -eq $true) 'REARM_RESULT_INVALID'
$launchMarker=Join-Path $store ('RESUME-'+$day+'-'+$id+'.launch.json')
$body=[ordered]@{
 schemaId='ARK_NO11_SAME_RUN_NATIVE_RESUME_LAUNCH_V1'
 sessionDate=$day
 runRoot=$run
 operatorConfirmed=$true
 previousTradeAuthorizationReused=$true
 issuedAtJst=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
 sameRunOnly=$true
 orderResendAllowed=$false
}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $body -Compress)+[char]10)
$f=[IO.File]::Open($launchMarker,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
# The original LIVE script's ResumeRun reuses all frozen policy, original
# account observer, existing broker config, and SAME inference DB.
$arguments=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
             (Quote $native),'-ConfigFile',(Quote $bootstrap),
             '-AccountWorkbookPath',(Quote ([string]$settings.accountWorkbookPath)),
             '-OrderIdWorkbookPath',(Quote ([string]$settings.orderIdWorkbookPath)),
             '-ResumeRun',(Quote $run),'-IApproveFullArkLiveOrdersForThisSession')
$logDir=Join-Path $store 'oneclick-logs'
[void][IO.Directory]::CreateDirectory($logDir)
$log=Join-Path $logDir ('Resume-'+$day+'-'+$id+'.log')
$err=Join-Path $logDir ('Resume-'+$day+'-'+$id+'.err')
$process=Start-Process -FilePath 'powershell.exe' -ArgumentList ($arguments -join ' ') -WorkingDirectory (Split-Path $native -Parent) -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
Need ($null -ne $process -and $process.Id -gt 0) 'NATIVE_RESUME_NOT_STARTED'
Write-Host 'NO11_ONECLICK_SAME_RUN_RESUME=REQUESTED'
Write-Host ('NATIVE_RESUME_PID='+$process.Id)
Write-Host ('NATIVE_RESUME_LOG='+$log)
Write-Host 'SAME_PREVIOUS_LEDGER_AND_ORDER_IDS=True'
Write-Host 'OLD_TRADE_START_MARKER_PRESERVED=True'
Write-Host 'ORIGINAL_COLLECTOR_RECEIPTS_MODIFIED=False'
Write-Host 'PREVIOUS_ORDER_RESENT=False'
Write-Host 'NATIVE_RESUME_REQUEST_IS_NOT_BROKER_ACK=True'
