# Pin and deploy only the REAL-ONLY UI2 read-model + UI launcher hook.
# Existing Excel, trade engine, Frozen models, Shadow and weekly RSS are untouched.
param(
 [string]$InstallRoot='C:\ArkTerminal\no11-unified-2026-10-30',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='Iam-2squared/ark-terminal'
$revision='ce66ea54ba07870d7a0600084d249ca8eb7502e4'
$installedBase='24b906e19a2623e45701311ca3fbb20dafe11c80'
$beforeLauncher='5c9e3bbe9181f514960842dcc11f420e01149bb9'
$base='research/no12-prebuy-causal-runtime-20261011/'
$files=[ordered]@{
 ($base+'tools/no11_live_ui2_readonly.py')='ee6cca7c57288b7fb77dc3a319d4bd9a7fdae9fe'
 ($base+'ui/no11_live_operations.html')='b2f77f7b57a22e0593f7a7225a594e690e50d0f3'
 ($base+'windows/Start-No11LiveUiReadOnly.ps1')='8d5bc4b120c4c8866766a43f936738d0d32d589c'
 ($base+'tests/test_no11_live_ui2_readonly.py')='6b4949c7da2ca8e30b39ae73b911fba169159822'
 ($base+'windows/Start-No11UnifiedLauncher.ps1')='c169b95c4026c3d23665b8ae45887b8ebcc91bbd'
}
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_UI2_INSTALL_'+$reason)}}
function Blob([string]$file){
 $v=@(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $v.Count -eq 1) 'GIT_BLOB_FAILED'
 return [string]$v[0]
}
if($OfflineSelfTest){
 Need ($revision -cmatch '^[0-9a-f]{40}$' -and
       $beforeLauncher -cmatch '^[0-9a-f]{40}$' -and
       $files.Count -eq 5 -and
       (@($files.Values | Where-Object {$_ -cnotmatch '^[0-9a-f]{40}$'}).Count -eq 0)) 'PINS_INVALID'
 Write-Host 'NO11_UI2_LIVE_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_UI2_ORDER_PERMISSION_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$tmpDir=''
$backup=''
$created=@()
$launcherChanged=$false
try{
 [void](Get-Command git -ErrorAction Stop)
 Need (Test-Path -LiteralPath $InstallRoot -PathType Container) 'INSTALL_ROOT_MISSING'
 $root=[IO.Path]::GetFullPath($InstallRoot)
 $head=([string](& git -C $root rev-parse HEAD)).Trim()
 Need ($LASTEXITCODE -eq 0 -and $head -ceq $installedBase) 'PINNED_INSTALL_ROOT_CHANGED'
 $launcher=Join-Path $root ($base+'windows/Start-No11UnifiedLauncher.ps1')
 Need (Test-Path -LiteralPath $launcher -PathType Leaf) 'OLD_LAUNCHER_MISSING'
 $current=Blob $launcher
 Need ($current -ceq $beforeLauncher) 'LOCAL_LAUNCHER_CHANGED_REVIEW_REQUIRED'
 foreach($entry in $files.GetEnumerator()){
  $dest=Join-Path $root $entry.Key
  if(Test-Path -LiteralPath $dest -PathType Leaf){
   Need ($entry.Key -ceq ($base+'windows/Start-No11UnifiedLauncher.ps1') -or
         ((Blob $dest) -ceq [string]$entry.Value)) 'EXISTING_UI_SOURCE_CONFLICT'
  }
 }
 $tmpDir=Join-Path $env:TEMP ('ArkNo11LiveUi-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($tmpDir)
 $staged=@{}
 $n=0
 foreach($entry in $files.GetEnumerator()){
  $n++
  $tmp=Join-Path $tmpDir ('file-'+$n)
  $url='https://raw.githubusercontent.com/'+$repo+'/'+$revision+'/'+$entry.Key
  Invoke-WebRequest -Uri $url -UseBasicParsing -OutFile $tmp
  Need ((Blob $tmp) -ceq [string]$entry.Value) 'SOURCE_HASH_MISMATCH'
  $staged[$entry.Key]=$tmp
 }
 $python=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $python -PathType Leaf) 'VERIFIED_PYTHON_MISSING'
 $backups=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\backups'
 [void][IO.Directory]::CreateDirectory($backups)
 $backup=Join-Path $backups ('Start-No11UnifiedLauncher.pre-ui2-'+[guid]::NewGuid().ToString('N')+'.ps1')
 [IO.File]::Copy($launcher,$backup,$false)
 foreach($entry in $files.GetEnumerator()){
  $dest=Join-Path $root $entry.Key
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $dest))
  if($dest -ieq $launcher){
   [IO.File]::Copy([string]$staged[$entry.Key],$dest,$true)
   $launcherChanged=$true
  }elseif(-not (Test-Path -LiteralPath $dest -PathType Leaf)){
   [IO.File]::Copy([string]$staged[$entry.Key],$dest,$false)
   $created+=@($dest)
  }
  Need ((Blob $dest) -ceq [string]$entry.Value) 'INSTALLED_HASH_MISMATCH'
 }
 $engine=Join-Path $root $base
 & $python -B (Join-Path $engine 'tools/no11_live_ui2_readonly.py') --offline-selftest
 Need ($LASTEXITCODE -eq 0) 'PYTHON_SELFTEST_FAILED'
 & $python -B -m unittest discover -s (Join-Path $engine 'tests') -p 'test_no11_live_ui2_readonly.py' -v
 Need ($LASTEXITCODE -eq 0) 'READONLY_UI_UNIT_TESTS_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $engine 'windows/Start-No11LiveUiReadOnly.ps1') -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'UI_WINDOWS_SELFTEST_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $engine 'windows/Start-No11UnifiedLauncher.ps1') -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'LAUNCHER_WINDOWS_SELFTEST_FAILED'
 Write-Host 'NO11_UI2_LIVE_INSTALL=PASS_READONLY_UI_AUTOLAUNCH_STAGED'
 Write-Host 'NO11_UI2_FROZEN_ORIGINAL_MODIFIED=False'
 Write-Host 'NO11_UI2_SHADOW_REPORTS_INCLUDED=False'
 Write-Host 'NO11_UI2_WEEKLY_RSS_PROCESS_TOUCHED=False'
 Write-Host 'NO11_UI2_REAL_BROKER_ORDER_VERIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}catch{
 if($launcherChanged -and $backup -and (Test-Path -LiteralPath $backup)){
  [IO.File]::Copy($backup,$launcher,$true)
 }
 foreach($file in $created){
  if(Test-Path -LiteralPath $file -PathType Leaf){Remove-Item -LiteralPath $file -Force}
 }
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_UI2_INSTALL_[A-Z0-9_]+$'){$reason='NO11_UI2_INSTALL_DOWNLOAD_OR_IO_FAILURE'}
 Write-Host ('NO11_UI2_LIVE_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($tmpDir -and (Test-Path -LiteralPath $tmpDir -PathType Container)){
  Remove-Item -LiteralPath $tmpDir -Recurse -Force
 }
}
