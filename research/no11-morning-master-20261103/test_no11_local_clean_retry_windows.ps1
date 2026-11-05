# Offline Windows 5.1 test; never uses Excel, brokers, or trading.
$ErrorActionPreference='Stop'
$dir=$PSScriptRoot
$script=Join-Path $dir 'Install-No11LocalCleanRetry.ps1'
$pythonTest=Join-Path $dir 'test_local_clean_reference_patch.py'
foreach($f in @($script,(Join-Path $dir 'Retry-No11OneClickPreorder.ps1'))){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($f,[ref]$tokens,[ref]$errors)
 if($errors.Count -gt 0){throw 'NO11_LOCAL_CLEAN_PARSE_FAILED'}
}
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script -OfflineSelfTest
if($LASTEXITCODE -ne 0){throw 'NO11_LOCAL_CLEAN_INSTALL_SELFTEST_FAILED'}
& python -B $pythonTest
if($LASTEXITCODE -ne 0){throw 'NO11_LOCAL_CLEAN_EXACT_BLOB_FIXTURE_FAILED'}
Write-Host 'NO11_LOCAL_CLEAN_WINDOWS_OFFLINE=PASS'
Write-Host 'WHITE_UI_MODIFIED=False'
Write-Host 'BROKER_ORDER_TRANSMISSION=False'
