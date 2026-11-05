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
# Additional ACTUAL installer exercise in a fake user's local AppData.
# Proves that the white theme, Clean helper and original bytes are preserved.
$priorLocal=$env:LOCALAPPDATA
$sandbox=Join-Path $env:TEMP ('no11-clean-local-mock-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $sandbox 'appdata'
try{
 $root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $whiteDir=Join-Path $root 'oneclick'
 $sourceDir=Join-Path $sandbox 'engine\windows'
 [void][IO.Directory]::CreateDirectory($whiteDir)
 [void][IO.Directory]::CreateDirectory($sourceDir)
 $python=(Get-Command python -ErrorAction Stop).Source
 $localReference=Join-Path $sourceDir 'Capture-No11SessionReferenceReadOnly.ps1'
 & $python -B $pythonTest --emit-fixture $localReference
 if($LASTEXITCODE -ne 0){throw 'NO11_CLEAN_MOCK_FIXTURE_CREATION_FAILED'}
 $originalReference=[IO.File]::ReadAllBytes($localReference)
 $clean=Join-Path $sourceDir 'No11CleanCompatibility.ps1'
 [IO.File]::WriteAllText($clean,'function Read-No11CleanReferenceRows {}' + [char]10 +
  'function ConvertTo-No11CleanJson {}',[Text.UTF8Encoding]::new($false))
 $ui=Join-Path $whiteDir 'Start-No11OneClick.ps1'
 $originalUi=([IO.File]::ReadAllText((Join-Path $dir 'Start-No11OneClick.ps1'))).Replace(
  'FromArgb(29,32,38)','FromArgb(250,250,250)')
 [IO.File]::WriteAllText($ui,$originalUi,[Text.UTF8Encoding]::new($false))
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  engine=(Split-Path -Parent $sourceDir)
  python=$python
  orderTransmission=$false
 }
 [IO.File]::WriteAllText((Join-Path $root 'automatic-inputs.json'),(
  ConvertTo-Json -InputObject $binding -Compress),[Text.UTF8Encoding]::new($false))
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $script -Apply
 if($LASTEXITCODE -ne 0){throw 'NO11_CLEAN_MOCK_ACTUAL_INSTALL_FAILED'}
 $newText=[IO.File]::ReadAllText($localReference)
 if(-not ($newText.Contains('No11CleanCompatibility.ps1') -and
  $newText.Contains('Read-No11CleanReferenceRows') -and
  $newText.Contains('ConvertTo-No11CleanJson') -and
  $newText.Contains('CONFIGURED_BROKER_BOOK_IDENTITY') -and
  $newText.Contains('EXCEL_ROT_PID_MISMATCH') -and
  $newText.Contains('NO11_REFERENCE_DIAGNOSTIC_STAGE='))){
  throw 'NO11_CLEAN_MOCK_ORIGINAL_EXTENSION_WAS_LOST'
 }
 $uiText=[IO.File]::ReadAllText($ui)
 if(-not ($uiText.Contains('FromArgb(250,250,250)') -and
  $uiText.Contains('RETRY START TRADING / NORMAL MAX3'))){
  throw 'NO11_CLEAN_MOCK_WHITE_THEME_NOT_PRESERVED'
 }
 $backup=@(Get-ChildItem -LiteralPath $root -Directory -Filter 'local-clean-retry-backup-*')
 if($backup.Count -ne 1){throw 'NO11_CLEAN_MOCK_BACKUP_MISSING'}
 $prior=[IO.File]::ReadAllBytes((Join-Path $backup[0].FullName 'Capture-No11SessionReferenceReadOnly.before.ps1'))
 if(([Convert]::ToBase64String($prior)) -cne ([Convert]::ToBase64String($originalReference))){
  throw 'NO11_CLEAN_MOCK_ORIGINAL_BYTES_CHANGED'
 }
 if(Test-Path -LiteralPath (Join-Path $root 'TRADE-2026-11-05.launch.json')){
  throw 'NO11_CLEAN_MOCK_CREATED_TRADE_MARKER'
 }
 Write-Host 'NO11_LOCAL_CLEAN_REAL_INSTALL_MOCK=PASS'
}finally{
 $env:LOCALAPPDATA=$priorLocal
 if(Test-Path -LiteralPath $sandbox -PathType Container){
  Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
 }
}
Write-Host 'NO11_LOCAL_CLEAN_WINDOWS_OFFLINE=PASS'
Write-Host 'WHITE_UI_MODIFIED=False'
Write-Host 'BROKER_ORDER_TRANSMISSION=False'
