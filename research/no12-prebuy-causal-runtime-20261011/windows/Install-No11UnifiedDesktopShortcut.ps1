# Installs a NEW unified desktop launcher shortcut; never touches legacy icons.
param([switch]$OfflineSelfTest,[string]$ShortcutName='Ark Terminal No11 Normal + Weekly.lnk')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$runner=Join-Path $PSScriptRoot 'Start-No11UnifiedLauncher.ps1'
$weekly=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'
$live=Join-Path $PSScriptRoot 'Run-No11ReceivedSessionOperatorLive.ps1'
$desktop=[Environment]::GetFolderPath('Desktop')
$shortcut=Join-Path $desktop $ShortcutName
$exe=Join-Path $PSHOME 'powershell.exe'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_UNIFIED_INSTALL_'+$reason)}
}
if($OfflineSelfTest){
 Need ($ShortcutName -ceq 'Ark Terminal No11 Normal + Weekly.lnk' -and
       (Test-Path -LiteralPath $runner -PathType Leaf) -and
       (Test-Path -LiteralPath $weekly -PathType Leaf) -and
       (Test-Path -LiteralPath $live -PathType Leaf)) 'OFFLINE_SOURCE_FILES'
 Write-Host 'NO11_UNIFIED_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_UNIFIED_INSTALL_OLD_LAUNCHERS_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need ($ShortcutName -cmatch '^[A-Za-z0-9 +_-]{1,100}\.lnk$') 'SHORTCUT_NAME'
 Need (Test-Path -LiteralPath $desktop -PathType Container) 'DESKTOP_REQUIRED'
 foreach($file in @($runner,$weekly,$live,$exe)){
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'RUNTIME_FILE_NOT_INSTALLED'
 }
 $args='-NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "'+$runner+'"'
 $com=New-Object -ComObject WScript.Shell
 if(Test-Path -LiteralPath $shortcut -PathType Leaf){
  $existing=$com.CreateShortcut($shortcut)
  Need ([IO.Path]::GetFullPath([string]$existing.TargetPath).Equals(
        [IO.Path]::GetFullPath($exe),
        [StringComparison]::OrdinalIgnoreCase) -and
        [string]$existing.Arguments -ceq $args) 'FOREIGN_DESKTOP_SHORTCUT_WONT_OVERWRITE'
  Write-Host 'NO11_UNIFIED_INSTALL=ALREADY_INSTALLED'
 }else{
  $icon=$com.CreateShortcut($shortcut)
  $icon.TargetPath=$exe
  $icon.Arguments=$args
  $icon.WorkingDirectory=$PSScriptRoot
  $icon.Description='Ark Terminal No11 NORMAL MAX3 (daily approval) and weekly RSS'
  $icon.IconLocation=$exe+',0'
  $icon.Save()
  Need (Test-Path -LiteralPath $shortcut -PathType Leaf) 'SHORTCUT_CREATE_FAILED'
  Write-Host 'NO11_UNIFIED_INSTALL=DESKTOP_SHORTCUT_CREATED'
 }
 Write-Host ('NO11_UNIFIED_INSTALL_SHORTCUT='+$shortcut)
 Write-Host 'NO11_UNIFIED_INSTALL_LIVE_ORDER_PERMISSION=NOT_GRANTED'
 Write-Host 'NO11_UNIFIED_INSTALL_OLD_LAUNCHERS_UNCHANGED=True'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_UNIFIED_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_UNIFIED_INSTALL_WINDOWS_OR_SOURCE_FAILURE'
 }
 Write-Host ('NO11_UNIFIED_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}