# User-facing OneClick recovery review, never a LIVE resume or order permission.
# Independent account observation plus original same-day recovery auditor in read-only mode.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_ONECLICK_REVIEW_'+$code)}}
if($OfflineSelfTest){
 Write-Host 'NO11_ONECLICK_REVIEW_OFFLINE_SELFTEST=PASS'
 Write-Host 'AUTO_RECOVERY_OR_TRADE=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$day=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd')
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settings=Get-Content -LiteralPath (Join-Path $store 'settings.json') -Raw -Encoding UTF8|ConvertFrom-Json
$binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
Need ($settings.sameDayApprovalRequired -eq $true -and $settings.orderTransmission -eq $false -and
      $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1') 'CONFIG_UNSAFE'
$bootstrap=[string]$settings.bootstrapConfigFile
$boot=Get-Content -LiteralPath $bootstrap -Raw -Encoding UTF8|ConvertFrom-Json
Need ($boot.sessionDate -ceq $day -and $boot.orderTransmission -eq $false) 'NOT_CURRENT_DAY'
$root=[string]$boot.privateRoot
Need ([IO.Path]::IsPathRooted($root) -and (Test-Path -LiteralPath $root -PathType Container)) 'PRIVATE_ROOT_MISSING'
$engine=[string]$binding.engine
$observer=Join-Path $engine 'windows\Observe-No11AccountReadOnly.ps1'
$helper=Join-Path $PSScriptRoot 'no11_same_day_reconcile.py'
$python=[string]$binding.python
foreach($p in @($observer,$helper,$python)){
 Need ([IO.Path]::IsPathRooted($p) -and (Test-Path -LiteralPath $p -PathType Leaf)) 'AUDIT_RUNTIME_NOT_INSTALLED'
}
$active=@(Get-CimInstance Win32_Process | Where-Object {
 $_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh|python|pythonw)(\.exe)?$' -and
 [string]$_.CommandLine -match 'Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
})
Need ($active.Count -eq 0) 'ARK_STILL_RUNNING'
$id=[guid]::NewGuid().ToString('N')
$file=Join-Path $root ('oneclick-recovery-review-'+$id+'.json')
$stop=Join-Path $root ('oneclick-recovery-review-'+$id+'.stop')
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $observer -WorkbookPath ([string]$settings.accountWorkbookPath) -OrderIdWorkbookPath ([string]$settings.orderIdWorkbookPath) -OutputFile $file -StopFile $stop -Samples 1 | Out-Null
Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $file -PathType Leaf)) 'BROKER_OBSERVATION_FAILED'
$observation=Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
Need ($observation.status -ceq 'OBSERVED' -and $observation.brokerObservation.status -ceq 'OBSERVED' -and
      $observation.brokerObservation.completeTables -eq $true -and
      $observation.brokerObservation.sameSnapshotVerified -eq $true) 'BROKER_NOT_FULLY_OBSERVED'
$envBefore=[Environment]::GetEnvironmentVariable('ARK_NO11_ENGINE_PATH','Process')
try{
 [Environment]::SetEnvironmentVariable('ARK_NO11_ENGINE_PATH',$engine,'Process')
 $result=@(& $python -B -X utf8 $helper --session $day --bootstrap $bootstrap --observation $file --launcher-store $store)
 $code=$LASTEXITCODE
 $allowed=@('RECOVERY_REVIEW=','LEDGER_ORDERS=','LEDGER_COMMANDS=','LEDGER_POSITIONS=','FRESH_BROKER_ORDERS=','OLD_HALT_REASONS=','TRADING_LEDGER_EVENTS_UNCHANGED=','ORDER_TRANSMISSION=')
 foreach($line in $result){
  if($null -eq $line){continue}
  foreach($prefix in $allowed){
   if(([string]$line).StartsWith($prefix)){Write-Host ([string]$line);break}
  }
 }
 Write-Host ('NO11_ONECLICK_REVIEW_EXIT_CODE='+$code)
 if($code -ne 0){
  # ARK_NO11_ONEPASS_NONZERO_MANUAL_RECONNECT_REVIEW_V1
  # Reuse the SAME freshly captured broker snapshot rather than making the
  # operator repeat the original broker check. This is audit-only, never rearm.
  $compare=Join-Path $PSScriptRoot 'no11_manual_reconnect_review.py'
  $pointerFile=Join-Path $root ('received-session-'+$day+'.active.json')
  if((Test-Path -LiteralPath $compare -PathType Leaf) -and
     (Test-Path -LiteralPath $pointerFile -PathType Leaf)){
   $pointer=Get-Content -LiteralPath $pointerFile -Raw -Encoding UTF8|ConvertFrom-Json
   $run=[string]$pointer.runRoot
   if($pointer.schemaId -ceq 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1' -and
      $pointer.sessionDate -ceq $day -and
      [IO.Path]::IsPathRooted($run) -and
      [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($run)) -ieq [IO.Path]::GetFullPath($root)){
    $db=Join-Path $run ('inference\broker-execution-'+$day+'.sqlite')
    if(Test-Path -LiteralPath $db -PathType Leaf){
     $assessment=@(& $python -B -X utf8 $compare --session $day --ledger-db $db --observation $file --engine $engine)
     $reviewCode=$LASTEXITCODE
     if($reviewCode -eq 0 -and $assessment.Count -eq 1){
      $resultObj=$assessment[0]|ConvertFrom-Json
      Need ($resultObj.schemaId -ceq 'ARK_NO11_MANUAL_RECONNECT_REVIEW_V1' -and
            $resultObj.newBuyAuthorized -eq $false -and
            $resultObj.haltMarkerCleared -eq $false -and
            $resultObj.orderResendAllowed -eq $false) 'RECONNECT_REVIEW_UNSAFE'
      Write-Host ('NO11_ONECLICK_MANUAL_RECONNECT_REVIEW='+$resultObj.state)
      Write-Host ('NO11_ONECLICK_MATCHED_ORDERS='+$resultObj.matchedOrders)
      Write-Host ('NO11_ONECLICK_MATCHED_ARK_POSITIONS='+$resultObj.matchedArkPositions)
      Write-Host 'REQUIRES_MANUAL_CONFIRMATION_AND_RESTART_SUPERVISOR=True'
      Write-Host 'ENTRY_HALT_MARKER_MODIFIED=False'
      Write-Host 'ORDER_RESENT=False'
      $code=0
     }
    }
   }
  }
 }
 Need ($code -eq 0) 'AUDITOR_REJECTED'
}finally{
 [Environment]::SetEnvironmentVariable('ARK_NO11_ENGINE_PATH',$envBefore,'Process')
}
Write-Host 'RECOVERY_APPLIED=False'
Write-Host 'TRADE_LAUNCHED=False'
Write-Host 'ORDER_TRANSMISSION=False'
