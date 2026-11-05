# OneClick: one manual same-session 2026-11-05 retry ONLY after proof that
# 09:00 and 12:30 requests both failed before any ARK native Trade/ORDER.
# No marker deletion; no replay of submitted orders; original native broker
# session, cash, source/Excel, MAX3, strategy and order checks still run.
param(
 [ValidateSet('Status','Trade')][string]$Mode='Status',
 [switch]$IApproveOrdersForToday,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_ONECLICK_RETRY_'+$why)}}
function Jst{[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))}
function NoExtraNativeProcess{
 $processes=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Recover-No11FilteredMorning[.]ps1|Start-No11AfternoonFilteredRecovery[.]ps1'
 })
 Need ($processes.Count -eq 0) 'EXISTING_TRADE_OR_ORDER_PROCESS'
}
function Quote([string]$path){
 Need ([IO.Path]::IsPathRooted($path) -and
       -not $path.Contains('"') -and -not $path.Contains([char]10) -and
       -not $path.Contains([char]13)) 'PATH_ARGUMENT'
 return '"'+[IO.Path]::GetFullPath($path)+'"'
}
function Has([string]$body,[string]$token){
 return @($body.Split([char]10)|ForEach-Object{$_.Trim()}|Where-Object{$_ -ceq $token}).Count -eq 1
}
function ProvePreorderFailure{
 $clock=Jst
 $day='2026-11-05'
 Need ($clock.ToString('yyyy-MM-dd') -ceq $day -and
       $clock.ToString('HH:mm:ss') -ge '12:35:00' -and
       $clock.ToString('HH:mm:ss') -lt '15:20:00') 'ONLY_TODAY_AFTER_FAILED_1230_ATTEMPT'
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $dayFiles=@(
  ('PREOPEN-'+$day+'.request.json'),
  ('PREOPEN-'+$day+'.execution-claimed'),
  ('AFTERNOON-'+$day+'.request.json'),
  ('AFTERNOON-'+$day+'.execution-claimed'),
  ('MORNING-FILTERED-RETRY-'+$day+'.claim.json'),
  'settings.json','automatic-inputs.json'
 )
 foreach($n in $dayFiles){Need (Test-Path -LiteralPath (Join-Path $store $n) -PathType Leaf) 'PREORDER_EVIDENCE_MISSING'}
 foreach($n in @(
  ('TRADE-'+$day+'.launch.json'),
  ('ONECLICK-RETRY-'+$day+'.claim.json')
 )){
  Need (-not (Test-Path -LiteralPath (Join-Path $store $n))) 'TRADE_OR_MANUAL_RETRY_ALREADY_CLAIMED'
 }
 $request=Get-Content -LiteralPath (Join-Path $store $dayFiles[0]) -Raw -Encoding UTF8|ConvertFrom-Json
 $preClaim=(Get-Content -LiteralPath (Join-Path $store $dayFiles[1]) -Raw -Encoding UTF8).Trim()
 Need ($request.schemaId -ceq 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1' -and
       $request.sessionDate -ceq $day -and
       $request.sameDayExplicitOrderApproval -eq $true -and
       $request.orderTransmissionAtArm -eq $false -and
       $request.tradeLaunchedAtArm -eq $false -and
       [string]$request.nonce -cmatch '^[a-f0-9]{32}$' -and
       $preClaim -ceq ('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|'+$day+'|'+[string]$request.nonce)) 'ORIGINAL_APPROVAL_UNVERIFIED'
 $arm=Get-Content -LiteralPath (Join-Path $store $dayFiles[2]) -Raw -Encoding UTF8|ConvertFrom-Json
 $claim=(Get-Content -LiteralPath (Join-Path $store $dayFiles[3]) -Raw -Encoding UTF8).Trim()
 Need ($arm.schemaId -ceq 'ARK_NO11_AFTERNOON_1230_FILTERED_RETRY_V1' -and
       $arm.sessionDate -ceq $day -and
       $arm.standbyNonce -ceq $request.nonce -and
       $arm.sameDayEarlierApprovalReused -eq $true -and
       $arm.approvedPointerSha256 -ceq $request.pointerSha256 -and
       $arm.orderTransmission -eq $false -and
       $arm.tradeLaunchedAtArm -eq $false -and
       [string]$arm.nonce -cmatch '^[a-f0-9]{32}$' -and
       $claim -ceq ('AFTERNOON_SINGLE_REQUEST_CLAIMED|'+$day+'|'+[string]$arm.nonce)) 'AFTERNOON_APPROVAL_UNVERIFIED'
 $oldRetry=Get-Content -LiteralPath (Join-Path $store $dayFiles[4]) -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($oldRetry.schemaId -ceq 'ARK_NO11_SAME_DAY_PREORDER_FILTERED_RETRY_V1' -and
       $oldRetry.sessionDate -ceq $day -and
       $oldRetry.originalRequestNonce -ceq $request.nonce -and
       $oldRetry.previousAttemptProvenNoOrder -eq $true -and
       $oldRetry.humanRetryActionApproved -eq $true -and
       $oldRetry.orderTransmission -eq $false -and
       [int]$oldRetry.selectedPassed -eq 39 -and
       (@($oldRetry.blockedSymbols)|Sort-Object) -join ',' -ceq '3003.T,7616.T') 'FAILED_AFTERNOON_RETRY_ORIGIN_UNVERIFIED'
 $logs=Join-Path $store 'oneclick-logs'
 $morning=Join-Path $logs ('Trade-'+$day+'-'+[string]$request.nonce+'.log')
 $after=Join-Path $logs ('Afternoon-'+$day+'-'+[string]$arm.nonce+'.log')
 $retry=Join-Path $logs ('MorningFilteredRetry-'+$day+'.log')
 foreach($file in @($morning,$after,$retry)){
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'PREORDER_FAILURE_LOG_MISSING'
  Need ((Get-Item -LiteralPath $file).Length -gt 30 -and (Get-Item -LiteralPath $file).Length -lt 200000) 'PREORDER_LOG_SIZE'
 }
 $early=[IO.File]::ReadAllText($morning)
 $afternoon=[IO.File]::ReadAllText($after)
 $later=[IO.File]::ReadAllText($retry)
 foreach($token in @(
  'AUTOMATIC_INPUTS=DATA_UNAVAILABLE_OR_INCONSISTENT',
  'BLOCKED_SYMBOL_COUNT=2',
  'TRADE_LAUNCHED=False',
  'ORDER_TRANSMISSION=False',
  'ORDER_SENT_BY_BRIDGE=False',
  'NO11_UNIFIED=BLOCKED|NO11_UNIFIED_AUTOMATIC_INPUTS_OR_INITIAL_BROKER_CONNECTION_INCOMPLETE'
 )){Need (Has $early $token) '0900_PREORDER_FAILURE_NOT_PROVEN'}
 foreach($token in @(
  'NO11_MORNING_FILTERED_RETRY=REQUESTED_ONCE',
  'NO11_AFTERNOON_1230=NATIVE_TRADE_REQUESTED_ONCE',
  'NATIVE_REQUEST_IS_NOT_BROKER_ORDER_CONFIRMATION=True',
  'AFTERNOON_AUTO_RETRIES=False'
 )){Need (Has $afternoon $token) 'AFTERNOON_CLAIM_LOG_NOT_PROVEN'}
 foreach($token in @(
  'NO11_SESSION_REFERENCE=BLOCKED|NO11_REFERENCE_EXCEL_COM_OR_SOURCE_FAILURE',
  'AUTOMATIC_LAUNCHER=BLOCKED|NO11_MORNING_REFERENCE_CAPTURE_FAILED',
  'ORDER_SENT_BY_BRIDGE=False',
  'NO11_UNIFIED=BLOCKED|NO11_UNIFIED_AUTOMATIC_INPUTS_OR_INITIAL_BROKER_CONNECTION_INCOMPLETE',
  'NO11_UNIFIED_AUTOMATIC_ORDER_APPROVAL=False'
 )){Need (Has $later $token) '1230_PREORDER_FAILURE_NOT_PROVEN'}
 foreach($data in @($early,$afternoon,$later)){
  Need ($data -notmatch '(?m)^NO11_UNIFIED_TRADE_LAUNCHED_PID=|^NO11_UNIFIED_TRADEX=|^ORDER_SENT=(?!False)' ) 'POSSIBLE_LIVE_ORDER_REQUEST'
 }
 $settings=Get-Content -LiteralPath (Join-Path $store 'settings.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
       $settings.normalMaxPositions -eq 3 -and
       $settings.sameDayApprovalRequired -eq $true -and
       $settings.automaticOrderAuthorization -eq $false -and
       $settings.orderTransmission -eq $false -and
       $binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'ACCOUNT_AND_RUNTIME_SETTINGS_CHANGED'
 $root=[string]$binding.dailyCycleRoot
 Need ([IO.Path]::IsPathRooted($root) -and (Test-Path -LiteralPath $root -PathType Container)) 'DAILY_CYCLE_ROOT'
 $pointer=Join-Path $root ('prepared-days\'+$day+'.json')
 Need (Test-Path -LiteralPath $pointer -PathType Leaf) 'DAILY_CYCLE_POINTER_MISSING'
 Need ((Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$request.pointerSha256) '0830_APPROVED_HANDOFF_CHANGED'
 $p=Get-Content -LiteralPath $pointer -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($p.schemaId -ceq 'ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1' -and
       $p.sessionDate -ceq $day -and
       $p.orderTransmission -eq $false -and
       [int]$p.selectedCount -eq 41 -and
       [IO.Path]::IsPathRooted([string]$p.handoff) -and
       (Test-Path -LiteralPath ([string]$p.handoff) -PathType Leaf)) 'TODAY_HANDOFF_UNVERIFIED'
 Need ((Get-FileHash -LiteralPath ([string]$p.handoff) -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
       [string]$p.handoffSha256) 'TODAY_HANDOFF_HASH_CHANGED'
 foreach($part in @('automatic','bridge')){
  $path=[string]$binding.$part
  Need ([IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType Leaf) -and
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
        [string]$binding.($part+'Sha256')) 'AUTO_SOURCE_CHANGED'
 }
 $native=Join-Path ([string]$binding.engine) 'windows\Start-No11UnifiedLauncher.ps1'
 $reference=Join-Path ([string]$binding.engine) 'windows\Capture-No11SessionReferenceReadOnly.ps1'
 Need ((Test-Path -LiteralPath $native -PathType Leaf) -and
       (Test-Path -LiteralPath $reference -PathType Leaf)) 'NATIVE_LAUNCHER_OR_REFERENCE_MISSING'
 # The reference fix is installed and exact pinned, not merely downloaded.
 $captureHash=(& git hash-object --no-filters -- $reference).Trim()
 Need ($LASTEXITCODE -eq 0 -and
       $captureHash -ceq 'f1e9739ccfb8ac520a4484d00ffccc5471264763') 'RSS_REFERENCE_FIX_NOT_INSTALLED'
 NoExtraNativeProcess
 return @{Store=$store;Native=$native;Day=$day}
}
if($OfflineSelfTest){
 Need (-not $IApproveOrdersForToday) 'SELFTEST_FLAGS'
 Need (Has ("SAFE="+[char]10+"ORDER_SENT_BY_BRIDGE=False"+[char]10) 'ORDER_SENT_BY_BRIDGE=False') 'TEST_EXACT_LINE'
 Need (-not (Has ("ORDER_SENT_BY_BRIDGE=False_EXTRA"+[char]10) 'ORDER_SENT_BY_BRIDGE=False')) 'TEST_LINE_FALSE_PASS'
 Write-Host 'NO11_ONECLICK_RETRY_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 if($Mode -eq 'Status'){
  Need (-not $IApproveOrdersForToday) 'STATUS_MUST_BE_READONLY'
  [void](ProvePreorderFailure)
  Write-Host 'NO11_ONECLICK_RETRY_STATUS=READY'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need $IApproveOrdersForToday.IsPresent 'NEW_EXPLICIT_SAME_DAY_ORDER_APPROVAL_REQUIRED'
 $checked=ProvePreorderFailure
 $store=$checked.Store
 $day=$checked.Day
 $claimPath=Join-Path $store ('ONECLICK-RETRY-'+$day+'.claim.json')
 $clock=Jst
 $request=[ordered]@{
  schemaId='ARK_NO11_ONECLICK_VERIFIED_PREORDER_RETRY_V1'
  sessionDate=$day
  explicitlyReapprovedAtJst=$clock.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  originalAttempts=2
  excludedSymbols=@('3003.T','7616.T')
  plannedVerifiedScope=39
  earlierAttemptsBlockedBeforeTrade=$true
  oldBrokerOrdersResent=$false
  manualSameDayOneShot=$true
  orderTransmission=$false
 }
 $data=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $request -Depth 8 -Compress)+[char]10)
 $file=[IO.File]::Open($claimPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$file.Write($data,0,$data.Length);$file.Flush($true)}finally{$file.Dispose()}
 # Original native runner will again independently verify live source,
 # Excel/RSS, cash, broker session, max3, one-shot trade and strategy gates.
 Need (-not (Test-Path -LiteralPath (Join-Path $store ('TRADE-'+$day+'.launch.json')))) 'NATIVE_MARKER_CREATED_CONCURRENTLY'
 NoExtraNativeProcess
 $folder=Join-Path $store 'oneclick-logs'
 [void][IO.Directory]::CreateDirectory($folder)
 $out=Join-Path $folder ('OneClickRetry-'+$day+'.log')
 $err=Join-Path $folder ('OneClickRetry-'+$day+'.err')
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
         (Quote $checked.Native),'-Mode','Trade','-IApproveOrdersForToday')
 $child=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory (Split-Path -Parent $checked.Native) -WindowStyle Hidden -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
 Need ($null -ne $child -and $child.Id -gt 0) 'NATIVE_PROCESS_NOT_STARTED'
 Write-Host 'NO11_ONECLICK_RETRY=REQUESTED_ONCE'
 Write-Host ('LIVE_REQUEST_PID='+$child.Id)
 Write-Host ('LIVE_LOG='+$out)
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'MARKERS_DELETED=False'
 Write-Host 'THIS_IS_NOT_ORDER_OR_FILL_CONFIRMATION=True'
 exit 0
}catch{
 $msg=[string]$_.Exception.Message
 if($msg -cnotmatch '^NO11_ONECLICK_RETRY_[A-Z0-9_]+$'){$msg='NO11_ONECLICK_RETRY_SOURCE_OR_RUNTIME_UNVERIFIED'}
 if($Mode -eq 'Status'){
  Write-Host ('NO11_ONECLICK_RETRY_STATUS=BLOCKED|'+$msg)
 }else{
  Write-Host ('NO11_ONECLICK_RETRY=BLOCKED|'+$msg)
 }
 Write-Host 'TRADE_RETRY_SENT=False'
 exit 2
}
