# Windows 5.1 actual code-only install on completely isolated fake LOCALAPPDATA.
# No Excel, no real orders, no user UI file, no application startup.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_SELECTION_MOCK_'+$why)}}
$prior=$env:LOCALAPPDATA
$sandbox=Join-Path $env:TEMP ('ark-no11-ui-selection-test-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $sandbox 'fake-appdata'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $one=Join-Path $store 'oneclick'
 [void][IO.Directory]::CreateDirectory($one)
 $python=(Get-Command python -ErrorAction Stop).Source
 $originalText=Get-Content (Join-Path $PSScriptRoot 'Start-No11OneClick.ps1') -Raw -Encoding UTF8
 # The production user's local WHITE theme is not in Git; test an alternative
 # theme with the original reserved PREOPEN and verified one-shot retry.
 $whiteTheme=$originalText.Replace('FromArgb(29,32,38)','FromArgb(246,246,246)')
 $whiteTheme=$whiteTheme.Replace('FromArgb(236,241,246)','FromArgb(23,29,37)')
 $initial=Join-Path $sandbox 'original-white.ps1'
 [IO.File]::WriteAllText($initial,$whiteTheme,[Text.UTF8Encoding]::new($false))
 $white=Join-Path $one 'Start-No11OneClick.ps1'
 & $python -B (Join-Path $PSScriptRoot 'patch_oneclick_preorder_retry.py') --original $initial --candidate $white
 Need ($LASTEXITCODE -eq 0) 'INITIAL_VERIFIED_RETRY_FIXTURE'
 $before=[IO.File]::ReadAllBytes($white)
 $root=Join-Path $sandbox 'private-cycle'
 [void][IO.Directory]::CreateDirectory($root)
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  orderTransmission=$false
  python=$python
  dailyCycleRoot=$root
 }
 [IO.File]::WriteAllText((Join-Path $store 'automatic-inputs.json'),(
   ConvertTo-Json -InputObject $binding -Compress),[Text.UTF8Encoding]::new($false))
 $installer=Join-Path $PSScriptRoot 'Install-No11OneClickSelectionStatus.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Apply
 Need ($LASTEXITCODE -eq 0) 'ACTUAL_INSTALLER_FAILED'
 $text=[IO.File]::ReadAllText($white)
 Need ($text.Contains('FromArgb(246,246,246)') -and
       $text.Contains('FromArgb(23,29,37)') -and
       $text.Contains('RETRY START TRADING / NORMAL MAX3') -and
       $text.Contains('No11WeeklyDailySelectionStatus') -and
       $text.Contains('ReadNo11SelectionDisplay') -and
       $text.Contains('if(CanQueuePreopen $s){') -and
       $text.Contains('$nightly.Add_Click({')) 'WHITE_THEME_OR_BUTTON_REMOVED'
 $reader=Join-Path $one 'no11_selection_status.py'
 Need (Test-Path -LiteralPath $reader -PathType Leaf) 'READ_ONLY_SELECTION_HELPER_MISSING'
 $out=@(& $python -B $reader --binding (Join-Path $store 'automatic-inputs.json') --line)
 Need ($LASTEXITCODE -eq 0 -and $out.Count -eq 1 -and
       [string]$out[0] -match '^NO11_SELECTION_UI=WEEKLY  UNKNOWN') 'EMPTY_STATUS_NOT_SAFE'
 $backups=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'oneclick-selection-status-backup-*')
 Need ($backups.Count -eq 1) 'BACKUP_MISSING'
 $originalBacked=[IO.File]::ReadAllBytes((Join-Path $backups[0].FullName 'Start-No11OneClick.WHITE.before.ps1'))
 Need (([Convert]::ToBase64String($originalBacked)) -ceq
       ([Convert]::ToBase64String($before))) 'WHITE_ORIGINAL_NOT_PRESERVED'
 Need (-not (Test-Path -LiteralPath (Join-Path $store 'TRADE-2026-11-06.launch.json'))) 'CREATED_TRADE_MARKER'
 Write-Host 'NO11_SELECTION_WHITE_MOCK_INSTALL=PASS'
 Write-Host 'EXISTING_WHITE_THEME_AND_BUTTONS_PRESERVED=True'
 Write-Host 'ORIGINAL_SOURCE_BYTES_BACKED_UP=True'
 Write-Host 'NO_ORDER_STATE_CREATED=True'
}finally{
 $env:LOCALAPPDATA=$prior
 if(Test-Path -LiteralPath $sandbox -PathType Container){
  Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
 }
}
