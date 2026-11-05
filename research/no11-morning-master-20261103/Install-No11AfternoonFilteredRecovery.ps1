# One-time 2026-11-05 afternoon 12:30 standby installer/ARM.
# Patch only the stale SEED-date helper if still present; preserve WHITE UI.
# Does not call Trade or broker at installation/ARM. Optional explicit -ArmToday
# starts a detached worker that may request native Trade ONCE at >= 12:30 JST.
param([switch]$Apply,[switch]$ArmToday,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_AFTERNOON_INSTALL_'+$reason)}
}
function Blob([string]$filename){
 $raw=[IO.File]::ReadAllBytes($filename)
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $s=$s.Replace(([string][char]13+[char]10),[string][char]10)
 $bytes=[Text.Encoding]::UTF8.GetBytes($s)
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $joined=New-Object byte[] ($prefix.Length+$bytes.Length)
 [array]::Copy($prefix,0,$joined,0,$prefix.Length)
 [array]::Copy($bytes,0,$joined,$prefix.Length,$bytes.Length)
 $h=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($joined))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $ArmToday) 'SELFTEST_FLAGS'
 Write-Host 'NO11_AFTERNOON_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_THEME_CHANGED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_INSTALL_REQUIRED'
$now=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9))
Need ($now.ToString('yyyy-MM-dd') -ceq '2026-11-05') 'ONLY_TODAY'
if($ArmToday){
 Need ($now.ToString('HH:mm:ss') -ge '11:00:00' -and
       $now.ToString('HH:mm:ss') -lt '12:30:00') 'ARM_ONLY_BEFORE_1230'
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$oneclick=Join-Path $store 'oneclick'
$white=Join-Path $oneclick 'Start-No11OneClick.ps1'
$helper=Join-Path $oneclick 'Recover-No11FilteredMorning.ps1'
$worker=Join-Path $oneclick 'Start-No11AfternoonFilteredRecovery.ps1'
Need ((Test-Path -LiteralPath $white -PathType Leaf) -and
      (Test-Path -LiteralPath $helper -PathType Leaf) -and
      (Test-Path -LiteralPath $oneclick -PathType Container)) 'FIRST_39_FIX_REQUIRED'
$whiteHash=(Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash
$oldHelper='d844d7a45cb9bbcd247258ca16dc7797cbd4a6b4'
$newHelper='a05315c6840fce75c70f96e36d1c7d6a073cc6e6'
$current=Blob $helper
Need ($current -in @($oldHelper,$newHelper)) 'UNKNOWN_HELPER_VERSION'
$temp=Join-Path $env:TEMP ('no11-afternoon-install-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'
 $afternoonRef='50fffd85f20990109383733ce499c4fd6a7f2dab'
 $afternoonPin='537fa896d6931852c7cfbd8be497099e8bdf9432'
 $afternoonName='research/no11-morning-master-20261103/Start-No11AfternoonFilteredRecovery.ps1'
 $incoming=Join-Path $temp 'afternoon.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri ($uri+$afternoonRef+'/'+$afternoonName) -OutFile $incoming -ErrorAction Stop
 Need ((Blob $incoming) -ceq $afternoonPin) 'AFTERNOON_SCRIPT_PIN_CHANGED'
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($incoming,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'AFTERNOON_PS_SYNTAX'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $incoming -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'AFTERNOON_SCRIPT_SELFTEST'
 $busy=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11AfternoonFilteredRecovery[.]ps1|Recover-No11FilteredMorning[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($busy.Count -eq 0) 'ACTIVE_TRADE_OR_RECOVERY'
 $backup=Join-Path $store ('afternoon-installer-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Recover-No11FilteredMorning.before.ps1'),
                           [IO.File]::ReadAllBytes($helper))
 if($current -ceq $oldHelper){
  $repair=Join-Path $temp 'repair.ps1'
  $repairCommit='d8087a5f1553c55a3c76dab62d85107ce6e25b77'
  $repairName='research/no11-morning-master-20261103/Repair-No11MorningRetrySeedDate.ps1'
  Invoke-WebRequest -UseBasicParsing -Uri ($uri+$repairCommit+'/'+$repairName) -OutFile $repair -ErrorAction Stop
  Need ((Blob $repair) -ceq 'ad2c4fa438a46199a8bbc0a01feecfaadc0e5f83') 'REPAIR_PIN_CHANGED'
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $repair -Apply
  Need ($LASTEXITCODE -eq 0) 'SEED_DATE_REPAIR_FAILED'
  Write-Host 'NO11_AFTERNOON_HELPER=SEED_DATE_PATCHED'
 }else{
  Write-Host 'NO11_AFTERNOON_HELPER=ALREADY_CORRECT'
 }
 Need ((Blob $helper) -ceq $newHelper) 'HELPER_CHANGED_OR_REPAIR_FAILED'
 if(Test-Path -LiteralPath $worker -PathType Leaf){
  Need ((Blob $worker) -ceq $afternoonPin) 'AFTERNOON_WORKER_PREEXISTS_DIFFERENT'
 }else{
  [IO.File]::WriteAllBytes($worker,[IO.File]::ReadAllBytes($incoming))
 }
 Need ((Blob $worker) -ceq $afternoonPin -and
       (Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $whiteHash) 'WHITE_OR_WORKER_CHANGED'
 Write-Host 'NO11_AFTERNOON_INSTALL=PASS'
 Write-Host 'WAIT_FOR_JST=12:30'
 Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
 if($ArmToday){
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $worker -Mode Arm -UseTodayApprovedStandby
  Need ($LASTEXITCODE -eq 0) 'AFTERNOON_ARM_FAILED'
 }
}catch{
 $message=[string]$_.Exception.Message
 Write-Host ('NO11_AFTERNOON_INSTALL=BLOCKED|'+$message)
 throw
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
