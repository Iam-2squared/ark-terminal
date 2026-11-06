# Fix Ark No.1.1 CLASSIC one-click startup after failed status-file republish.
# This installer is additive: only adds two NEW V2 launcher files and updates
# the previously-created CLASSIC shortcut (with backup). Does not touch the
# original No.1.1 icon, former new Shadow icon, Excel, registry, RSS, model, data.
param([switch]$OfflineSelfTest,[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$revision='85c6a51880c73e4711e9535a09bc713132f2ebf0'
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/integration/no11-shadow-oneclick/windows/'
$required=[ordered]@{
 'windows\Ark-Shadow-READ-ONLY.cmd'='ab861a5c31a975b0673081226b449cac75c2891d'
 'windows\Start-ArkShadowReadOnly.ps1'='4bcb50f2d56038a475052fec04d7791515605caa'
 'ui\ark_shadow_ui.py'='4a2d5f66f8ad32c47c16957904ffc86121d1d83a'
 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'='3e955c07d114df7459a5e18ea7d3a48bd61fe829'
 'windows\Start-ArkShadowClassicReadOnly.ps1'='47fc03c7e1c9bd1ccfb1976cbbfdfdb03357e611'
 'ui\ark_shadow_classic.py'='b726c04e769bd9b094d3a7af06b10e66dbb98115'
 'ui\classic\index.html'='ec79214fcc8ad9f200d7899ee562ed11b917b686'
 'ui\classic\ark-readonly-overlay.js'='b0f27e1ad0e62b24052ce839c9eac29f934a677f'
 'ui\classic\ark-shadow-classic-bridge.js'='aa487cf742079174e058a6c3e803e24a35494277'
}
# Source file names are different from new local names by design.
$new=[ordered]@{
 'windows\Start-ArkShadowClassicReadOnly-V2.ps1'=[ordered]@{
  remote='Start-ArkShadowClassicReadOnly.ps1';sha='a53c23e983fb39840eda0f874332b169256addd0'}
 'windows\Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd'=[ordered]@{
  remote='Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd';sha='77a3a4ba8fb2875dc3aa838417a47578e42689eb'}
}
function Need([bool]$value,[string]$reason){
 if(-not $value){throw ('ARK_CLASSIC_V2_'+$reason)}
}
$step='ENTRY'
function Stage([string]$name){
 $script:step=$name
 Write-Host ('ARK_CLASSIC_V2_STAGE='+$name)
}
if($OfflineSelfTest){
 Need ($required.Count -eq 9 -and $new.Count -eq 2 -and
  $revision -match '^[a-f0-9]{40}$') 'SELFTEST_PINS'
 Write-Host 'ARK_CLASSIC_V2_INSTALLER_OFFLINE_SELFTEST=PASS'
 Write-Host 'ARK_CLASSIC_V2_EXISTING_FILES_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$dest=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-oneclick-app'
$icon=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark Terminal Classic Shadow READ ONLY.lnk'
$prior=Join-Path $dest 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'
$target=Join-Path $dest 'windows\Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd'
$staging=Join-Path $env:TEMP ('ark-classic-v2-'+[guid]::NewGuid().ToString('N'))
$backupDir=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-classic-upgrade-backup'
$shortcutBackup=''
$changeAttempted=$false
try{
 Stage 'VERIFY_NINE_ORIGINAL_BLOBS'
 Need (Test-Path -LiteralPath $dest -PathType Container) 'PREVIOUS_APP_MISSING'
 $git=(Get-Command git.exe -CommandType Application -ErrorAction Stop).Source
 foreach($relative in $required.Keys){
  $existing=Join-Path $dest $relative
  Need (Test-Path -LiteralPath $existing -PathType Leaf) 'REQUIRED_FILE_MISSING'
  $current=(& $git hash-object --no-filters $existing)
  Need ($LASTEXITCODE -eq 0 -and ([string]$current).Trim() -ceq [string]$required[$relative]) 'EXISTING_LOCAL_FILE_CHANGED'
 }
 Write-Host 'ARK_CLASSIC_V2_NINE_ORIGINAL_BLOBS=PASS'

 Stage 'VERIFY_CLASSIC_SHORTCUT_OWNERSHIP'
 Need (Test-Path -LiteralPath $icon -PathType Leaf) 'CLASSIC_ICON_MISSING'
 $shell=New-Object -ComObject WScript.Shell
 $link=$shell.CreateShortcut($icon)
 $linkTarget=[string]$link.TargetPath
 Need (-not [string]::IsNullOrWhiteSpace($linkTarget)) 'SHORTCUT_EMPTY'
 $originalTarget=[IO.Path]::GetFullPath($prior)
 $newTarget=[IO.Path]::GetFullPath($target)
 $currentTarget=[IO.Path]::GetFullPath($linkTarget)
 Need ($currentTarget.Equals($originalTarget,[StringComparison]::OrdinalIgnoreCase) -or
   $currentTarget.Equals($newTarget,[StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_NOT_OUR_CLASSIC_ICON'
 
 Stage 'DOWNLOAD_VERIFY_NEW_V2'
 [void][IO.Directory]::CreateDirectory($staging)
 foreach($relative in $new.Keys){
  $part=$new[$relative]
  $remote=[string]$part['remote'];$expected=[string]$part['sha']
  Need ($expected -match '^[a-f0-9]{40}$') 'V2_PIN_INVALID'
  $temp=Join-Path $staging $remote
  Invoke-WebRequest -UseBasicParsing -Uri ($base+$remote) -OutFile $temp -ErrorAction Stop
  $actual=(& $git hash-object --no-filters $temp)
  Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $expected) 'V2_SOURCE_BLOB_MISMATCH'
 }
 Stage 'INSTALL_NEW_FILES_NO_OVERWRITE'
 foreach($relative in $new.Keys){
  $part=$new[$relative]
  $installed=Join-Path $dest $relative
  if(Test-Path -LiteralPath $installed -PathType Leaf){
   $actual=(& $git hash-object --no-filters $installed)
   Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq [string]$part['sha']) 'V2_LOCAL_MODIFIED_NO_OVERWRITE'
  }else{
   [IO.File]::Copy((Join-Path $staging ([string]$part['remote'])),$installed,$false)
  }
  Write-Host ('ARK_CLASSIC_V2_FILE='+$relative)
 }
 Stage 'PARSER_AND_DOUBLE_PUBLISH_SELFTEST'
 $script=Join-Path $dest 'windows\Start-ArkShadowClassicReadOnly-V2.ps1'
 $tokens=$null;$parseErrors=$null
 [void][System.Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$parseErrors)
 Need ($parseErrors.Count -eq 0) 'WINDOWS_PS5_PARSE_ERROR'
 $selfOutput=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -OfflineSelfTest)
 $selfCode=$LASTEXITCODE
 foreach($l in $selfOutput){if(([string]$l) -like 'ARK_SHADOW_*'){Write-Host $l}}
 Need ($selfCode -eq 0 -and
  @($selfOutput|Where-Object {$_ -ceq 'ARK_SHADOW_STATUS_REPUBLISH_SELFTEST=PASS'}).Count -eq 1 -and
  @($selfOutput|Where-Object {$_ -ceq 'ARK_SHADOW_OFFLINE_SELFTEST=PASS'}).Count -eq 1) 'DOUBLE_PUBLISH_OFFLINE_SELFTEST_FAILED'
 Write-Host 'ARK_CLASSIC_V2_ATOMIC_STATUS_TEST=PASS'

 Stage 'TEST_NEW_V2_CMD_HASH'
 $v2cmd=Join-Path $dest 'windows\Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd'
 $v2sha=(& $git hash-object --no-filters $v2cmd)
 Need ($LASTEXITCODE -eq 0 -and ([string]$v2sha).Trim() -ceq
   [string]$new['windows\Ark-Shadow-CLASSIC-V2-READ-ONLY.cmd']['sha']) 'V2_CMD_INVALID'
 if($VerifyOnly){
  Write-Host 'ARK_CLASSIC_V2_STATUS=VERIFIED_NO_ICON_CHANGE'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Stage 'BACKUP_AND_UPDATE_ONLY_CLASSIC_SHORTCUT'
 [void][IO.Directory]::CreateDirectory($backupDir)
 if(-not $currentTarget.Equals($newTarget,[StringComparison]::OrdinalIgnoreCase)){
  $shortcutBackup=Join-Path $backupDir ('classic-pre-v2-'+[guid]::NewGuid().ToString('N')+'.lnk')
  [IO.File]::Copy($icon,$shortcutBackup,$false)
  $changeAttempted=$true
  $link.TargetPath=$target
  $link.WorkingDirectory=(Split-Path -Parent $target)
  $link.Description='ARK original rich UI / Frozen Shadow / READ ONLY V2'
  $link.Save()
  Write-Host ('ARK_CLASSIC_V2_SHORTCUT_BACKUP='+$shortcutBackup)
 }
 $check=$shell.CreateShortcut($icon)
 Need ([IO.Path]::GetFullPath([string]$check.TargetPath).Equals(
   $newTarget,[StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_POSTVERIFY_FAILED'
 Write-Host 'ARK_CLASSIC_V2_STATUS=COMPLETE'
 Write-Host 'ARK_CLASSIC_V2_LAUNCH_PORT=8769'
 Write-Host 'ARK_CLASSIC_V2_OLD_NO11_UNCHANGED=True'
 Write-Host 'ARK_CLASSIC_V2_OLD_SHADOW_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -notmatch '^ARK_CLASSIC_V2_[A-Z0-9_]+$'){
  $reason='ARK_CLASSIC_V2_UNEXPECTED_'+$step
 }
 # If shortcut was modified but post-check failed, restore its exact backup.
 if($changeAttempted -and $shortcutBackup -and
    (Test-Path -LiteralPath $shortcutBackup -PathType Leaf)){
  try{[IO.File]::Copy($shortcutBackup,$icon,$true)
    Write-Host 'ARK_CLASSIC_V2_SHORTCUT_RESTORED_FROM_BACKUP=True'
  }catch{Write-Host 'ARK_CLASSIC_V2_SHORTCUT_RESTORE=UNCONFIRMED'}
 }
 Write-Host ('ARK_CLASSIC_V2_STATUS=BLOCKED|'+$reason)
 Write-Host ('ARK_CLASSIC_V2_FAILED_STAGE='+$step)
 Write-Host ('ARK_CLASSIC_V2_ERROR_TYPE='+$_.Exception.GetType().Name)
 Write-Host 'ARK_CLASSIC_V2_OLD_NO11_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if(Test-Path -LiteralPath $staging -PathType Container){
  Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
 }
}
