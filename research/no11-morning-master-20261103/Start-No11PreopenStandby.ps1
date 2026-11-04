# ARK No.1.1 — operator-approved 08:30-08:59 JST standby.
# Exactly one same-day native Trade request at >=09:00 JST; never a broker
# order at 08:30, never a retry of Trade, never a marker/ledger reset.
param(
 [ValidateSet('Arm','Run')][string]$Mode='Arm',
 [switch]$IApproveOrdersForToday,
 [string]$Nonce='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_PREOPEN_'+$why)}
}
function Clock { return [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)) }
function IsArmWindow([DateTimeOffset]$t){
 return ($t.DayOfWeek -notin @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday) -and
         $t.ToString('HH:mm:ss') -ge '08:30:00' -and
         $t.ToString('HH:mm:ss') -lt '09:00:00')
}
function IsLaunchWindow([DateTimeOffset]$t){
 return ($t.DayOfWeek -notin @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday) -and
         $t.ToString('HH:mm:ss') -ge '09:00:00' -and
         $t.ToString('HH:mm:ss') -lt '09:02:00')
}
function Quote([string]$v){
 Need ([IO.Path]::IsPathRooted($v) -and
       -not $v.Contains('"') -and -not $v.Contains([char]10) -and
       -not $v.Contains([char]13)) 'UNSAFE_PATH'
 return '"'+[IO.Path]::GetFullPath($v)+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday -and [string]::IsNullOrEmpty($Nonce)) 'SELFTEST_FLAGS'
 Need (-not (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:29:59+09:00')))) 'SELFTEST_BEFORE_0830'
 Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:30:00+09:00'))) 'SELFTEST_0830'
 Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:59:59+09:00'))) 'SELFTEST_0859'
 Need (-not (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T09:00:00+09:00')))) 'SELFTEST_ARM_AFTER9'
 Need (IsLaunchWindow ([DateTimeOffset]::Parse('2026-11-05T09:00:00+09:00'))) 'SELFTEST_0900'
 Need (IsLaunchWindow ([DateTimeOffset]::Parse('2026-11-05T09:01:59+09:00'))) 'SELFTEST_0901'
 Need (-not (IsLaunchWindow ([DateTimeOffset]::Parse('2026-11-05T09:02:00+09:00')))) 'SELFTEST_EXPIRY'
 Need (-not (IsArmWindow ([DateTimeOffset]::Parse('2026-11-07T08:30:00+09:00')))) 'SELFTEST_WEEKEND'
 Write-Host 'NO11_PREOPEN_OFFLINE_SELFTEST=PASS'
 Write-Host 'BEFORE_0900_ORDER_TRANSMISSION=False'
 Write-Host 'TRADE_LAUNCHED=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$files=Join-Path $store 'oneclick-logs'
$bindingFile=Join-Path $store 'automatic-inputs.json'
$settingsFile=Join-Path $store 'settings.json'
$statusTool=Join-Path $PSScriptRoot 'oneclick_status.py'
$watch=Join-Path $PSScriptRoot 'Watch-No11OneClickTradeUi.ps1'
$now=Clock
$day=$now.ToString('yyyy-MM-dd')
$queue=Join-Path $store ('PREOPEN-'+$day+'.request.json')
$claim=Join-Path $store ('PREOPEN-'+$day+'.execution-claimed')
$tradeMarker=Join-Path $store ('TRADE-'+$day+'.launch.json')
function GetStatus {
 Need ((Test-Path -LiteralPath $settingsFile -PathType Leaf) -and
       (Test-Path -LiteralPath $bindingFile -PathType Leaf) -and
       (Test-Path -LiteralPath $statusTool -PathType Leaf)) 'STATUS_DEPENDENCY'
 $binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
 $settings=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.normalMaxPositions -eq 3 -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
 $python=[string]$binding.python
 $native=Join-Path ([string]$binding.engine) 'windows\Start-No11UnifiedLauncher.ps1'
 Need ([IO.Path]::IsPathRooted($python) -and
       (Test-Path -LiteralPath $python -PathType Leaf) -and
       [IO.Path]::IsPathRooted($native) -and
       (Test-Path -LiteralPath $native -PathType Leaf)) 'NATIVE_RUNTIME_MISSING'
 $out=@(& $python -B -X utf8 $statusTool --settings $settingsFile --binding $bindingFile)
 Need ($LASTEXITCODE -eq 0 -and $out.Count -eq 1) 'STATUS_UNVERIFIED'
 $s=$out[0]|ConvertFrom-Json
 Need ($s.schemaId -ceq 'ARK_NO11_ONECLICK_STATUS_V1' -and
       $s.readOnly -eq $true -and
       $s.brokerOrderTransmission -eq $false -and
       $s.sessionDate -ceq $day) 'STATUS_SCOPE'
 return [pscustomobject]@{State=$s;Binding=$binding;Native=$native}
}
try {
 Need (Test-Path -LiteralPath $store -PathType Container) 'LOCAL_INSTALL_REQUIRED'
 Need ($now.Offset -eq [TimeSpan]::FromHours(9)) 'JST_REQUIRED'
 if($Mode -eq 'Arm'){
  Need $IApproveOrdersForToday 'SAME_DAY_EXPLICIT_APPROVAL_REQUIRED'
  Need (IsArmWindow $now) 'ARM_WINDOW_0830_TO_0900_ONLY'
  Need (-not (Test-Path -LiteralPath $queue) -and
        -not (Test-Path -LiteralPath $claim) -and
        -not (Test-Path -LiteralPath $tradeMarker)) 'ALREADY_RESERVED_OR_STARTED'
  $state=GetStatus
  Need ($state.State.mode -ceq 'OUTSIDE_ENTRY_WINDOW' -and
        $state.State.reason -ceq 'NEW_ENTRY_WINDOW_CLOSED' -and
        $state.State.canRequestTrade -eq $false) 'HANDOFF_NOT_PREOPEN_READY'
  $root=[string]$state.Binding.dailyCycleRoot
  Need ([IO.Path]::IsPathRooted($root)) 'DAILY_ROOT_REQUIRED'
  $pointer=Join-Path $root ('prepared-days\'+$day+'.json')
  Need (Test-Path -LiteralPath $pointer -PathType Leaf) 'TODAY_POINTER_MISSING'
  $fingerprint=(Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash.ToLowerInvariant()
  $nativeHash=(Get-FileHash -LiteralPath $state.Native -Algorithm SHA256).Hash.ToLowerInvariant()
  $selfHash=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $id=[guid]::NewGuid().ToString('N')
  $body=[ordered]@{
   schemaId='ARK_NO11_PREOPEN_STANDBY_REQUEST_V1'
   sessionDate=$day
   requestedAtJst=$now.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
   earliestTradeStartJst=($day+'T09:00:00+09:00')
   expiresAtJst=($day+'T09:02:00+09:00')
   sameDayExplicitOrderApproval=$true
   nonce=$id
   pointerSha256=$fingerprint
   nativeLauncherSha256=$nativeHash
   standbyRunnerSha256=$selfHash
   tradeLaunchedAtArm=$false
   orderTransmissionAtArm=$false
  }
  $raw=[Text.UTF8Encoding]::new($false).GetBytes(
      (ConvertTo-Json -InputObject $body -Compress)+[char]10)
  $stream=[IO.File]::Open($queue,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($raw,0,$raw.Length);$stream.Flush($true)}
  finally{$stream.Dispose()}
  [void][IO.Directory]::CreateDirectory($files)
  $stdout=Join-Path $files ('Preopen-'+$day+'-'+$id+'.log')
  $stderr=Join-Path $files ('Preopen-'+$day+'-'+$id+'.err')
  $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
          (Quote $PSCommandPath),'-Mode','Run','-Nonce',$id)
  $worker=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  Need ($null -ne $worker -and $worker.Id -gt 0) 'WAITING_PROCESS_NOT_STARTED'
  Write-Host 'NO11_PREOPEN_STANDBY=ARMED'
  Write-Host ('PREOPEN_DATE='+$day)
  Write-Host ('WORKER_PID='+$worker.Id)
  Write-Host 'WAITING_UNTIL_JST=09:00'
  Write-Host 'PC_MUST_REMAIN_AWAKE=True'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need (-not $IApproveOrdersForToday) 'RUN_MUST_READ_SAVED_APPROVAL'
 Need ($Nonce -cmatch '^[a-f0-9]{32}$') 'NONCE_INVALID'
 Need (Test-Path -LiteralPath $queue -PathType Leaf) 'QUEUE_NOT_FOUND'
 $req=Get-Content -LiteralPath $queue -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($req.schemaId -ceq 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1' -and
       $req.sessionDate -ceq $day -and
       $req.nonce -ceq $Nonce -and
       $req.sameDayExplicitOrderApproval -eq $true -and
       $req.tradeLaunchedAtArm -eq $false -and
       $req.orderTransmissionAtArm -eq $false -and
       $req.earliestTradeStartJst -ceq ($day+'T09:00:00+09:00') -and
       $req.expiresAtJst -ceq ($day+'T09:02:00+09:00')) 'QUEUE_IDENTITY_INVALID'
 $requested=[DateTimeOffset]::Parse([string]$req.requestedAtJst)
 Need ($requested.ToString('yyyy-MM-dd') -ceq $day -and
       (IsArmWindow $requested)) 'QUEUED_APPROVAL_TIME_INVALID'
 Need ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$req.standbyRunnerSha256) 'STANDBY_CODE_CHANGED'
 while((Clock).ToString('yyyy-MM-dd') -ceq $day -and (Clock).ToString('HH:mm:ss') -lt '09:00:00'){
  Start-Sleep -Milliseconds 500
 }
 $launchClock=Clock
 Need ($launchClock.ToString('yyyy-MM-dd') -ceq $day -and
       (IsLaunchWindow $launchClock)) 'LAUNCH_WINDOW_EXPIRED'
 # Durable one-shot claim; a crash after claiming must NOT retry Trade.
 $claimed=[IO.File]::Open($claim,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(
     'PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|'+$day+'|'+$Nonce+[char]10)
  $claimed.Write($bytes,0,$bytes.Length);$claimed.Flush($true)
 }finally{$claimed.Dispose()}
 Need (-not (Test-Path -LiteralPath $tradeMarker)) 'TRADE_ALREADY_STARTED_NO_DUPLICATE'
 Need ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$req.standbyRunnerSha256) 'STANDBY_CODE_CHANGED'
 $current=GetStatus
 Need ($current.State.mode -ceq 'OPERATOR_CHECK' -and
       $current.State.reason -ceq 'PRELIMINARY_INPUTS_READY' -and
       $current.State.canRequestTrade -eq $true) '0900_PRECHECK_FAILED'
 $pointer=Join-Path ([string]$current.Binding.dailyCycleRoot) ('prepared-days\'+$day+'.json')
 Need ((Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$req.pointerSha256) 'HANDOFF_CHANGED_SINCE_APPROVAL'
 Need ((Get-FileHash -LiteralPath $current.Native -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$req.nativeLauncherSha256) 'NATIVE_CODE_CHANGED_SINCE_APPROVAL'
 # Invoke the ORIGINAL native Trade command ONCE. It repeats workbook, broker
 # permission, session-date, one-shot marker and broker readiness validation.
 [void][IO.Directory]::CreateDirectory($files)
 $nativeStdout=Join-Path $files ('Trade-'+$day+'-'+$Nonce+'.log')
 $nativeStderr=Join-Path $files ('Trade-'+$day+'-'+$Nonce+'.err')
 $nativeArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
               (Quote $current.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $native=Start-Process -FilePath 'powershell.exe' -ArgumentList ($nativeArgs -join ' ') -WorkingDirectory (Split-Path -Parent $current.Native) -PassThru -WindowStyle Hidden -RedirectStandardOutput $nativeStdout -RedirectStandardError $nativeStderr
 Need ($null -ne $native -and $native.Id -gt 0) 'NATIVE_PROCESS_NOT_STARTED'
 Write-Host 'NO11_PREOPEN_NATIVE_TRADE=REQUESTED_ONCE'
 Write-Host ('NO11_PREOPEN_NATIVE_PID='+$native.Id)
 Write-Host ('NO11_PREOPEN_NATIVE_LOG='+$nativeStdout)
 Write-Host 'NATIVE_LAUNCH_REQUEST_IS_NOT_ORDER_CONFIRMATION=True'
 if(Test-Path -LiteralPath $watch -PathType Leaf){
  try{
   $watchLog=Join-Path $files ('Ui2-'+$day+'-'+$Nonce+'.log')
   $watchErr=Join-Path $files ('Ui2-'+$day+'-'+$Nonce+'.err')
   $watchArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                (Quote $watch),'-NativeLog',(Quote $nativeStdout))
   [void](Start-Process -FilePath 'powershell.exe' -ArgumentList ($watchArgs -join ' ') -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $watchLog -RedirectStandardError $watchErr)
   Write-Host 'NO11_PREOPEN_UI2_MONITOR=STARTED_READ_ONLY'
  }catch {
   Write-Host 'NO11_PREOPEN_UI2_MONITOR=UNAVAILABLE_NO_TRADE_RETRY'
  }
 }
 if($native.WaitForExit(900000)){
  $native.Refresh()
  Write-Host ('NO11_PREOPEN_NATIVE_EXIT_CODE='+$native.ExitCode)
  $lines=@()
  if(Test-Path -LiteralPath $nativeStdout){
   $lines=@(Get-Content -LiteralPath $nativeStdout -Encoding UTF8 -ErrorAction SilentlyContinue)
  }
  if($native.ExitCode -eq 0 -and
     ($lines -contains 'NO11_UNIFIED_TRADEX=FROZEN_MAX3_ENGINE_REQUESTED')){
   Write-Host 'NO11_PREOPEN_RESULT=NATIVE_TRADE_REQUEST_CONFIRMED'
  }else{
   Write-Host 'NO11_PREOPEN_RESULT=BLOCKED_OR_FAILED_CHECK_NATIVE_LOG'
  }
 }else{
  Write-Host 'NO11_PREOPEN_RESULT=NATIVE_STATUS_PENDING_CHECK_LOG'
 }
 Write-Host 'PREOPEN_NEVER_RETRIES_TRADE=True'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_PREOPEN_[A-Z0-9_]+$'){
  $reason='NO11_PREOPEN_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_PREOPEN=BLOCKED|'+$reason)
 Write-Host 'TRADE_RETRY_ATTEMPTED=False'
 exit 2
}
