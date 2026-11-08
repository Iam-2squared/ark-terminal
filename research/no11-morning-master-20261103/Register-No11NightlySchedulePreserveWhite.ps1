# Add daily after-close RSS updates without replacing the user's approved white UI.
# No real orders; native Weekly/after-close source/data contracts remain intact.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_SCHEDULE_'+$code)}
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 Write-Host 'NO11_SCHEDULE_WHITE_UI_OFFLINE_SELFTEST=PASS'
 Write-Host 'TASK_REGISTERED=False'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply 'EXPLICIT_APPLY_REQUIRED'
$zone=[TimeZoneInfo]::Local
Need ($zone.GetUtcOffset([datetime]::Now).TotalHours -eq 9) 'PC_MUST_USE_JST'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$oneclick=Join-Path $store 'oneclick\Start-No11OneClick.ps1'
$bindingFile=Join-Path $store 'automatic-inputs.json'
$settingsFile=Join-Path $store 'settings.json'
foreach($f in @($oneclick,$bindingFile,$settingsFile)){
 Need (Test-Path -LiteralPath $f -PathType Leaf) 'INSTALL_REQUIRED'
}
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
$settings=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.dailyCycleTool) -and
      [IO.Path]::IsPathRooted([string]$binding.dailyCycleRoot) -and
      (Test-Path -LiteralPath ([string]$binding.dailyCycleTool) -PathType Leaf) -and
      (Test-Path -LiteralPath ([string]$binding.dailyCycleRoot) -PathType Container)) 'NIGHTLY_NOT_INSTALLED'
Need ($settings.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
      $settings.sameDayApprovalRequired -eq $true -and
      $settings.automaticOrderAuthorization -eq $false -and
      $settings.orderTransmission -eq $false) 'SETTINGS_UNSAFE'
# Both Scheduling and Trade use an unchanged installed OneClick; verify the
# scheduled route exists and the same-day approval remains in its live route.
$source=[IO.File]::ReadAllText($oneclick)
Need ($source.Contains("'ScheduledNightly'") -and
      $source.Contains("'-Mode'") -and
      $source.Contains("IApproveOrdersForToday") -and
      $source.Contains("NIGHTLY_NOT_READY") -and
      $source.Contains("NO11_ONECLICK_NIGHTLY_REQUESTED=True")) 'SCHEDULED_ROUTE_CONTRACT'
$taskName='ARK-No11-AfterClose-ReadOnly'
Need ($null -eq (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) 'TASK_ALREADY_EXISTS_REVIEW'
$active=@(Get-CimInstance Win32_Process|Where-Object{
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
 [string]$_.CommandLine -match 'Run-No11NightlyCycle|Prepare-No11WeeklyAfterClose|Run-No11WeeklyCandidateRefresh'
})
Need ($active.Count -eq 0) 'NIGHTLY_ALREADY_RUNNING'
$exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$oneclick+'" -Mode ScheduledNightly'
$action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory (Split-Path $oneclick -Parent)
$trigger=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At ([datetime]::Today.AddHours(18).AddMinutes(10))
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settingsTask=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 12) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settingsTask -Description 'ARK No.1.1: native after-close RSS originals / next-day immutable handoff ONLY. Never start Trade.' -ErrorAction Stop|Out-Null
$created=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
Need ($created.State -ne 'Disabled') 'TASK_DISABLED_AFTER_REGISTER'
Write-Host 'NO11_SCHEDULE_INSTALL=PASS'
Write-Host 'TASK_NAME=ARK-No11-AfterClose-ReadOnly'
Write-Host 'SCHEDULED_JST=MON_FRI_18_10'
Write-Host 'REQUIRES_INTERACTIVE_WINDOWS_LOGIN=True'
Write-Host 'REQUIRES_EXCEL_MSII_RSS_CONNECTED=True'
Write-Host 'CANNOT_RUN_IF_PC_OFF_OR_ASLEEP=True'
Write-Host 'FAILED_NIGHTLY_DOES_NOT_ENABLE_TRADE=True'
Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
Write-Host 'EXCEL_TOUCHED=False'
Write-Host 'TRADE_LAUNCHED=False'
Write-Host 'ORDER_TRANSMISSION=False'
