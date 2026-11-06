# One voluntary, strictly fail-closed 2026-11-06 afternoon retry, only after
# an unsuccessful PREOPEN request that failed before native LIVE/order.
# NEVER clear morning claims or existing broker/order/EXIT state.
# Status probes broker read-only; Request requires fresh explicit approval.
param(
 [ValidateSet('Status','Request')][string]$Mode='Status',
 [switch]$IApproveOrdersForToday,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_NOV06_AFTERNOON_'+$code)}}
function NowJst{[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9))}
function HasLine([string]$text,[string]$line){
 return @($text.Split([char]10)|ForEach-Object{$_.Trim()}|Where-Object{$_ -ceq $line}).Count -eq 1
}
function HashFile([string]$file){
 return (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
function ReadJson([string]$file){
 Need ([IO.Path]::IsPathRooted($file) -and (Test-Path -LiteralPath $file -PathType Leaf)) 'REQUIRED_SOURCE_MISSING'
 return (Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json)
}
function NoNativeProcess {
 $busy=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher[.]ps1|Run-No11ReceivedSessionOperatorLive[.]ps1|no11_received_session_controller[.]py|Invoke-No11MsiiOrder[.]ps1|Start-No11PreopenStandby[.]ps1|Request-No11Nov06AfternoonPreorder[.]ps1'
 })
 # Exclude this script's own invocation, but never another live/recovery worker.
 # Do not exempt any competing request process: exactly one manual attempt.
 Need ($busy.Count -eq 0) 'OTHER_LIVE_OR_PREOPEN_PROCESS_ACTIVE'
}
function SessionEvidence{
 $clock=NowJst
 $day='2026-11-06'
 Need ($clock.ToString('yyyy-MM-dd') -ceq $day) 'EXACT_DATE_REQUIRED'
 if($Mode -eq 'Request'){
  Need ($clock.ToString('HH:mm:ss') -ge '12:30:00' -and $clock.ToString('HH:mm:ss') -lt '15:20:00') 'AFTERNOON_ENTRY_WINDOW'
 }else{
  Need ($clock.ToString('HH:mm:ss') -ge '11:30:00' -and $clock.ToString('HH:mm:ss') -lt '15:20:00') 'STATUS_WINDOW'
 }
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $reserve=Join-Path $store ('PREOPEN-'+$day+'.request.json')
 $claim=Join-Path $store ('PREOPEN-'+$day+'.execution-claimed')
 $settings=ReadJson (Join-Path $store 'settings.json')
 $binding=ReadJson (Join-Path $store 'automatic-inputs.json')
 $r=ReadJson $reserve
 Need ((Test-Path -LiteralPath $claim -PathType Leaf) -and
       $r.schemaId -ceq 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1' -and
       $r.sessionDate -ceq $day -and
       $r.sameDayExplicitOrderApproval -eq $true -and
       $r.orderTransmissionAtArm -eq $false -and
       $r.tradeLaunchedAtArm -eq $false -and
       [string]$r.nonce -cmatch '^[a-f0-9]{32}$') 'MORNING_APPROVAL_UNVERIFIED'
 $claimed=(Get-Content -LiteralPath $claim -Raw -Encoding UTF8).Trim()
 Need ($claimed -ceq ('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|'+$day+'|'+[string]$r.nonce)) 'MORNING_SINGLE_USE_CLAIM_INVALID'
 foreach($filename in @(
  ('TRADE-'+$day+'.launch.json'),
  ('ONECLICK-RETRY-'+$day+'.claim.json'),
  ('AFTERNOON-'+$day+'.request.json'),
  ('AFTERNOON-'+$day+'.execution-claimed'),
  ('MORNING-FILTERED-RETRY-'+$day+'.claim.json'),
  ('AFTERNOON-MANUAL-'+$day+'.claimed')
  )){
  Need (-not (Test-Path -LiteralPath (Join-Path $store $filename))) 'TRADE_OR_RETRY_ALREADY_CLAIMED'
 }
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false -and
       $settings.normalMaxPositions -eq 3 -and
       $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'SETTINGS_CHANGED'
 foreach($source in @('bridge','automatic','runner','transportProbe')){
  $path=[string]$binding.$source
  $pin=[string]$binding.($source+'Sha256')
  Need ([IO.Path]::IsPathRooted($path) -and
       (Test-Path -LiteralPath $path -PathType Leaf) -and
       (HashFile $path) -ceq $pin) 'PINNED_CODE_CHANGED'
 }
 $pointerPath=Join-Path ([string]$binding.dailyCycleRoot) ('prepared-days\'+$day+'.json')
 Need ((HashFile $pointerPath) -ceq [string]$r.pointerSha256) 'PREOPEN_SOURCE_CHANGED'
 $pointer=ReadJson $pointerPath
 Need ($pointer.schemaId -ceq 'ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1' -and
       $pointer.sessionDate -ceq $day -and
       $pointer.orderTransmission -eq $false -and
       [int]$pointer.selectedCount -eq 45 -and
       (HashFile ([string]$pointer.handoff)) -ceq [string]$pointer.handoffSha256) 'MORNING_HANDOFF_CHANGED'
 $logs=Join-Path $store 'oneclick-logs'
 $pre=Join-Path $logs ('Preopen-'+$day+'-'+[string]$r.nonce+'.log')
 $tradeLog=Join-Path $logs ('Trade-'+$day+'-'+[string]$r.nonce+'.log')
 foreach($file in @($pre,$tradeLog)){
  Need ((Test-Path -LiteralPath $file -PathType Leaf) -and
        (Get-Item -LiteralPath $file).Length -gt 30 -and
        (Get-Item -LiteralPath $file).Length -le 200000) 'ORIGINAL_LOG_MISSING_OR_TRUNCATED'
 }
 $preText=[IO.File]::ReadAllText($pre)
 $trade=[IO.File]::ReadAllText($tradeLog)
 foreach($line in @(
  'NO11_PREOPEN_NATIVE_TRADE=REQUESTED_ONCE',
  'NO11_PREOPEN_RESULT=BLOCKED_OR_FAILED_CHECK_NATIVE_LOG',
  'PREOPEN_NEVER_RETRIES_TRADE=True'
 )){Need (HasLine $preText $line) 'MORNING_PREOPEN_FAILURE_NOT_PROVEN'}
 foreach($line in @(
  'AUTOMATIC_FILTER_PASS_COUNT=40',
  'AUTOMATIC_FILTER_EXCLUDED_COUNT=5',
  'AUTOMATIC_INPUTS=COMPLETE_NOT_LIVE_STARTED',
  'TRADE_LAUNCHED=False',
  'ORDER_TRANSMISSION=False',
  'ORDER_TRIGGER_WRITTEN_TO_ONE=False',
  'ORDER_SENT=False',
  'ORDER_SENT_BY_BRIDGE=False',
  'AUTOMATIC_LAUNCHER=BLOCKED|NO11_AUTOSTART_PHYSICAL_TRANSPORT_SETUP_FAILED',
  'NO11_UNIFIED=BLOCKED|NO11_UNIFIED_AUTOMATIC_INPUTS_OR_INITIAL_BROKER_CONNECTION_INCOMPLETE'
 )){Need (HasLine $trade $line) '0900_PREORDER_FAILURE_NOT_PROVEN'}
 Need ($trade -notmatch '(?m)^NO11_UNIFIED_TRADE_LAUNCHED_PID=|^NO11_UNIFIED_TRADEX=|^AUTOSTART_LIVE_BOOTSTRAP=|^ORDER_SENT=(?!False$)' -and
       $preText -notmatch '(?m)^NO11_PREOPEN_RESULT=NATIVE_TRADE_REQUEST_CONFIRMED') 'POSSIBLE_NATIVE_LIVE_OR_ORDER'
 $preparedPtr=ReadJson (Join-Path $store ('prepared-inputs-'+$day+'.json'))
 Need ($preparedPtr.schemaId -ceq 'ARK_NO11_AUTOMATIC_READY_INPUT_POINTER_V1' -and
       $preparedPtr.sessionDate -ceq $day -and $preparedPtr.orderTransmission -eq $false) 'MORNING_PREPARED_POINTER'
 $bootPath=[string]$preparedPtr.bootstrap
 $boot=ReadJson $bootPath
 Need ($boot.sessionDate -ceq $day -and $boot.orderTransmission -eq $false -and
       (HasLine $trade ('MORNING_PREPARED_BOOTSTRAP='+$bootPath))) 'MORNING_40_SOURCE_CHANGED'
 $native=Join-Path ([string]$binding.engine) 'windows\Start-No11UnifiedLauncher.ps1'
 $observer=Join-Path ([string]$binding.engine) 'windows\Observe-No11AccountReadOnly.ps1'
 Need ((Test-Path -LiteralPath $native -PathType Leaf) -and
       (Test-Path -LiteralPath $observer -PathType Leaf)) 'NATIVE_OR_BROKER_OBSERVER_MISSING'
 $root=[string]$boot.privateRoot
 Need ([IO.Path]::IsPathRooted($root) -and (Test-Path -LiteralPath $root -PathType Container)) 'PRIVATE_ROOT'
 Need (-not (Test-Path -LiteralPath (Join-Path $root ('received-session-'+$day+'.active.json')))) 'EXISTING_LIVE_SESSION'
 NoNativeProcess
 return @{Store=$store;Day=$day;Native=$native;Observer=$observer;Settings=$settings;Bootstrap=$boot;PreLog=$pre;TradeLog=$tradeLog}
}
function DoubleReadBroker($c){
 # A failed/incomplete/unavailable table is NEVER interpreted as zero orders.
 $reviews=@()
 for($n=1;$n -le 2;$n++){
  $path=Join-Path ([string]$c.Bootstrap.privateRoot) ('no11-afternoon-preflight-'+[guid]::NewGuid().ToString('N')+'.json')
  $stop=$path+'.stop'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $c.Observer -WorkbookPath ([string]$c.Settings.accountWorkbookPath) -OrderIdWorkbookPath ([string]$c.Settings.orderIdWorkbookPath) -OutputFile $path -StopFile $stop -Samples 1 | Out-Null
  Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $path -PathType Leaf)) 'BROKER_OBSERVATION_PROCESS_FAILED'
  $x=ReadJson $path
  $b=$x.brokerObservation
  Need ($x.status -ceq 'OBSERVED' -and $x.readOnly -eq $true -and
        $x.orderTransmission -eq $false -and
        $b.status -ceq 'OBSERVED' -and $b.completeTables -eq $true -and
        $b.sameSnapshotVerified -eq $true -and $b.rowsTruncated -eq $false) 'BROKER_NOT_FULLY_OBSERVED'
  Need (@($b.idRows).Count -eq 0 -and @($b.orders).Count -eq 0 -and @($b.executions).Count -eq 0 -and
        @($x.snapshot.orders).Count -eq 0 -and @($x.snapshot.executions).Count -eq 0) 'BROKER_HISTORY_NOT_PROVEN_EMPTY'
  $observedAt=[DateTimeOffset]::Parse([string]$b.captureCompletedAt)
  $age=((NowJst)-$observedAt).TotalSeconds
  Need ($observedAt.Offset.TotalHours -eq 9 -and $age -ge 0 -and $age -le 60) 'BROKER_SNAPSHOT_NOT_FRESH'
  $reviews+=@($x)
 }
 $s1=[string]$reviews[0].brokerObservation.excelSession.sessionKey
 $s2=[string]$reviews[1].brokerObservation.excelSession.sessionKey
 Need ($s1 -cmatch '^[a-f0-9]{64}([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and -not $path.Contains([char]10) -and
       -not $path.Contains([char]13)) 'NATIVE_PATH'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday -and $Mode -eq 'Status') 'SELFTEST_FLAGS'
 Need (HasLine ("ONE"+[char]10+"TWO=False"+[char]10) 'TWO=False') 'HAS_LINE'
 Need (-not (HasLine ("TWO=False_EXTRA"+[char]10) 'TWO=False')) 'HAS_LINE_EXACT'
 Need (-not (([DateTimeOffset]::Parse('2026-11-06T12:29:59+09:00')).ToString('HH:mm:ss') -ge '12:30:00')) 'TIME_PREMARKET'
 Write-Host 'NO11_NOV06_AFTERNOON_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($Mode -eq 'Status' -or $IApproveOrdersForToday.IsPresent) 'EXPLICIT_ORDER_APPROVAL_REQUIRED'
 $c=SessionEvidence
 # Status is a source/marker audit only; never produces a live order.
 if($Mode -eq 'Status'){
  Write-Host 'NO11_NOV06_AFTERNOON_STATUS=PREORDER_EVIDENCE_VERIFIED'
  Write-Host 'FRESH_BROKER_DOUBLE_READ_REQUIRED_AT_REQUEST=True'
  Write-Host 'NO_NATIVE_TRADE_REQUEST=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 # The user explicitly agrees to a NEW manual same-day approval.
 # Check two independent read-only broker observations before creating a claim.
 $bro=DoubleReadBroker $c
 $clock=NowJst
 Need ($clock.ToString('yyyy-MM-dd') -ceq $c.Day -and
       $clock.ToString('HH:mm:ss') -ge '12:30:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'REQUEST_WINDOW_EXPIRED'
 $c=SessionEvidence
 $claimPath=Join-Path $c.Store ('AFTERNOON-MANUAL-'+$c.Day+'.claimed')
 $claim=[ordered]@{
  schemaId='ARK_NO11_NOV06_ONE_TIME_AFTERNOON_PREORDER_RETRY_V1'
  sessionDate=$c.Day
  explicitlyApprovedAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  originalPreopenLogSha256=(HashFile $c.PreLog)
  originalNativeFailureLogSha256=(HashFile $c.TradeLog)
  brokerDoubleReadComplete=$true
  brokerOrdersAndExecutions=0
  nativeTradeMarkerAbsent=$true
  previousOrdersResent=$false
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $claim -Compress -Depth 8)+[char]10)
 $handle=[IO.File]::Open($claimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}finally{$handle.Dispose()}
 # Claim is intentionally permanent even when Start-Process fails: no second dispatch.
 NoNativeProcess
 Need (-not (Test-Path -LiteralPath (Join-Path $c.Store ('TRADE-'+$c.Day+'.launch.json')))) 'TRADE_CREATED_CONCURRENTLY'
 $outDir=Join-Path $c.Store 'oneclick-logs'
 $log=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.log')
 $err=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.err')
 Need (-not (Test-Path -LiteralPath $log) -and -not (Test-Path -LiteralPath $err)) 'AFTERNOON_LOG_ALREADY_USED'
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $c.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $process=Start-Process -FilePath 'powershell.exe' -WorkingDirectory (Split-Path -Parent $c.Native) -ArgumentList ($args -join ' ') -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err
 Need ($null -ne $process -and $process.Id -gt 0) 'NATIVE_REQUEST_FAILED'
 Write-Host 'NO11_NOV06_AFTERNOON=REQUESTED_ONCE'
 Write-Host ('NATIVE_REQUEST_PID='+$process.Id)
 Write-Host ('NATIVE_LOG='+$log)
 Write-Host 'REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True'
 Write-Host 'EXISTING_MARKERS_DELETED=False'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'ORDER_SENT_BY_HELPER=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_NOV06_AFTERNOON_[A-Z0-9_]+$'){
  $reason='NO11_NOV06_AFTERNOON_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_NOV06_AFTERNOON_'+$(if($Mode -eq 'Status'){'STATUS'}else{'REQUEST'})+'=BLOCKED|'+$reason)
 Write-Host 'NO11_NOV06_AFTERNOON_ORDER_SENT_BY_HELPER=False'
 exit 2
}
 -and $s1 -ceq $s2) 'BROKER_EXCEL_SESSION_CHANGED'
 # No previous ARK run exists; any historical or current broker order blocks
 # this extraordinary recovery. The native launcher independently rechecks.
 return @{First=$reviews[0];Second=$reviews[1]}
}
function Quote([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and -not $path.Contains([char]10) -and
       -not $path.Contains([char]13)) 'NATIVE_PATH'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday -and $Mode -eq 'Status') 'SELFTEST_FLAGS'
 Need (HasLine ("ONE"+[char]10+"TWO=False"+[char]10) 'TWO=False') 'HAS_LINE'
 Need (-not (HasLine ("TWO=False_EXTRA"+[char]10) 'TWO=False')) 'HAS_LINE_EXACT'
 Need (-not (([DateTimeOffset]::Parse('2026-11-06T12:29:59+09:00')).ToString('HH:mm:ss') -ge '12:30:00')) 'TIME_PREMARKET'
 Write-Host 'NO11_NOV06_AFTERNOON_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($Mode -eq 'Status' -or $IApproveOrdersForToday.IsPresent) 'EXPLICIT_ORDER_APPROVAL_REQUIRED'
 $c=SessionEvidence
 # Status is a source/marker audit only; never produces a live order.
 if($Mode -eq 'Status'){
  Write-Host 'NO11_NOV06_AFTERNOON_STATUS=PREORDER_EVIDENCE_VERIFIED'
  Write-Host 'FRESH_BROKER_DOUBLE_READ_REQUIRED_AT_REQUEST=True'
  Write-Host 'NO_NATIVE_TRADE_REQUEST=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 # The user explicitly agrees to a NEW manual same-day approval.
 # Check two independent read-only broker observations before creating a claim.
 $bro=DoubleReadBroker $c
 $clock=NowJst
 Need ($clock.ToString('yyyy-MM-dd') -ceq $c.Day -and
       $clock.ToString('HH:mm:ss') -ge '12:30:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'REQUEST_WINDOW_EXPIRED'
 $c=SessionEvidence
 $claimPath=Join-Path $c.Store ('AFTERNOON-MANUAL-'+$c.Day+'.claimed')
 $claim=[ordered]@{
  schemaId='ARK_NO11_NOV06_ONE_TIME_AFTERNOON_PREORDER_RETRY_V1'
  sessionDate=$c.Day
  explicitlyApprovedAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  originalPreopenLogSha256=(HashFile $c.PreLog)
  originalNativeFailureLogSha256=(HashFile $c.TradeLog)
  brokerDoubleReadComplete=$true
  brokerOrdersAndExecutions=0
  nativeTradeMarkerAbsent=$true
  previousOrdersResent=$false
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $claim -Compress -Depth 8)+[char]10)
 $handle=[IO.File]::Open($claimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}finally{$handle.Dispose()}
 # Claim is intentionally permanent even when Start-Process fails: no second dispatch.
 NoNativeProcess
 Need (-not (Test-Path -LiteralPath (Join-Path $c.Store ('TRADE-'+$c.Day+'.launch.json')))) 'TRADE_CREATED_CONCURRENTLY'
 $outDir=Join-Path $c.Store 'oneclick-logs'
 $log=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.log')
 $err=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.err')
 Need (-not (Test-Path -LiteralPath $log) -and -not (Test-Path -LiteralPath $err)) 'AFTERNOON_LOG_ALREADY_USED'
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $c.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $process=Start-Process -FilePath 'powershell.exe' -WorkingDirectory (Split-Path -Parent $c.Native) -ArgumentList ($args -join ' ') -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err
 Need ($null -ne $process -and $process.Id -gt 0) 'NATIVE_REQUEST_FAILED'
 Write-Host 'NO11_NOV06_AFTERNOON=REQUESTED_ONCE'
 Write-Host ('NATIVE_REQUEST_PID='+$process.Id)
 Write-Host ('NATIVE_LOG='+$log)
 Write-Host 'REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True'
 Write-Host 'EXISTING_MARKERS_DELETED=False'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'ORDER_SENT_BY_HELPER=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_NOV06_AFTERNOON_[A-Z0-9_]+$'){
  $reason='NO11_NOV06_AFTERNOON_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_NOV06_AFTERNOON_'+$(if($Mode -eq 'Status'){'STATUS'}else{'REQUEST'})+'=BLOCKED|'+$reason)
 Write-Host 'NO11_NOV06_AFTERNOON_ORDER_SENT_BY_HELPER=False'
 exit 2
}
 -and $s1 -ceq $s2) 'BROKER_EXCEL_SESSION_CHANGED'
 # No previous ARK run exists; any historical or current broker order blocks
 # this extraordinary recovery. The native launcher independently rechecks.
 return @{First=$reviews[0];Second=$reviews[1]}
}
function Quote([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and -not $path.Contains([char]10) -and
       -not $path.Contains([char]13)) 'NATIVE_PATH'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday -and $Mode -eq 'Status') 'SELFTEST_FLAGS'
 Need (HasLine ("ONE"+[char]10+"TWO=False"+[char]10) 'TWO=False') 'HAS_LINE'
 Need (-not (HasLine ("TWO=False_EXTRA"+[char]10) 'TWO=False')) 'HAS_LINE_EXACT'
 Need (-not (([DateTimeOffset]::Parse('2026-11-06T12:29:59+09:00')).ToString('HH:mm:ss') -ge '12:30:00')) 'TIME_PREMARKET'
 Write-Host 'NO11_NOV06_AFTERNOON_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($Mode -eq 'Status' -or $IApproveOrdersForToday.IsPresent) 'EXPLICIT_ORDER_APPROVAL_REQUIRED'
 $c=SessionEvidence
 # Status is a source/marker audit only; never produces a live order.
 if($Mode -eq 'Status'){
  Write-Host 'NO11_NOV06_AFTERNOON_STATUS=PREORDER_EVIDENCE_VERIFIED'
  Write-Host 'FRESH_BROKER_DOUBLE_READ_REQUIRED_AT_REQUEST=True'
  Write-Host 'NO_NATIVE_TRADE_REQUEST=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 # The user explicitly agrees to a NEW manual same-day approval.
 # Check two independent read-only broker observations before creating a claim.
 $bro=DoubleReadBroker $c
 $clock=NowJst
 Need ($clock.ToString('yyyy-MM-dd') -ceq $c.Day -and
       $clock.ToString('HH:mm:ss') -ge '12:30:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'REQUEST_WINDOW_EXPIRED'
 $c=SessionEvidence
 $claimPath=Join-Path $c.Store ('AFTERNOON-MANUAL-'+$c.Day+'.claimed')
 $claim=[ordered]@{
  schemaId='ARK_NO11_NOV06_ONE_TIME_AFTERNOON_PREORDER_RETRY_V1'
  sessionDate=$c.Day
  explicitlyApprovedAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  originalPreopenLogSha256=(HashFile $c.PreLog)
  originalNativeFailureLogSha256=(HashFile $c.TradeLog)
  brokerDoubleReadComplete=$true
  brokerOrdersAndExecutions=0
  nativeTradeMarkerAbsent=$true
  previousOrdersResent=$false
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $claim -Compress -Depth 8)+[char]10)
 $handle=[IO.File]::Open($claimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}finally{$handle.Dispose()}
 # Claim is intentionally permanent even when Start-Process fails: no second dispatch.
 NoNativeProcess
 Need (-not (Test-Path -LiteralPath (Join-Path $c.Store ('TRADE-'+$c.Day+'.launch.json')))) 'TRADE_CREATED_CONCURRENTLY'
 $outDir=Join-Path $c.Store 'oneclick-logs'
 $log=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.log')
 $err=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.err')
 Need (-not (Test-Path -LiteralPath $log) -and -not (Test-Path -LiteralPath $err)) 'AFTERNOON_LOG_ALREADY_USED'
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $c.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $process=Start-Process -FilePath 'powershell.exe' -WorkingDirectory (Split-Path -Parent $c.Native) -ArgumentList ($args -join ' ') -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err
 Need ($null -ne $process -and $process.Id -gt 0) 'NATIVE_REQUEST_FAILED'
 Write-Host 'NO11_NOV06_AFTERNOON=REQUESTED_ONCE'
 Write-Host ('NATIVE_REQUEST_PID='+$process.Id)
 Write-Host ('NATIVE_LOG='+$log)
 Write-Host 'REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True'
 Write-Host 'EXISTING_MARKERS_DELETED=False'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'ORDER_SENT_BY_HELPER=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_NOV06_AFTERNOON_[A-Z0-9_]+$'){
  $reason='NO11_NOV06_AFTERNOON_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_NOV06_AFTERNOON_'+$(if($Mode -eq 'Status'){'STATUS'}else{'REQUEST'})+'=BLOCKED|'+$reason)
 Write-Host 'NO11_NOV06_AFTERNOON_ORDER_SENT_BY_HELPER=False'
 exit 2
}
 -and $s1 -ceq $s2) 'BROKER_EXCEL_SESSION_CHANGED'
 # No previous ARK run exists; any historical or current broker order blocks
 # this extraordinary recovery. The native launcher independently rechecks.
 return @{First=$reviews[0];Second=$reviews[1]}
}
function Quote([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and -not $path.Contains([char]10) -and
       -not $path.Contains([char]13)) 'NATIVE_PATH'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday -and $Mode -eq 'Status') 'SELFTEST_FLAGS'
 Need (HasLine ("ONE"+[char]10+"TWO=False"+[char]10) 'TWO=False') 'HAS_LINE'
 Need (-not (HasLine ("TWO=False_EXTRA"+[char]10) 'TWO=False')) 'HAS_LINE_EXACT'
 Need (-not (([DateTimeOffset]::Parse('2026-11-06T12:29:59+09:00')).ToString('HH:mm:ss') -ge '12:30:00')) 'TIME_PREMARKET'
 Write-Host 'NO11_NOV06_AFTERNOON_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($Mode -eq 'Status' -or $IApproveOrdersForToday.IsPresent) 'EXPLICIT_ORDER_APPROVAL_REQUIRED'
 $c=SessionEvidence
 # Status is a source/marker audit only; never produces a live order.
 if($Mode -eq 'Status'){
  Write-Host 'NO11_NOV06_AFTERNOON_STATUS=PREORDER_EVIDENCE_VERIFIED'
  Write-Host 'FRESH_BROKER_DOUBLE_READ_REQUIRED_AT_REQUEST=True'
  Write-Host 'NO_NATIVE_TRADE_REQUEST=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 # The user explicitly agrees to a NEW manual same-day approval.
 # Check two independent read-only broker observations before creating a claim.
 $bro=DoubleReadBroker $c
 $clock=NowJst
 Need ($clock.ToString('yyyy-MM-dd') -ceq $c.Day -and
       $clock.ToString('HH:mm:ss') -ge '12:30:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'REQUEST_WINDOW_EXPIRED'
 $c=SessionEvidence
 $claimPath=Join-Path $c.Store ('AFTERNOON-MANUAL-'+$c.Day+'.claimed')
 $claim=[ordered]@{
  schemaId='ARK_NO11_NOV06_ONE_TIME_AFTERNOON_PREORDER_RETRY_V1'
  sessionDate=$c.Day
  explicitlyApprovedAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  originalPreopenLogSha256=(HashFile $c.PreLog)
  originalNativeFailureLogSha256=(HashFile $c.TradeLog)
  brokerDoubleReadComplete=$true
  brokerOrdersAndExecutions=0
  nativeTradeMarkerAbsent=$true
  previousOrdersResent=$false
  orderTransmission=$false
 }
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $claim -Compress -Depth 8)+[char]10)
 $handle=[IO.File]::Open($claimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}finally{$handle.Dispose()}
 # Claim is intentionally permanent even when Start-Process fails: no second dispatch.
 NoNativeProcess
 Need (-not (Test-Path -LiteralPath (Join-Path $c.Store ('TRADE-'+$c.Day+'.launch.json')))) 'TRADE_CREATED_CONCURRENTLY'
 $outDir=Join-Path $c.Store 'oneclick-logs'
 $log=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.log')
 $err=Join-Path $outDir ('AfternoonManual-'+$c.Day+'.err')
 Need (-not (Test-Path -LiteralPath $log) -and -not (Test-Path -LiteralPath $err)) 'AFTERNOON_LOG_ALREADY_USED'
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $c.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $process=Start-Process -FilePath 'powershell.exe' -WorkingDirectory (Split-Path -Parent $c.Native) -ArgumentList ($args -join ' ') -PassThru -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err
 Need ($null -ne $process -and $process.Id -gt 0) 'NATIVE_REQUEST_FAILED'
 Write-Host 'NO11_NOV06_AFTERNOON=REQUESTED_ONCE'
 Write-Host ('NATIVE_REQUEST_PID='+$process.Id)
 Write-Host ('NATIVE_LOG='+$log)
 Write-Host 'REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True'
 Write-Host 'EXISTING_MARKERS_DELETED=False'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'ORDER_SENT_BY_HELPER=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_NOV06_AFTERNOON_[A-Z0-9_]+$'){
  $reason='NO11_NOV06_AFTERNOON_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_NOV06_AFTERNOON_'+$(if($Mode -eq 'Status'){'STATUS'}else{'REQUEST'})+'=BLOCKED|'+$reason)
 Write-Host 'NO11_NOV06_AFTERNOON_ORDER_SENT_BY_HELPER=False'
 exit 2
}
