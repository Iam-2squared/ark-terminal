# Add the verified ORIGINAL RICH ARK UI to the already-installed new Shadow.
# Do not modify old No.1.1 launcher, workbook, user edits, source tree or models.
# Copy six NEW classic-only files, then atomically repoint ONLY the new Shadow
# desktop shortcut if its previous target is precisely the verified new cmd.
param([switch]$OfflineSelfTest,[switch]$NoShortcutSwitch)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$revision='c549cb35bea6a17ff703e0858e1c79390a5a23ac'
$source='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/integration/no11-shadow-oneclick/'
$original=[ordered]@{
 'windows\Ark-Shadow-READ-ONLY.cmd'='ab861a5c31a975b0673081226b449cac75c2891d'
 'windows\Start-ArkShadowReadOnly.ps1'='4bcb50f2d56038a475052fec04d7791515605caa'
 'ui\ark_shadow_ui.py'='4a2d5f66f8ad32c47c16957904ffc86121d1d83a'
}
$new=[ordered]@{
 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'='3e955c07d114df7459a5e18ea7d3a48bd61fe829'
 'windows\Start-ArkShadowClassicReadOnly.ps1'='47fc03c7e1c9bd1ccfb1976cbbfdfdb03357e611'
 'ui\ark_shadow_classic.py'='b726c04e769bd9b094d3a7af06b10e66dbb98115'
 'ui\classic\index.html'='ec79214fcc8ad9f200d7899ee562ed11b917b686'
 'ui\classic\ark-readonly-overlay.js'='b0f27e1ad0e62b24052ce839c9eac29f934a677f'
 'ui\classic\ark-shadow-classic-bridge.js'='aa487cf742079174e058a6c3e803e24a35494277'
}
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('ARK_CLASSIC_INSTALL_'+$reason)}
}
if($OfflineSelfTest){
 Need ($revision -match '^[a-f0-9]{40}$' -and
  $new.Count -eq 6 -and $original.Count -eq 3) 'PIN_INVALID'
 Write-Host 'ARK_CLASSIC_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'ARK_CLASSIC_INSTALL_OLD_NO11_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$dest=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-oneclick-app'
$desktop=[Environment]::GetFolderPath('Desktop')
$lnk=Join-Path $desktop 'Ark Terminal Shadow READ ONLY.lnk'
$previous=Join-Path $dest 'windows\Ark-Shadow-READ-ONLY.cmd'
$classic=Join-Path $dest 'windows\Ark-Shadow-CLASSIC-READ-ONLY.cmd'
$batchRoot=Join-Path $env:TEMP ('ark-classic-stage-'+[guid]::NewGuid().ToString('N'))
$backupRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-classic-upgrade-backup'
$tmpLink=''
try{
 $git=(Get-Command git.exe -CommandType Application -ErrorAction Stop).Source
 Need (Test-Path -LiteralPath $dest -PathType Container) 'ORIGINAL_SHADOW_APP_NOT_INSTALLED'
 Need ($dest -notmatch '[\r\n"]' -and $lnk -notmatch '[\r\n"]') 'PATH_INVALID'
 [void][IO.Directory]::CreateDirectory($batchRoot)
 # Existing code must be exactly the 6-file install the user already verified.
 # Abort on any edits. Never copy/overwrite files in the ORIGINAL No.1.1 app.
 foreach($relative in $original.Keys){
  $file=Join-Path $dest $relative
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'ORIGINAL_SHADOW_FILE_MISSING'
  $actual=(& $git hash-object --no-filters $file)
  Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $original[$relative]) 'ORIGINAL_SHADOW_FILE_CHANGED'
 }
 # Verify all NEW sources before writing any app files.
 foreach($relative in $new.Keys){
  $expected=[string]$new[$relative]
  Need ($expected -match '^[a-f0-9]{40}$') 'CLASSIC_SOURCE_PIN_INVALID'
  $download=Join-Path $batchRoot $relative
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $download))
  Invoke-WebRequest -UseBasicParsing -Uri ($source+($relative.Replace('\','/'))) -OutFile $download -ErrorAction Stop
  $actual=(& $git hash-object --no-filters $download)
  Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $expected) 'CLASSIC_DOWNLOAD_HASH_MISMATCH'
 }
 foreach($relative in $new.Keys){
  $installed=Join-Path $dest $relative
  if(Test-Path -LiteralPath $installed -PathType Leaf){
   $actual=(& $git hash-object --no-filters $installed)
   Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $new[$relative]) 'CLASSIC_LOCAL_FILE_MODIFIED'
  }
 }
 # Fail before touching any shortcut if it points anywhere unexpected.
 if(-not $NoShortcutSwitch){
  Need (Test-Path -LiteralPath $lnk -PathType Leaf) 'NEW_SHADOW_SHORTCUT_MISSING'
  $shell=New-Object -ComObject WScript.Shell
  $existing=$shell.CreateShortcut($lnk)
  $target=[IO.Path]::GetFullPath([string]$existing.TargetPath)
  Need ($target.Equals([IO.Path]::GetFullPath($previous),[StringComparison]::OrdinalIgnoreCase) -or
        $target.Equals([IO.Path]::GetFullPath($classic),[StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_TARGET_NOT_OURS'
 }
 foreach($relative in $new.Keys){
  $installed=Join-Path $dest $relative
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $installed))
  if(-not (Test-Path -LiteralPath $installed -PathType Leaf)){
   [IO.File]::Copy((Join-Path $batchRoot $relative),$installed,$false)
  }
  Write-Host ('ARK_CLASSIC_INSTALLED_FILE='+$relative)
 }
 # Verify the new entrypoint without touching Excel, MarketSpeed or user data.
 $entry=Join-Path $dest 'windows\Start-ArkShadowClassicReadOnly.ps1'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $entry -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'NEW_CLASSIC_OFFLINE_SELFTEST_FAILED'
 # Import and hash-build the ORIGINAL UI with pinned Python, without opening
 # Excel, MarketSpeed or a network server. This also checks Python syntax.
 $py=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $py -PathType Leaf) 'PINNED_PYTHON_MISSING'
 $pythonCheck='import sys;sys.path.insert(0,sys.argv[1]);import ark_shadow_classic as c;data,csp=c.classic_document();assert len(data)>100000 and len(csp)>100'
 & $py -B -c $pythonCheck (Join-Path $dest 'ui')
 Need ($LASTEXITCODE -eq 0) 'PYTHON_CLASSIC_IMPORT_OR_ASSET_INVALID'
 Write-Host 'ARK_CLASSIC_PYTHON_IMPORT=PASS'
 $node=Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue
 Need ($null -ne $node) 'NODE_JS_SYNTAX_CHECK_MISSING'
 & $node.Source --check (Join-Path $dest 'ui\classic\ark-shadow-classic-bridge.js')
 Need ($LASTEXITCODE -eq 0) 'CLASSIC_BROWSER_JAVASCRIPT_SYNTAX'
 if(-not $NoShortcutSwitch){
  if(-not $target.Equals([IO.Path]::GetFullPath($classic),[StringComparison]::OrdinalIgnoreCase)){
   [void][IO.Directory]::CreateDirectory($backupRoot)
   $guid=[guid]::NewGuid().ToString('N')
   $backup=Join-Path $backupRoot ('original-shadow-shortcut-'+$guid+'.lnk')
   $tmpLink=Join-Path $backupRoot ('new-shadow-classic-'+$guid+'.lnk')
   # Backup is immutable; never delete or overwrite the original shortcut.
   [IO.File]::Copy($lnk,$backup,$false)
   $update=$shell.CreateShortcut($tmpLink)
   $update.TargetPath=$classic
   $update.WorkingDirectory=(Split-Path -Parent $classic)
   $update.Description='Original Ark Terminal rich UI + Frozen No.1.1 Shadow; READ ONLY'
   $update.Save()
   Need (Test-Path -LiteralPath $tmpLink -PathType Leaf) 'NEW_SHORTCUT_STAGING_FAILED'
   [IO.File]::Replace($tmpLink,$lnk,$null)
   Write-Host ('ARK_CLASSIC_SHORTCUT_BACKUP='+$backup)
  }
  Write-Host ('ARK_CLASSIC_SHORTCUT_TARGET='+$classic)
 }else{
  Write-Host ('ARK_CLASSIC_MANUAL_START='+$classic)
 }
 Write-Host 'ARK_CLASSIC_INSTALL_STATUS=COMPLETE'
 Write-Host 'ARK_CLASSIC_OLD_NO11_LAUNCHER_UNCHANGED=True'
 Write-Host 'ARK_CLASSIC_ORIGINAL_NEW_SHADOW_FILES_UNCHANGED=True'
 Write-Host 'ARK_CLASSIC_LAUNCH_PORT=8769'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^ARK_CLASSIC_INSTALL_[A-Z0-9_]+$'){$reason='ARK_CLASSIC_INSTALL_SOURCE_OR_IO_FAILED'}
 Write-Host ('ARK_CLASSIC_INSTALL_STATUS=BLOCKED|'+$reason)
 Write-Host 'ARK_CLASSIC_OLD_NO11_LAUNCHER_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($tmpLink -and (Test-Path -LiteralPath $tmpLink -PathType Leaf)){
  Remove-Item -LiteralPath $tmpLink -Force -ErrorAction SilentlyContinue
 }
 if(Test-Path -LiteralPath $batchRoot -PathType Container){
  Remove-Item -LiteralPath $batchRoot -Recurse -Force -ErrorAction SilentlyContinue
 }
}
