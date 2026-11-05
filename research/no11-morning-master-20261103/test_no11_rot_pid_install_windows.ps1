# True Windows 5.1 installation acceptance in fake LOCALAPPDATA only.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_PID_MOCK_'+$why)}}
$originalLocal=$env:LOCALAPPDATA
$mock=Join-Path $env:TEMP ('ark-rot-pid-ci-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $mock 'fake-local'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $engine=Join-Path $mock 'engine'
 $scripts=Join-Path $engine 'windows'
 $oneclick=Join-Path $store 'oneclick'
 [void][IO.Directory]::CreateDirectory($scripts)
 [void][IO.Directory]::CreateDirectory($oneclick)
 $python=(Get-Command python -ErrorAction Stop).Source
 $ref=Join-Path $scripts 'Capture-No11SessionReferenceReadOnly.ps1'
 & $python -B (Join-Path $PSScriptRoot 'test_local_rot_pid_probe.py') --emit-installed-fixture $ref
 Need ($LASTEXITCODE -eq 0) 'INSTALLED_SOURCE_FIXTURE'
 $original=[IO.File]::ReadAllBytes($ref)
 $clean=Join-Path $scripts 'No11CleanCompatibility.ps1'
 $white=Join-Path $oneclick 'Start-No11OneClick.ps1'
 [IO.File]::WriteAllText($clean,'# ORIGINAL CLEAN COMPATIBILITY HELPER PRESERVED',[Text.UTF8Encoding]::new($false))
 [IO.File]::WriteAllText($white,'# USER APPROVED WHITE ONECLICK UNMODIFIED',[Text.UTF8Encoding]::new($false))
 $originalClean=[IO.File]::ReadAllBytes($clean)
 $originalWhite=[IO.File]::ReadAllBytes($white)
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  engine=$engine
  python=$python
  orderTransmission=$false
 }
 [IO.File]::WriteAllText((Join-Path $store 'automatic-inputs.json'),(
  ConvertTo-Json -InputObject $binding -Compress),[Text.UTF8Encoding]::new($false))
 $installer=Join-Path $PSScriptRoot 'Install-No11RotPidDiagnostics.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'ACTUAL_INSTALL_FAILED'
 $updated=[IO.File]::ReadAllText($ref)
 Need ($updated.Contains('NO11_REFERENCE_ROT_PID_PROBE=') -and
       $updated.Contains('$identityAttempt -le 3') -and
       $updated.Contains('EXCEL_ROT_PID_MISMATCH') -and
       $updated.Contains('No11CleanCompatibility.ps1') -and
       $updated.Contains('CONFIGURED_BROKER_BOOK_IDENTITY') -and
       $updated.Contains('Read-No11CleanReferenceRows') -and
       $updated.Contains('ConvertTo-No11CleanJson')) 'PATCH_OR_ORIGINAL_POLICY_LOST'
 Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
       ([Convert]::ToBase64String($originalWhite))) 'WHITE_UI_CHANGED'
 Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($clean))) -ceq
       ([Convert]::ToBase64String($originalClean))) 'CLEAN_HELPER_CHANGED'
 $backups=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'rot-pid-diagnostic-backup-*')
 Need ($backups.Count -eq 1) 'BACKUP_MISSING'
 $bytes=[IO.File]::ReadAllBytes((Join-Path $backups[0].FullName 'Capture-No11SessionReferenceReadOnly.before.ps1'))
 Need (([Convert]::ToBase64String($bytes)) -ceq ([Convert]::ToBase64String($original))) 'BACKUP_NOT_BYTE_IDENTICAL'
 Need (-not (Test-Path -LiteralPath (Join-Path $store 'TRADE-2026-11-05.launch.json')) -and
       -not (Test-Path -LiteralPath (Join-Path $store 'ONECLICK-RETRY-2026-11-05.claim.json'))) 'INSTALL_CREATED_ORDER_STATE'
 Write-Host 'NO11_ROT_PID_MOCK_INSTALL=PASS'
 Write-Host 'ORIGINAL_CLEAN_AND_WHITE_PRESERVED=True'
 Write-Host 'NO_ORDER_STATE_CREATED=True'
}finally{
 $env:LOCALAPPDATA=$originalLocal
 if(Test-Path -LiteralPath $mock -PathType Container){
  Remove-Item -LiteralPath $mock -Recurse -Force -ErrorAction SilentlyContinue
 }
}
