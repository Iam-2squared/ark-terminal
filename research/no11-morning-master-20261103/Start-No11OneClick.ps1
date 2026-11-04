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
$form.ClientSize=New-Object System.Drawing.Size(680,412)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
$form.StartPosition='CenterScreen'
$form.BackColor=[System.Drawing.Color]::FromArgb(19,27,39)
$form.ForeColor=[System.Drawing.Color]::White
$title=New-Object System.Windows.Forms.Label
$title.Text='ARK TERMINAL | NORMAL MAX3 | STATUS FIRST'
$title.Font=New-Object System.Drawing.Font('Segoe UI',14,[System.Drawing.FontStyle]::Bold)
$title.AutoSize=$true
$title.Location=New-Object System.Drawing.Point(24,24)
$form.Controls.Add($title)
$status=New-Object System.Windows.Forms.Label
$status.AutoSize=$false
$status.Size=New-Object System.Drawing.Size(630,94)
$status.Location=New-Object System.Drawing.Point(26,76)
$status.Font=New-Object System.Drawing.Font('Consolas',10)
$form.Controls.Add($status)
$trade=New-Object System.Windows.Forms.Button
$trade.Text='START NORMAL MAX3 TRADING'
$trade.Size=New-Object System.Drawing.Size(628,46)
$trade.Location=New-Object System.Drawing.Point(26,180)
$form.Controls.Add($trade)
$nightly=New-Object System.Windows.Forms.Button
$nightly.Text='AFTER-CLOSE RSS UPDATE (NO ORDERS)'
$nightly.Size=New-Object System.Drawing.Size(310,36)
$nightly.Location=New-Object System.Drawing.Point(26,236)
$form.Controls.Add($nightly)
$refresh=New-Object System.Windows.Forms.Button
$refresh.Text='REFRESH STATUS'
$refresh.Size=New-Object System.Drawing.Size(308,36)
$refresh.Location=New-Object System.Drawing.Point(346,236)
$form.Controls.Add($refresh)
$notice=New-Object System.Windows.Forms.Label
$notice.Text='Opening this window never authorizes orders. Real trading needs explicit same-day YES.'
$notice.Size=New-Object System.Drawing.Size(625,45)
$notice.Location=New-Object System.Drawing.Point(26,338)
$form.Controls.Add($notice)
$review=New-Object System.Windows.Forms.Button
$review.Text='REVIEW FAILED RUN (READ ONLY)'
$review.Size=New-Object System.Drawing.Size(310,36)
$review.Location=New-Object System.Drawing.Point(26,283)
$form.Controls.Add($review)
$logsButton=New-Object System.Windows.Forms.Button
$logsButton.Text='OPEN ARK LOGS'
$logsButton.Size=New-Object System.Drawing.Size(308,36)
$logsButton.Location=New-Object System.Drawing.Point(346,283)
$form.Controls.Add($logsButton)
function RefreshUi{
 try{
  $s=GetStatus
  $detail=''
  if($s.PSObject.Properties.Name -contains 'runHealth'){
   $rh=$s.runHealth
   $attempt=if($rh.PSObject.Properties.Name -contains 'collectorAttempt'){$rh.collectorAttempt}else{'UNVERIFIED'}
   $halt=if($rh.PSObject.Properties.Name -contains 'entryHalted'){$rh.entryHalted}else{'UNVERIFIED'}
   $detail=[Environment]::NewLine+'RUN: '+$rh.state+' / COLLECTOR: '+$attempt+' / ENTRY HALT: '+$halt
  }
  $status.Text=('SESSION: '+$s.sessionDate+[Environment]::NewLine+'STATUS: '+$s.mode+' / '+$s.reason+$detail+[Environment]::NewLine+'Preliminary only: Excel/RSS verified by native launcher')
  $trade.Enabled=($s.canRequestTrade -eq $true)
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
 if($s.canRequestTrade -ne $true){RefreshUi;return}
 $answer=[System.Windows.Forms.MessageBox]::Show('Authorize REAL broker cash LONG orders for TODAY ONLY (normal MAX3 / 100 shares) subject to ALL existing RSS, strategy, cash and broker gates? No order or fill is guaranteed.','ARK - explicit same-day trade approval',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Warning)
 if($answer -ne [System.Windows.Forms.DialogResult]::Yes){return}
 try{
  # Native Trade checks are repeated and owns the one-shot trade marker.
  $trade.Enabled=$false
  $id=StartOriginal 'Trade'
  $status.Text='TRADE REQUESTED PID='+$id+'; inspect logs and MSII for actual broker orders'
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
  $tool=Join-Path $PSScriptRoot 'Review-No11RecoveryReadOnly.ps1'
  Need (Test-Path -LiteralPath $tool -PathType Leaf) 'REVIEW_HELPER_MISSING'
  $args=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Quote $tool))
  $out=LogFiles 'Review'
  $proc=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $out[0] -RedirectStandardError $out[1] -PassThru -WindowStyle Hidden
  $status.Text='READ-ONLY RECOVERY REVIEW PID='+$proc.Id+'; open logs for results'
 }catch{
  $status.Text='RECOVERY REVIEW NOT STARTED; no trading controls changed'
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
