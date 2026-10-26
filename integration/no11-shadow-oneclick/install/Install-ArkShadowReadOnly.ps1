# Ark Shadow separate installer. No old shortcut/research/model/Excel is modified.
# Downloads exact verified code revisions. Local Windows PowerShell 5.1 + Git.
param([switch]$OfflineSelfTest,[switch]$NoShortcut)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$revision='1bf3aa7ad591bf0346578d69300c59932b85abbb'
$source='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/integration/no11-shadow-oneclick/'
$files=[ordered]@{
 'windows\Ark-Shadow-READ-ONLY.cmd'='ab861a5c31a975b0673081226b449cac75c2891d'
 'windows\Start-ArkShadowReadOnly.ps1'='063dd44e6c491f009bbc0aa669f72cd1af3e4572'
 'ui\ark_shadow_ui.py'='d8f9a8c032668ecc5d65a41d9b2ee694c4e9f08f'
 'ui\index.html'='c02a7168a2148dcc3b70af7eb3eac2c3e8a04309'
 'ui\app.css'='3ee513fb3d8eea877172524f81232da4104dee39'
 'ui\app.js'='d1e419ff288464fbff2f4177280807b4a740f16c'
}
function Need([bool]$yes,[string]$code){if(-not $yes){throw ('ARK_SHADOW_INSTALL_'+$code)}}
if($OfflineSelfTest){
 Need ($files.Count -eq 6 -and $revision -match '^[a-f0-9]{40}$') 'PIN_INVALID'
 Write-Host 'ARK_SHADOW_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'ARK_SHADOW_INSTALL_OLD_FILES_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$destination=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-oneclick-app'
$desktop=[Environment]::GetFolderPath('Desktop')
$icon=Join-Path $desktop 'Ark Terminal Shadow READ ONLY.lnk'
$target=Join-Path $destination 'windows\Ark-Shadow-READ-ONLY.cmd'
$temporary=Join-Path $env:TEMP ('ark-shadow-install-'+[guid]::NewGuid().ToString('N'))
try{
 $git=(Get-Command git.exe -CommandType Application -ErrorAction Stop).Source
 Need ($destination -notmatch '(?i)[\r\n"]') 'DESTINATION_INVALID'
 [void][IO.Directory]::CreateDirectory($temporary)
 # Verify all 6 remote Git blobs BEFORE writing anything to the installation.
 foreach($relative in $files.Keys){
  $expected=[string]$files[$relative]
  Need ($expected -match '^[a-f0-9]{40}$') 'SHA_INVALID'
  $download=Join-Path $temporary $relative
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $download))
  $url=$source+($relative.Replace('\','/'))
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $download -ErrorAction Stop
  $actual=(& $git hash-object --no-filters $download)
  Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $expected) 'DOWNLOAD_BLOB_MISMATCH'
 }
 # Do not overwrite local edits, even to this newly-created installer folder.
 foreach($relative in $files.Keys){
  $file=Join-Path $destination $relative
  if(Test-Path -LiteralPath $file -PathType Leaf){
   $actual=(& $git hash-object --no-filters $file)
   Need ($LASTEXITCODE -eq 0 -and ([string]$actual).Trim() -ceq $files[$relative]) 'LOCAL_FILE_MODIFIED_NO_OVERWRITE'
  }
 }
 # Existing shortcut with a different target is treated as a conflict.
 if(-not $NoShortcut -and (Test-Path -LiteralPath $icon -PathType Leaf)){
  $w=New-Object -ComObject WScript.Shell
  $current=$w.CreateShortcut($icon)
  Need (([string]$current.TargetPath).Equals($target,[StringComparison]::OrdinalIgnoreCase)) 'SHORTCUT_CONFLICT_DO_NOT_OVERWRITE'
 }
 foreach($relative in $files.Keys){
  $out=Join-Path $destination $relative
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $out))
  if(-not (Test-Path -LiteralPath $out -PathType Leaf)){
   [IO.File]::Copy((Join-Path $temporary $relative),$out,$false)
  }
  Write-Host ('ARK_SHADOW_INSTALLED_FILE='+$relative)
 }
 if(-not $NoShortcut -and -not (Test-Path -LiteralPath $icon -PathType Leaf)){
  $w=New-Object -ComObject WScript.Shell
  $shortcut=$w.CreateShortcut($icon)
  $shortcut.TargetPath=$target
  $shortcut.WorkingDirectory=(Split-Path -Parent $target)
  $shortcut.Description='ARK No.1.1 new local read-only Shadow console (orders OFF)'
  $shortcut.Save()
 }
 Write-Host ('ARK_SHADOW_NEW_SHORTCUT='+$icon)
 Write-Host ('ARK_SHADOW_INSTALL_ROOT='+$destination)
 Write-Host 'ARK_SHADOW_INSTALL_STATUS=COMPLETE'
 Write-Host 'ARK_SHADOW_OLD_LAUNCHER_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 $message=$_.Exception.Message
 if($message -notmatch '^ARK_SHADOW_INSTALL_[A-Z0-9_]+$'){$message='ARK_SHADOW_INSTALL_DOWNLOAD_OR_IO_FAILED'}
 Write-Host ('ARK_SHADOW_INSTALL_STATUS=BLOCKED|'+$message)
 Write-Host 'ARK_SHADOW_OLD_LAUNCHER_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if(Test-Path -LiteralPath $temporary -PathType Container){
  Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
 }
}
