# ARK No.1.1 OneClick desktop control.
# Never starts live trading on open; existing operator approval and broker gates stay intact.
param([ValidateSet('Menu','Status','ScheduledNightly')][string]$Mode='Menu',[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_ONECLICK_'+$code)}}
function Quote([string]$s){
 Need ([IO.Path]::IsPathRooted($s) -and -not ($s.Contains('"') -or $s.Contains([char]10) -or $s.Contains([char]13))) 'UNSAFE_ARG'
 return '"'+$s+'"'
}
if($OfflineSelfTest){
 Need ($Mode -in @('Menu','Status','ScheduledNightly')) 'MODE_INVALID'
 Write-Host 'NO11_ONECLICK_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADING_APPROVAL_AUTOMATED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settingsFile=Join-Path $store 'settings.json'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $settingsFile -PathType Leaf) -and (Test-Path -LiteralPath $bindingFile -PathType Leaf)) 'EXISTING_INSTALL_REQUIRED'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$python=[string]$binding.python
$engine=[string]$binding.engine
$launcher=Join-Path $engine 'windows\Start-No11UnifiedLauncher.ps1'
$statusTool=Join-Path $PSScriptRoot 'oneclick_status.py'
foreach($file in @($python,$launcher,$statusTool)){
 Need ([IO.Path]::IsPathRooted($file) -and (Test-Path -LiteralPath $file -PathType Leaf)) 'REQUIRED_RUNTIME_NOT_FOUND'
}
function GetStatus {
 $out=@(& $python -B -X utf8 $statusTool --settings $settingsFile --binding $bindingFile)
 $code=$LASTEXITCODE
 Need ($out.Count -eq 1) 'HEALTH_RESPONSE_SHAPE'
 $value=$out[0]|ConvertFrom-Json
 Need ($value.schemaId -ceq 'ARK_NO11_ONECLICK_STATUS_V1' -and $value.brokerOrderTransmission -eq $false -and $value.readOnly -eq $true) 'HEALTH_RESPONSE_UNSAFE'
 if($code -ne 0){$value.canRequestTrade=$false;$value.canRunNightly=$false}
 return $value
}
function LogFiles([string]$task){
 $logs=Join-Path $store 'oneclick-logs'
 [void][IO.Directory]::CreateDirectory($logs)
 $day=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd')
 $nonce=[guid]::NewGuid().ToString('N')
 return @((Join-Path $logs ($task+'-'+$day+'-'+$nonce+'.log')),(Join-Path $logs ($task+'-'+$day+'-'+$nonce+'.err')))
}
function StartOriginal([string]$runMode){
 Need ($runMode -in @('Trade','Weekly')) 'UNEXPECTED_ORIGINAL_MODE'
 $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $launcher),'-Mode',$runMode)
 if($runMode -eq 'Trade'){$args+=@('-IApproveOrdersForToday')}
 $files=LogFiles $runMode
 $p=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory (Split-Path -Parent $launcher) -RedirectStandardOutput $files[0] -RedirectStandardError $files[1] -PassThru -WindowStyle Hidden
 Need ($null -ne $p -and $p.Id -gt 0) 'CHILD_NOT_STARTED'
 # ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1
 # The native Trade launcher opens UI2 once. Observe its result and retry
 # ONLY the independent read-only UI helper if native reported UI failure.
 if($runMode -eq 'Trade'){
  $watch=Join-Path $PSScriptRoot 'Watch-No11OneClickTradeUi.ps1'
  $script:LastUi2Monitor='NOT_INSTALLED'
  if(Test-Path -LiteralPath $watch -PathType Leaf){
   $watchArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',(Quote $watch),'-NativeLog',(Quote $files[0]))
   $watchLogs=LogFiles 'Ui2'
   try{
    $monitor=Start-Process -FilePath 'powershell.exe' -ArgumentList ($watchArgs -join ' ') -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $watchLogs[0] -RedirectStandardError $watchLogs[1] -PassThru -WindowStyle Hidden
    $script:LastUi2Monitor=if($null -ne $monitor -and $monitor.Id -gt 0){'STARTED'}else{'MONITOR_UNAVAILABLE'}
   }catch{
    $script:LastUi2Monitor='MONITOR_UNAVAILABLE'
   }
  }
 }
 return $p.Id
}
if($Mode -eq 'Status'){
 $state=GetStatus
 Write-Host ('NO11_ONECLICK_MODE='+$state.mode)
 Write-Host ('NO11_ONECLICK_REASON='+$state.reason)
 Write-Host ('NO11_ONECLICK_PRELIMINARY_TRADE_ALLOWED='+$state.canRequestTrade)
 Write-Host ('NO11_ONECLICK_NIGHTLY_ALLOWED='+$state.canRunNightly)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if($Mode -eq 'ScheduledNightly'){
 $state=GetStatus
 Need ($state.mode -ceq 'AFTER_CLOSE' -and $state.canRunNightly -eq $true) 'NIGHTLY_NOT_READY'
 # Native Weekly runner checks source pins, RSS status and duplicate run marker.
 # No real trade or approval is requested on this scheduled path.
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $launcher -Mode Weekly
 $code=$LASTEXITCODE
 Need ($code -eq 0) 'NIGHTLY_RUNNER_FAILED'
 Write-Host 'NO11_ONECLICK_NIGHTLY_REQUESTED=True'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$form=New-Object System.Windows.Forms.Form
$form.Text='ARK Terminal - OneClick'
$form.ClientSize=New-Object System.Drawing.Size(760,444)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
$form.StartPosition='CenterScreen'
$form.BackColor=[System.Drawing.Color]::FromArgb(29,32,38)
$form.ForeColor=[System.Drawing.Color]::FromArgb(236,241,246)
$title=New-Object System.Windows.Forms.Label
$title.Text='ARK TERMINAL   /   ONECLICK'
$title.Font=New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=New-Object System.Drawing.Point(24,24)
$form.Controls.Add($title)
$status=New-Object System.Windows.Forms.Label
$status.AutoSize=$false
$status.Size=New-Object System.Drawing.Size(708,108)
$status.Location=New-Object System.Drawing.Point(26,82)
$status.Font=New-Object System.Drawing.Font('Segoe UI',10.5,[System.Drawing.FontStyle]::Regular)
$form.Controls.Add($status)
$trade=New-Object System.Windows.Forms.Button
$trade.Text='START TRADING   /   NORMAL MAX3'
$trade.Size=New-Object System.Drawing.Size(708,52)
$trade.Location=New-Object System.Drawing.Point(26,204)
$form.Controls.Add($trade)
$nightly=New-Object System.Windows.Forms.Button
$nightly.Text='UPDATE NEXT SESSION DATA'
$nightly.Size=New-Object System.Drawing.Size(347,42)
$nightly.Location=New-Object System.Drawing.Point(26,269)
$form.Controls.Add($nightly)
$refresh=New-Object System.Windows.Forms.Button
$refresh.Text='REFRESH STATUS'
$refresh.Size=New-Object System.Drawing.Size(347,42)
$refresh.Location=New-Object System.Drawing.Point(387,269)
$form.Controls.Add($refresh)
$notice=New-Object System.Windows.Forms.Label
$notice.Text='Real orders require explicit daily approval. Original broker safety checks remain active.'
$notice.Size=New-Object System.Drawing.Size(708,40)
$notice.Location=New-Object System.Drawing.Point(26,393)
$form.Controls.Add($notice)
$review=New-Object System.Windows.Forms.Button
$review.Text='REVIEW STOPPED SESSION'
$review.Size=New-Object System.Drawing.Size(347,42)
$review.Location=New-Object System.Drawing.Point(26,322)
$form.Controls.Add($review)
$logsButton=New-Object System.Windows.Forms.Button
$logsButton.Text='OPEN LOGS'
$logsButton.Size=New-Object System.Drawing.Size(347,42)
$logsButton.Location=New-Object System.Drawing.Point(387,322)
$form.Controls.Add($logsButton)
# ARK_NO11_ONECLICK_GRAPHITE_ICEBLUE_THEME_V2
# Display-only. Never change existing order approval, collector, or broker routes.
$title.ForeColor=[System.Drawing.Color]::FromArgb(244,247,250)
$status.ForeColor=[System.Drawing.Color]::FromArgb(228,234,241)
$status.BackColor=[System.Drawing.Color]::FromArgb(40,45,53)
$status.Padding=New-Object System.Windows.Forms.Padding(14,8,12,7)
$notice.ForeColor=[System.Drawing.Color]::FromArgb(170,182,196)
$notice.Font=New-Object System.Drawing.Font('Segoe UI',9,[System.Drawing.FontStyle]::Regular)
foreach($b in @($trade,$nightly,$refresh,$review,$logsButton)){
 $b.FlatStyle=[System.Windows.Forms.FlatStyle]::Flat
 $b.UseVisualStyleBackColor=$false
 $b.BackColor=[System.Drawing.Color]::FromArgb(51,58,68)
 $b.ForeColor=[System.Drawing.Color]::FromArgb(237,242,247)
 $b.FlatAppearance.BorderSize=1
 $b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(82,97,112)
 $b.FlatAppearance.MouseOverBackColor=[System.Drawing.Color]::FromArgb(63,73,86)
 $b.FlatAppearance.MouseDownBackColor=[System.Drawing.Color]::FromArgb(43,53,64)
 $b.Font=New-Object System.Drawing.Font('Segoe UI',10.5,[System.Drawing.FontStyle]::Bold)
 $b.Cursor=[System.Windows.Forms.Cursors]::Hand
}
$trade.BackColor=[System.Drawing.Color]::FromArgb(43,106,132)
$trade.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(90,151,176)
$trade.FlatAppearance.MouseOverBackColor=[System.Drawing.Color]::FromArgb(54,121,146)
function UiReason([string]$raw){
 switch -CaseSensitive ($raw){
  'NIGHTLY_NOT_INSTALLED' {return 'Nightly update not configured'}
  'NIGHTLY_OPERATOR_BUTTON_AVAILABLE' {return 'Nightly update available'}
  'ALREADY_STARTED_TODAY' {return 'Already started today'}
  'PRELIMINARY_INPUTS_READY' {return 'Inputs found - live checks pending'}
  'EXISTING_RUN_REQUIRES_REVIEW' {return 'Existing session requires review'}
  'NEW_ENTRY_WINDOW_CLOSED' {return 'New entries closed (15:20)'}
  'TODAY_HANDOFF_MISSING' {return 'Today data not ready'}
  'HANDOFF_HASH_CHANGED' {return 'Data verification failed'}
  'NON_TRADING_DAY' {return 'No scheduled trading'}
  'CONFIG_UNSAFE' {return 'Configuration needs review'}
  default {return $raw.Replace('_',' ')}
 }
}
# ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1
# Status is read-only: only same-day, source-verified 08:30-08:59 can queue.
# Normal Trade is always launched by the original native 09:00+ path.
function PreopenReserved($s){
 $day=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
 if($s.sessionDate -cne $day){return $false}
 return (Test-Path -LiteralPath (Join-Path $store ('PREOPEN-'+$day+'.request.json')) -PathType Leaf)
}
function CanQueuePreopen($s){
 $now=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
 if($now.DayOfWeek -in @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday) -or
    $now.ToString('HH:mm:ss') -lt '08:30:00' -or
    $now.ToString('HH:mm:ss') -ge '09:00:00'){return $false}
 if($s.sessionDate -cne $now.ToString('yyyy-MM-dd') -or
    $s.mode -cne 'OUTSIDE_ENTRY_WINDOW' -or
    $s.reason -cne 'NEW_ENTRY_WINDOW_CLOSED' -or
    $s.canRequestTrade -eq $true -or (PreopenReserved $s)){return $false}
 return (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'Start-No11PreopenStandby.ps1') -PathType Leaf)
}
function RefreshUi{
 try{
  $s=GetStatus
  $trading=if($s.mode -ceq 'AFTER_CLOSE'){'Closed for today'}elseif($s.canRequestTrade -eq $true){'Awaiting same-day approval'}else{'Not available'}
  $preopen=CanQueuePreopen $s
  $reserved=PreopenReserved $s
  if($preopen){$trading='08:30 STANDBY READY - 09:00 AUTO START'}
  if($reserved){$trading=if($s.reason -ceq 'ALREADY_STARTED_TODAY'){'TRADE REQUESTED - check logs'}else{'09:00 START RESERVED - check logs'}}
  $recovery='No current recovery request'
  if($s.PSObject.Properties.Name -contains 'runHealth'){
   $rh=$s.runHealth
   $attempt=if($rh.PSObject.Properties.Name -contains 'collectorAttempt'){$rh.collectorAttempt}else{'Unknown'}
   $recovery='Review required - collector: '+$attempt
   if($rh.PSObject.Properties.Name -contains 'entryHalted' -and $rh.entryHalted -eq $true){$trading='ENTRY HALTED - review required'}
  }
  $status.Text=('SESSION     '+$s.sessionDate+[Environment]::NewLine+
                'TRADING     '+$trading+[Environment]::NewLine+
                'DATA        '+(UiReason ([string]$s.reason))+[Environment]::NewLine+
                'RECOVERY    '+$recovery)
  $trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen) -and (-not $reserved)
  $nightly.Enabled=($s.canRunNightly -eq $true)
  $review.Enabled=($s.PSObject.Properties.Name -contains 'runHealth' -and $s.runHealth.state -ne 'NO_RUN_POINTER')
 }catch{
  $status.Text='STATUS: SOURCE_OR_RUNTIME_UNVERIFIED -- Trade is blocked'
  $trade.Enabled=$false
  $nightly.Enabled=$false
  $review.Enabled=$false
 }
}
$refresh.Add_Click({RefreshUi})
$trade.Add_Click({
 $s=GetStatus
 if(CanQueuePreopen $s){
  $approval=[System.Windows.Forms.MessageBox]::Show(
   'Authorize REAL broker cash LONG orders for TODAY ONLY, with a SINGLE automatic 09:00 start request? No order before 09:00. Existing RSS, broker, cash, MAX3, one-shot and strategy safety checks remain mandatory. Keep Windows awake and logged in with Excel and Market Speed II connected.',
   'ARK - 08:30 STANDBY FOR 09:00',
   [System.Windows.Forms.MessageBoxButtons]::YesNo,
   [System.Windows.Forms.MessageBoxIcon]::Warning)
  if($approval -ne [System.Windows.Forms.DialogResult]::Yes){return}
  try{
   $standby=Join-Path $PSScriptRoot 'Start-No11PreopenStandby.ps1'
   Need (Test-Path -LiteralPath $standby -PathType Leaf) 'PREOPEN_SCRIPT_MISSING'
   $trade.Enabled=$false
   $result=@(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $standby -Mode Arm -IApproveOrdersForToday)
   Need ($LASTEXITCODE -eq 0 -and ($result -contains 'NO11_PREOPEN_STANDBY=ARMED')) 'PREOPEN_RESERVATION_FAILED'
   $status.Text='PREOPEN STANDBY ARMED for TODAY. Native Trade will be requested once at 09:00 JST if all checks pass. Keep PC awake; check OneClick logs.'
  }catch{
   $status.Text='PREOPEN STANDBY FAILED; no Trade retry. Review OneClick logs and existing reservation.'
  }
  return
 }
 if($s.canRequestTrade -ne $true){RefreshUi;return}
 $answer=[System.Windows.Forms.MessageBox]::Show('Authorize REAL broker cash LONG orders for TODAY ONLY (normal MAX3 / 100 shares) subject to ALL existing RSS, strategy, cash and broker gates? No order or fill is guaranteed.','ARK - explicit same-day trade approval',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Warning)
 if($answer -ne [System.Windows.Forms.DialogResult]::Yes){return}
 try{
  # Native Trade checks are repeated and owns the one-shot trade marker.
  $trade.Enabled=$false
  $id=StartOriginal 'Trade'
  $status.Text='TRADE REQUESTED PID='+$id+'; ARK Terminal 2.0 auto-open via native launcher; UI2 monitor '+$script:LastUi2Monitor+'. Check logs.'
 }catch{
  $status.Text='TRADE REQUEST FAILED; inspect logs before further action'
 }
})
$nightly.Add_Click({
 $s=GetStatus
 if($s.canRunNightly -ne $true){RefreshUi;return}
 $answer=[System.Windows.Forms.MessageBox]::Show('Run existing RSS after-close/weekly processing? No broker orders.','ARK - after-close refresh',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Information)
 if($answer -ne [System.Windows.Forms.DialogResult]::Yes){return}
 try{
  $nightly.Enabled=$false
  $id=StartOriginal 'Weekly'
  $status.Text='AFTER-CLOSE RSS REQUESTED PID='+$id+'; inspect logs'
 }catch{
  $status.Text='AFTER-CLOSE REQUEST FAILED; inspect logs'
 }
})
$review.Add_Click({
 try{
  $s=GetStatus
  if($s.PSObject.Properties.Name -notcontains 'runHealth'){RefreshUi;return}
  # ARK_NO11_ONECLICK_SAME_RUN_RESUME_BUTTON_V1
  # Keep the exact approved white controls, layout and button name.
  # A stopped, source-halted LIVE run may be resumed only after the operator
  # explicitly confirms current broker orders/holdings with Market Speed II.
  $jst=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
  $time=$jst.ToString('HH:mm:ss')
  $canOffer=($s.runHealth.PSObject.Properties.Name -contains 'entryHalted' -and
             $s.runHealth.entryHalted -eq $true -and
             $time -ge '09:00:00' -and $time -lt '15:20:00' -and
             $s.sessionDate -ceq $jst.ToString('yyyy-MM-dd') -and
             (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'Resume-No11SameSession.ps1') -PathType Leaf))
  $resuming=$false
  if($canOffer){
   $answer=[System.Windows.Forms.MessageBox]::Show(
    'Have you checked the CURRENT same-day orders, executions and holdings in Market Speed II? YES: attempt one reviewed SAME-RUN collector/EXIT resume, with exact broker/ledger matching; NEVER resend existing orders. NO: run read-only review only. CANCEL: do nothing. Unknown orders or uncertain holdings block recovery.',
    'ARK - SAME-DAY DISCONNECT RECOVERY',
    [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
    [System.Windows.Forms.MessageBoxIcon]::Warning)
   if($answer -eq [System.Windows.Forms.DialogResult]::Cancel){return}
   $resuming=($answer -eq [System.Windows.Forms.DialogResult]::Yes)
  }
  $tool=Join-Path $PSScriptRoot (if($resuming){'Resume-No11SameSession.ps1'}else{'Review-No11RecoveryReadOnly.ps1'})
  Need (Test-Path -LiteralPath $tool -PathType Leaf) 'REVIEW_HELPER_MISSING'
  $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $tool))
  if($resuming){$args+=@('-Apply','-IConfirmSameDayBrokerOrdersAndPositions')}
  $out=LogFiles (if($resuming){'Recovery'}else{'Review'})
  $proc=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $out[0] -RedirectStandardError $out[1] -PassThru -WindowStyle Hidden
  $status.Text=if($resuming){'RECOVERY REQUEST PID='+$proc.Id+'; see Recovery log for confirmed result (NOT a broker ACK)'}else{'READ-ONLY RECOVERY REVIEW PID='+$proc.Id+'; open logs for results'}
 }catch{
  $status.Text='RECOVERY/REVIEW NOT STARTED; no trading controls changed'
 }
})
$logsButton.Add_Click({
 $folder=Join-Path $store 'oneclick-logs'
 if(Test-Path -LiteralPath $folder -PathType Container){Start-Process -FilePath 'explorer.exe' -ArgumentList ('"'+$folder+'"')}
})
$timer=New-Object System.Windows.Forms.Timer
$timer.Interval=15000
$timer.Add_Tick({RefreshUi})
$form.Add_Shown({$timer.Start()})
$form.Add_FormClosed({$timer.Stop()})
RefreshUi
[void]$form.ShowDialog()
