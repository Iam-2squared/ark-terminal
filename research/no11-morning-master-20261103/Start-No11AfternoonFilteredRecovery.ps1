# 2026-11-05 only. Explicitly ARM one 12:30 JST recovery of the 09:00
# blocked/UNSENT Trade. Never send orders at ARM or before the afternoon open.
# The ORIGINAL native broker/Excel/session/strategy gates still control Trade.
param(
 [ValidateSet('Arm','Run')][string]$Mode='Arm',
 [switch]$UseTodayApprovedStandby,
 [string]$Nonce='',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_AFTERNOON_'+$why)}
}
function NowJst{return [DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9))}
function ArmWindow([DateTimeOffset]$t){
 return $t.ToString('yyyy-MM-dd') -ceq '2026-11-05' -and
        $t.ToString('HH:mm:ss') -ge '11:00:00' -and
        $t.ToString('HH:mm:ss') -lt '12:30:00'
}
function LaunchWindow([DateTimeOffset]$t){
 return $t.ToString('yyyy-MM-dd') -ceq '2026-11-05' -and
        $t.ToString('HH:mm:ss') -ge '12:30:00' -and
        $t.ToString('HH:mm:ss') -lt '12:35:00'
}
function Quote([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and
       -not $path.Contains([char]13) -and
       -not $path.Contains([char]10)) 'UNSAFE_PATH'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
function Blob([string]$file){
 $raw=[IO.File]::ReadAllBytes($file)
 $text=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $text=$text.Replace(([string][char]13+[char]10),[string][char]10)
 $body=[Text.Encoding]::UTF8.GetBytes($text)
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$body.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$body.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($body,0,$all,$header.Length,$body.Length)
 $digest=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($digest.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$digest.Dispose()}
}
function NoNativeProcesses{
 $busy=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Recover-No11FilteredMorning[.]ps1'
 })
 Need ($busy.Count -eq 0) 'EXISTING_LIVE_OR_ORDER_PROCESS'
}
if($OfflineSelfTest){
 Need (-not $UseTodayApprovedStandby -and [string]::IsNullOrEmpty($Nonce)) 'SELFTEST_FLAGS'
 Need (-not (ArmWindow ([DateTimeOffset]::Parse('2026-11-05T10:59:59+09:00')))) 'TEST_BEFORE_1100'
 Need (ArmWindow ([DateTimeOffset]::Parse('2026-11-05T11:00:00+09:00'))) 'TEST_ARM_1100'
 Need (ArmWindow ([DateTimeOffset]::Parse('2026-11-05T12:29:59+09:00'))) 'TEST_ARM_1229'
 Need (-not (ArmWindow ([DateTimeOffset]::Parse('2026-11-05T12:30:00+09:00')))) 'TEST_ARM_1230'
 Need (-not (LaunchWindow ([DateTimeOffset]::Parse('2026-11-05T12:29:59+09:00')))) 'TEST_NO_TRADE_BEFORE_1230'
 Need (LaunchWindow ([DateTimeOffset]::Parse('2026-11-05T12:30:00+09:00'))) 'TEST_1230'
 Need (LaunchWindow ([DateTimeOffset]::Parse('2026-11-05T12:34:59+09:00'))) 'TEST_1234'
 Need (-not (LaunchWindow ([DateTimeOffset]::Parse('2026-11-05T12:35:00+09:00')))) 'TEST_EXPIRE'
 Need (-not (LaunchWindow ([DateTimeOffset]::Parse('2026-11-06T12:30:00+09:00')))) 'TEST_NO_FUTURE_DAY'
 Write-Host 'NO11_AFTERNOON_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 $now=NowJst
 $day='2026-11-05'
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 Need (Test-Path -LiteralPath $store -PathType Container) 'ONECLICK_INSTALL_REQUIRED'
 $settingsPath=Join-Path $store 'settings.json'
 $bindingPath=Join-Path $store 'automatic-inputs.json'
 $reserve=Join-Path $store ('PREOPEN-'+$day+'.request.json')
 $preclaim=Join-Path $store ('PREOPEN-'+$day+'.execution-claimed')
 $tradeMarker=Join-Path $store ('TRADE-'+$day+'.launch.json')
 $oldRetryClaim=Join-Path $store ('MORNING-FILTERED-RETRY-'+$day+'.claim.json')
 $afternoon=Join-Path $store ('AFTERNOON-'+$day+'.request.json')
 $attempt=Join-Path $store ('AFTERNOON-'+$day+'.execution-claimed')
 $helper=Join-Path $PSScriptRoot 'Recover-No11FilteredMorning.ps1'
 foreach($f in @($settingsPath,$bindingPath,$reserve,$preclaim,$helper)){
  Need (Test-Path -LiteralPath $f -PathType Leaf) 'ORIGINAL_APPROVAL_OR_HELPER_MISSING'
 }
 Need ((Blob $helper) -ceq 'a05315c6840fce75c70f96e36d1c7d6a073cc6e6') 'FILTERED_RETRY_HELPER_NOT_PATCHED'
 Need (-not (Test-Path -LiteralPath $tradeMarker) -and
       -not (Test-Path -LiteralPath $oldRetryClaim)) 'TRADE_OR_OLD_RETRY_ALREADY_CLAIMED'
 $r=Get-Content -LiteralPath $reserve -Raw -Encoding UTF8|ConvertFrom-Json
 $claimed=(Get-Content -LiteralPath $preclaim -Raw -Encoding UTF8).Trim()
 Need ($r.schemaId -ceq 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1' -and
       $r.sessionDate -ceq $day -and
       $r.sameDayExplicitOrderApproval -eq $true -and
       [string]$r.nonce -cmatch '^[a-f0-9]{32}$' -and
       $claimed -ceq ('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|'+$day+'|'+[string]$r.nonce)) 'PREOPEN_APPROVAL_OR_CLAIM_MISMATCH'
 $settings=Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8|ConvertFrom-Json
 $binding=Get-Content -LiteralPath $bindingPath -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false -and
       $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
 foreach($name in @('automatic','bridge')){
  $file=[string]$binding.$name
  $pin=[string]$binding.($name+'Sha256')
  Need ([IO.Path]::IsPathRooted($file) -and (Test-Path -LiteralPath $file -PathType Leaf) -and
        (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $pin) 'CODE_BINDING_CHANGED'
 }
 $dailyRoot=[string]$binding.dailyCycleRoot
 Need ([IO.Path]::IsPathRooted($dailyRoot) -and
       (Test-Path -LiteralPath $dailyRoot -PathType Container)) 'DAILY_ROOT'
 $pointer=Join-Path $dailyRoot ('prepared-days\'+$day+'.json')
 Need (Test-Path -LiteralPath $pointer -PathType Leaf) 'TODAY_HANDOFF_MISSING'
 Need ((Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$r.pointerSha256) '0830_APPROVED_POINTER_CHANGED'
 $log=Join-Path $store ('oneclick-logs\Trade-'+$day+'-'+[string]$r.nonce+'.log')
 Need (Test-Path -LiteralPath $log -PathType Leaf) 'ORIGINAL_TRADE_FAILURE_LOG_MISSING'
 $text=[IO.File]::ReadAllText($log)
 foreach($expected in @('AUTOMATIC_INPUTS=DATA_UNAVAILABLE_OR_INCONSISTENT',
                         'BLOCKED_SYMBOL_COUNT=2','ORDER_SENT_BY_BRIDGE=False',
                         'ORDER_TRANSMISSION=False','TRADE_LAUNCHED=False')){
  Need ($text.Contains($expected)) 'PREVIOUS_FAILED_BEFORE_ORDER_UNVERIFIED'
 }
 NoNativeProcesses
 if($Mode -eq 'Arm'){
  Need $UseTodayApprovedStandby.IsPresent 'OPERATOR_ARM_REQUIRED'
  Need (ArmWindow $now) 'ARM_ONLY_1100_TO_1230'
  Need (-not (Test-Path -LiteralPath $afternoon) -and
       -not (Test-Path -LiteralPath $attempt)) 'AFTERNOON_ALREADY_RESERVED'
  $newNonce=[guid]::NewGuid().ToString('N')
  $sourceHash=(Get-FileHash -LiteralPath $helper -Algorithm SHA256).Hash.ToLowerInvariant()
  $runnerHash=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $record=[ordered]@{
   schemaId='ARK_NO11_AFTERNOON_1230_FILTERED_RETRY_V1'
   sessionDate=$day
   standbyNonce=[string]$r.nonce
   nonce=$newNonce
   requestedAtJst=$now.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
   earliestTradeStartJst=($day+'T12:30:00+09:00')
   expiresAtJst=($day+'T12:35:00+09:00')
   sameDayEarlierApprovalReused=$true
   approvedPointerSha256=[string]$r.pointerSha256
   helperSha256=$sourceHash
   runnerSha256=$runnerHash
   blockedSymbols=@('3003.T','7616.T')
   orderTransmission=$false
   tradeLaunchedAtArm=$false
  }
  $data=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $record -Depth 6 -Compress)+[char]10)
  $file=[IO.File]::Open($afternoon,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$file.Write($data,0,$data.Length);$file.Flush($true)}finally{$file.Dispose()}
  $logs=Join-Path $store 'oneclick-logs'
  [void][IO.Directory]::CreateDirectory($logs)
  $stdout=Join-Path $logs ('Afternoon-'+$day+'-'+$newNonce+'.log')
  $stderr=Join-Path $logs ('Afternoon-'+$day+'-'+$newNonce+'.err')
  $cmd=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
         '-File',(Quote $PSCommandPath),'-Mode','Run','-Nonce',$newNonce)
  $proc=Start-Process -FilePath 'powershell.exe' -ArgumentList ($cmd -join ' ') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  Need ($null -ne $proc -and $proc.Id -gt 0) 'AFTERNOON_WORKER_NOT_STARTED'
  Write-Host 'NO11_AFTERNOON_1230=ARMED'
  Write-Host ('SESSION='+$day)
  Write-Host ('WORKER_PID='+$proc.Id)
  Write-Host 'LAUNCH_WINDOW_JST=12:30-12:34'
  Write-Host 'PC_MUST_STAY_AWAKE=True'
  Write-Host 'WHITE_ONECLICK_CHANGED=False'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need (-not $UseTodayApprovedStandby) 'RUN_APPROVAL_FROM_SAVED_RECORD_ONLY'
 Need ([string]$Nonce -cmatch '^[a-f0-9]{32}$') 'NONCE_INVALID'
 Need (Test-Path -LiteralPath $afternoon -PathType Leaf) 'AFTERNOON_REQUEST_NOT_FOUND'
 $armed=Get-Content -LiteralPath $afternoon -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($armed.schemaId -ceq 'ARK_NO11_AFTERNOON_1230_FILTERED_RETRY_V1' -and
       $armed.sessionDate -ceq $day -and
       $armed.nonce -ceq $Nonce -and
       $armed.standbyNonce -ceq $r.nonce -and
       $armed.sameDayEarlierApprovalReused -eq $true -and
       $armed.earliestTradeStartJst -ceq ($day+'T12:30:00+09:00') -and
       $armed.expiresAtJst -ceq ($day+'T12:35:00+09:00') -and
       $armed.approvedPointerSha256 -ceq $r.pointerSha256 -and
       $armed.orderTransmission -eq $false -and
       $armed.tradeLaunchedAtArm -eq $false) 'AFTERNOON_REQUEST_INVALID'
 $issued=[DateTimeOffset]::Parse([string]$armed.requestedAtJst)
 Need (ArmWindow $issued) 'APPROVAL_TIME_INVALID'
 Need ((Get-FileHash -LiteralPath $helper -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$armed.helperSha256 -and
       (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$armed.runnerSha256) 'SOURCES_CHANGED_AFTER_ARM'
 while((NowJst).ToString('yyyy-MM-dd') -ceq $day -and
       (NowJst).ToString('HH:mm:ss') -lt '12:30:00'){
  Start-Sleep -Milliseconds 500
 }
 $launch=NowJst
 Need (LaunchWindow $launch) 'AUTO_LAUNCH_WINDOW_MISSED'
 $file=[IO.File]::Open($attempt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{
  $bytes=[Text.UTF8Encoding]::new($false).GetBytes(('AFTERNOON_SINGLE_REQUEST_CLAIMED|'+$day+'|'+$Nonce)+[char]10)
  $file.Write($bytes,0,$bytes.Length);$file.Flush($true)
 }finally{$file.Dispose()}
 Need (-not (Test-Path -LiteralPath $tradeMarker) -and
       -not (Test-Path -LiteralPath $oldRetryClaim)) 'TRADE_ALREADY_ATTEMPTED'
 Need ((Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$armed.approvedPointerSha256 -and
       (Get-FileHash -LiteralPath $helper -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$armed.helperSha256 -and
       (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$armed.runnerSha256) 'HANDOFF_OR_CODE_CHANGED_AT_1230'
 NoNativeProcesses
 # Only the original guarded retry may create a TRADE request. Never retry
 # it automatically, even if this process dies after the claim.
 $output=@(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -UseTodayApprovedStandby)
 $code=$LASTEXITCODE
 foreach($line in $output){Write-Host $line}
 Need ($code -eq 0 -and $output -contains 'NO11_MORNING_FILTERED_RETRY=REQUESTED_ONCE') 'NATIVE_RETRY_NOT_CONFIRMED'
 Write-Host 'NO11_AFTERNOON_1230=NATIVE_TRADE_REQUESTED_ONCE'
 Write-Host 'NATIVE_REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True'
 Write-Host 'AFTERNOON_AUTO_RETRIES=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_AFTERNOON_[A-Z0-9_]+$'){
  $reason='NO11_AFTERNOON_SOURCE_OR_RUNTIME_UNVERIFIED'
 }
 Write-Host ('NO11_AFTERNOON_1230=BLOCKED|'+$reason)
 Write-Host 'AFTERNOON_AUTO_RETRIES=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
