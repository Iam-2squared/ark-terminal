# Exercise the actual code-only installer on isolated mock WHITE OneClick.
# No user's Excel, no live broker, no real orders, no private account files.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$yes,[string]$label){if(-not $yes){throw ('NO11_POST1230_TEST_'+$label)}}
$originalLocal=$env:LOCALAPPDATA
$mock=Join-Path $env:TEMP ('ark-post1230-retry-ci-'+[guid]::NewGuid().ToString('N'))
$env:LOCALAPPDATA=Join-Path $mock 'fake-localappdata'
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $one=Join-Path $store 'oneclick'
 $engine=Join-Path $mock 'fake-engine'
 $windows=Join-Path $engine 'windows'
 [void][IO.Directory]::CreateDirectory($one)
 [void][IO.Directory]::CreateDirectory($windows)
 $repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
 $originalUi=Join-Path $PSScriptRoot 'Start-No11OneClick.ps1'
 $originalCapture=Join-Path $repo 'research\no12-prebuy-causal-runtime-20261011\windows\Capture-No11SessionReferenceReadOnly.ps1'
 $white=Join-Path $one 'Start-No11OneClick.ps1'
 $reference=Join-Path $windows 'Capture-No11SessionReferenceReadOnly.ps1'
 # CI branch contains the patched reference. Obtain original via pinned
 # historical commit instead, to mimic the actual installed prior state.
 $oldCommit='cbdba2cebf45c1a6dfd37c1661535c0a1da02ec4'
 $oldReferenceUrl='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$oldCommit+'/research/no12-prebuy-causal-runtime-20261011/windows/Capture-No11SessionReferenceReadOnly.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri $oldReferenceUrl -OutFile $reference
 Need ((& git hash-object --no-filters -- $reference).Trim() -ceq
       '26d2a79c912d4bfd2422bcb82562004794b50487') 'ORIGINAL_REFERENCE_MISMATCH'
 # Reproduce the actual Windows CRLF checkout that previously tripped the
 # old "hash-object --no-filters" installer despite unchanged source tokens.
 $sourceBytes=[IO.File]::ReadAllBytes($reference)
 $asString=([Text.UTF8Encoding]::new($false,$true)).GetString($sourceBytes)
 Need (-not $asString.Contains([char]13)) 'TEST_SOURCE_NOT_EXPECTED_LF'
 $windowsBytes=[Text.Encoding]::UTF8.GetBytes($asString.Replace([string][char]10,([string][char]13+[char]10)))
 [IO.File]::WriteAllBytes($reference,$windowsBytes)
 Need ((& git hash-object --no-filters -- $reference).Trim() -cne
       '26d2a79c912d4bfd2422bcb82562004794b50487') 'TEST_WINDOWS_CRLF_NOT_REPRODUCED'
 $mockUi=([IO.File]::ReadAllText($originalUi)).Replace(
  'FromArgb(29,32,38)','FromArgb(251,251,251)').Replace(
  'FromArgb(43,106,132)','FromArgb(25,90,140)')
 Need ($mockUi.Contains('FromArgb(251,251,251)')) 'FAKE_WHITE_THEME_NOT_CREATED'
 [IO.File]::WriteAllText($white,$mockUi,[Text.UTF8Encoding]::new($false))
 $whiteBefore=[IO.File]::ReadAllText($white)
 $binding=[ordered]@{
  schemaId='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
  engine=$engine
  python=(Get-Command python -ErrorAction Stop).Source
  orderTransmission=$false
 }
 $bindingFile=Join-Path $store 'automatic-inputs.json'
 [IO.File]::WriteAllText($bindingFile,(ConvertTo-Json -InputObject $binding -Compress),
                          [Text.UTF8Encoding]::new($false))
 $install=Join-Path $PSScriptRoot 'Install-No11OneClickPreorderRetry.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $install -Apply
 Need ($LASTEXITCODE -eq 0) 'ACTUAL_INSTALL_FAILED'
 $after=[IO.File]::ReadAllText($white)
 Need ($after.Contains('FromArgb(251,251,251)') -and
       $after.Contains('FromArgb(25,90,140)') -and
       $after.Contains('# ARK_NO11_ONECLICK_VERIFIED_PREORDER_RETRY_20261105') -and
       $after.Contains('RETRY START TRADING / NORMAL MAX3') -and
       $after.Contains('START TRADING   /   NORMAL MAX3') -and
       $after.Contains('CanQueuePreopen $s') -and
       $after.Contains('Review-No11RecoveryReadOnly.ps1')) 'WHITE_UI_OR_ACTIONS_BROKEN'
 Need ((& git hash-object --no-filters -- $reference).Trim() -ceq
       'f1e9739ccfb8ac520a4484d00ffccc5471264763') 'COLLECTOR_NOT_UPDATED'
 $retry=Join-Path $one 'Retry-No11OneClickPreorder.ps1'
 Need ((& git hash-object --no-filters -- $retry).Trim() -ceq
       '732d17a8b57b2f597b248f02a43839ff4b839a09') 'GUARDED_HELPER_NOT_PINNED'
 $backup=@(Get-ChildItem -LiteralPath $store -Directory -Filter 'oneclick-preorder-retry-backup-*')
 Need ($backup.Count -eq 1) 'BACKUP_NOT_CREATED'
 Need ([IO.File]::ReadAllText((Join-Path $backup[0].FullName 'Start-No11OneClick.WHITE.before.ps1')) -ceq
       $whiteBefore) 'WHITE_BACKUP_BYTES_DIFFER'
 Need (-not (Test-Path -LiteralPath (Join-Path $store 'TRADE-2026-11-05.launch.json')) -and
       -not (Test-Path -LiteralPath (Join-Path $store 'ONECLICK-RETRY-2026-11-05.claim.json'))) 'INSTALL_CREATED_TRADE_OR_CLAIM'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $retry -Mode Status | Out-Null
 Need ($LASTEXITCODE -ne 0) 'STATUS_ALLOWED_WITHOUT_REAL_APPROVAL'
 Write-Host 'NO11_POST1230_WHITE_ONECLICK_MOCK=PASS'
 Write-Host 'ORIGINAL_WHITE_THEME_PRESERVED=True'
 Write-Host 'START_BUTTON_PREORDER_RETRY_VERIFIED=True'
 Write-Host 'BROKER_TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 $env:LOCALAPPDATA=$originalLocal
 if(Test-Path -LiteralPath $mock -PathType Container){
  Remove-Item -LiteralPath $mock -Recurse -Force -ErrorAction SilentlyContinue
 }
}
