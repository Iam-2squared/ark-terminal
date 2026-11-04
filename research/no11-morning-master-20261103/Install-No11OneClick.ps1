# Install OneClick additive desktop entry without modifying protected ARK live files.
# Optional interactive-user after-close task, never a trade or order task.
param(
 [switch]$Apply,
 [switch]$EnableNightlyTask,
 [string]$SourceDir=$PSScriptRoot,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_ONECLICK_INSTALL_'+$why)}}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $EnableNightlyTask) 'SELFTEST_MODE'
 Write-Host 'NO11_ONECLICK_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$settingsFile=Join-Path $store 'settings.json'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $settingsFile -PathType Leaf) -and (Test-Path -LiteralPath $bindingFile -PathType Leaf)) 'INSTALLED_ARK_REQUIRED'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$engine=[string]$binding.engine
$python=[string]$binding.python
Need ((Test-Path -LiteralPath (Join-Path $engine 'windows\Start-No11UnifiedLauncher.ps1') -PathType Leaf) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'NATIVE_LAUNCHER_MISSING'
function AssertStopped {
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)(\.exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($active.Count -eq 0) 'ACTIVE_ARK_PROCESS'
}
AssertStopped

function Blob([byte[]]$raw) {
 $text=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $canonical=[Text.Encoding]::UTF8.GetBytes($text.Replace(([string][char]13)+([string][char]10),[string][char]10))
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$canonical.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$canonical.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($canonical,0,$all,$header.Length,$canonical.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$pins=[ordered]@{
 'oneclick_status.py'='1f5611336abc8d68731a44243fa67a6c6a4ebf9f'
 'Start-No11OneClick.ps1'='6d1f91d2470e96df28a181f5ebd89b0151fabf67'
 'Review-No11RecoveryReadOnly.ps1'='e0ba60daa329a4c301ac0db62ab980d55096feec'
 'no11_same_day_reconcile.py'='e26e0cdf8d6af186cc1d1ec40aca75f02e71589f'
}
$source=@{}
foreach($name in $pins.Keys){
 $src=Join-Path $SourceDir $name
 Need (Test-Path -LiteralPath $src -PathType Leaf) 'SOURCE_MISSING'
 $raw=[IO.File]::ReadAllBytes($src)
 Need ((Blob $raw) -ceq $pins[$name]) 'SOURCE_HASH_CHANGED'
 $source[$name]=$raw
}
$oneclick=Join-Path $store 'oneclick'
[void][IO.Directory]::CreateDirectory($oneclick)
$backup=Join-Path $store ('oneclick-install-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($backup)
$old=@{}
foreach($name in $pins.Keys){
 $target=Join-Path $oneclick $name
 $old[$name]=if(Test-Path -LiteralPath $target -PathType Leaf){[IO.File]::ReadAllBytes($target)}else{$null}
 if($null -ne $old[$name]){[IO.File]::WriteAllBytes((Join-Path $backup ($name+'.before')),$old[$name])}
}
$launcher=Join-Path $oneclick 'Start-No11OneClick.ps1'
$pyfile=Join-Path $oneclick 'oneclick_status.py'
$desktop=[Environment]::GetFolderPath('Desktop')
$shortcut=Join-Path $desktop 'ARK Terminal OneClick.lnk'
$existingShortcut=$null
if(Test-Path -LiteralPath $shortcut -PathType Leaf){
 $existingShortcut=[IO.File]::ReadAllBytes($shortcut)
 [IO.File]::WriteAllBytes((Join-Path $backup 'OneClick.lnk.before'),$existingShortcut)
}
# Build and parse candidate before touching the installed OneClick target.
$candidate=Join-Path $backup 'OneClick.candidate.ps1'
[IO.File]::WriteAllBytes($candidate,$source['Start-No11OneClick.ps1'])
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tokens,[ref]$errors)
Need ($errors.Count -eq 0) 'POWERSHELL_PARSE'
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest | Out-Null
Need ($LASTEXITCODE -eq 0) 'POWERSHELL_SELFTEST'
$reviewCandidate=Join-Path $backup 'Review.candidate.ps1'
[IO.File]::WriteAllBytes($reviewCandidate,$source['Review-No11RecoveryReadOnly.ps1'])
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($reviewCandidate,[ref]$tokens,[ref]$errors)
Need ($errors.Count -eq 0) 'REVIEW_POWERSHELL_PARSE'
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $reviewCandidate -OfflineSelfTest | Out-Null
Need ($LASTEXITCODE -eq 0) 'REVIEW_POWERSHELL_SELFTEST'
$pythonSyntax='import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8-sig").read())'
$pythonCandidate=Join-Path $backup 'oneclick-status.candidate.py'
[IO.File]::WriteAllBytes($pythonCandidate,$source['oneclick_status.py'])
& $python -B -c $pythonSyntax $pythonCandidate
Need ($LASTEXITCODE -eq 0) 'PYTHON_SYNTAX'
$reconcileCandidate=Join-Path $backup 'reconcile.candidate.py'
[IO.File]::WriteAllBytes($reconcileCandidate,$source['no11_same_day_reconcile.py'])
& $python -B -c $pythonSyntax $reconcileCandidate
Need ($LASTEXITCODE -eq 0) 'RECOVERY_PYTHON_SYNTAX'
if($EnableNightlyTask){
 Need ($binding.PSObject.Properties.Name -contains 'dailyCycleTool' -and
       (Test-Path -LiteralPath ([string]$binding.dailyCycleTool) -PathType Leaf) -and
       (Test-Path -LiteralPath ([string]$binding.dailyCycleRoot) -PathType Container)) 'NIGHTLY_NOT_INSTALLED'
 $taskName='ARK-No11-AfterClose-ReadOnly'
 $already=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
 Need ($null -eq $already) 'TASK_EXISTS_MANUAL_REVIEW'
}
AssertStopped
$installed=@()
$taskInstalled=$false
try{
 foreach($name in $pins.Keys){
  $target=Join-Path $oneclick $name
  $tmp=$target+'.candidate-'+[guid]::NewGuid().ToString('N')
  [IO.File]::WriteAllBytes($tmp,$source[$name])
  if($null -ne $old[$name]){
   Need ([IO.File]::ReadAllBytes($target).Length -eq $old[$name].Length) 'TARGET_CONCURRENT_CHANGE'
   $beforeHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
   $backupHash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($old[$name]))).Replace('-','')
   Need ($beforeHash -ceq $backupHash) 'TARGET_CHANGED'
   [IO.File]::Replace($tmp,$target,[System.Management.Automation.Language.NullString]::Value)
  }else{
   Need (-not (Test-Path -LiteralPath $target)) 'TARGET_CONCURRENT_CREATION'
   [IO.File]::Move($tmp,$target)
  }
  $installed+=,$name
 }
 $shell=New-Object -ComObject WScript.Shell
 $link=$shell.CreateShortcut($shortcut)
 $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $link.TargetPath=$exe
 $link.Arguments='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$launcher+'" -Mode Menu'
 $link.WorkingDirectory=$oneclick
 $link.Description='ARK No11: existing broker checks and same-day approval, no automatic orders on open'
 $link.Save()
 if($EnableNightlyTask){
  $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
  $args='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$launcher+'" -Mode ScheduledNightly'
  $action=New-ScheduledTaskAction -Execute $exe -Argument $args -WorkingDirectory $oneclick
  $trigger=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At ([datetime]::Today.AddHours(18).AddMinutes(10))
  $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
  $options=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $options -Description 'ARK No11: only after-close source preparation; NEVER LIVE orders' -ErrorAction Stop|Out-Null
  $taskInstalled=$true
 }
 Write-Host 'NO11_ONECLICK_INSTALL=PASS'
 Write-Host 'DESKTOP_SHORTCUT_CREATED=True'
 Write-Host 'NIGHTLY_TASK_INSTALLED='+$taskInstalled
 Write-Host 'SAME_DAY_TRADE_APPROVAL_REQUIRED=True'
 Write-Host 'ORIGINAL_TRADE_FILES_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
}catch{
 if($taskInstalled){Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue}
 if($null -eq $existingShortcut){if(Test-Path -LiteralPath $shortcut){Remove-Item -LiteralPath $shortcut -Force}}
 else{[IO.File]::WriteAllBytes($shortcut,$existingShortcut)}
 foreach($name in $installed){
  $dest=Join-Path $oneclick $name
  if($null -eq $old[$name]){if(Test-Path -LiteralPath $dest){Remove-Item -LiteralPath $dest -Force}}
  else{[IO.File]::WriteAllBytes($dest,$old[$name])}
 }
 throw
}
