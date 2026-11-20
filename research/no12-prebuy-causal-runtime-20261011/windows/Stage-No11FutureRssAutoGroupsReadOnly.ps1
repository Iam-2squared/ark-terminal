# One-time AFTER TODAY ONLY: install future regular weekday RSS auto-groups.
# Does not touch the October 28 catch-up script, workbook, market data, models,
# brokerage, scheduling state or orders. Strict old/new Git blob whitelist.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='2d554264c62001bbc7bb07fbcf86812cc52e586f'
$files=@(
 @{
  relative='windows\Run-No11WeeklyCandidateRefreshReadOnly.ps1';
  accepted=@('b4dfbc4556e3cc54002d5d16c62f465b4f463975',
             'f31862730426795e1138d922719fe85b5f72a2b7',
             '78eee12cefa77abb37ec3f442c21efe3ca1ed7f2',
             '9b2d6f4e5876c1692406f4a2dcff3000dbd515b3');
  target='9b2d6f4e5876c1692406f4a2dcff3000dbd515b3'
 },
 @{
  relative='windows\Prepare-No11WeeklyAfterCloseReadOnly.ps1';
  accepted=@('15204f78a9b03f1db9094072597f0243b7991ece',
             '563e5a0894b643124fdf1ace0b60fe3e25048b5c',
             '3b18343f05043108af328863aa02fde5f8428a19');
  target='3b18343f05043108af328863aa02fde5f8428a19'
 }
)
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_RSS_AUTOGROUP_INSTALL_'+$reason)}
}
function Blob([string]$file){
 $value=(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and $value -is [string] -and
  $value.Trim() -cmatch '^[a-f0-9]{40}$') 'GIT_HASH_UNAVAILABLE'
 return $value.Trim()
}
function SafePath([string]$path){
 $item=[IO.Path]::GetFullPath($path)
 while(-not [string]::IsNullOrEmpty($item)){
  if(Test-Path -LiteralPath $item){
   Need (((Get-Item -LiteralPath $item -Force).Attributes -band
      [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_SOURCE_FORBIDDEN'
  }
  $parent=Split-Path -Parent $item
  if($parent -ceq $item){break}
  $item=$parent
 }
}
if($OfflineSelfTest){
 Need ($files.Count -eq 2) 'CONFIG_COUNT'
 foreach($entry in $files){
  Need ([string]$entry.target -cmatch '^[a-f0-9]{40}$' -and
   $entry.target -in $entry.accepted) 'SOURCE_PINS'
 }
 Write-Host 'NO11_RSS_AUTOGROUP_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_RSS_AUTOGROUP_INSTALL_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_ROOT_REQUIRED'
 SafePath $EngineRoot
 foreach($n in @('git','powershell.exe')){[void](Get-Command $n -ErrorAction Stop)}
 # Any earlier catch-up or after-close Excel script must terminate normally
 # before replacing a source file. Do NOT kill or close the user's Excel.
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop|
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Run-No11WeeklyCandidateRefreshReadOnly|Prepare-No11WeeklyAfterCloseReadOnly|Run-No11Oct28CatchUpReadOnly|Run-No11WeeklyCandidateCatchUpReadOnly)\.ps1'})
 Need ($busy.Count -eq 0) 'COLLECTOR_STILL_RUNNING_FINISH_TODAY_FIRST'

 $job=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\future-autogroup-install\'+[guid]::NewGuid().ToString('N'))
 $stage=Join-Path $job 'stage';$backups=Join-Path $job 'backups'
 [void][IO.Directory]::CreateDirectory($stage)
 [void][IO.Directory]::CreateDirectory($backups)
 $changes=@()
 foreach($file in $files){
  $source=Join-Path $EngineRoot ([string]$file.relative)
  SafePath $source
  Need (Test-Path -LiteralPath $source -PathType Leaf) 'EXISTING_SOURCE_MISSING'
  $actual=Blob $source
  Write-Host ('NO11_RSS_AUTOGROUP_LOCAL_SHA_'+[IO.Path]::GetFileName($source)+'='+$actual)
  Need ($actual -in $file.accepted) 'LOCAL_SOURCE_DIVERGED_INSPECT_FIRST'
  if($actual -ceq $file.target){continue}
  $candidate=Join-Path $stage ([IO.Path]::GetFileName($source))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
   '/research/no12-prebuy-causal-runtime-20261011/'+([string]$file.relative).Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $candidate
  Need ((Blob $candidate) -ceq $file.target) 'PINNED_DOWNLOAD_HASH_FAILED'
  $tokens=$null;$errors=$null
  [void][Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tokens,[ref]$errors)
  Need ($errors.Count -eq 0) 'POWERSHELL_SOURCE_PARSE'
  if($source.EndsWith('Run-No11WeeklyCandidateRefreshReadOnly.ps1',
      [StringComparison]::OrdinalIgnoreCase)){
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest
   Need ($LASTEXITCODE -eq 0) 'CANDIDATE_OFFLINE_SELFTEST'
  }
  $changes+=@([pscustomobject]@{src=$source;candidate=$candidate;expected=$file.target;
     backup=(Join-Path $backups ([IO.Path]::GetFileName($source)+'.bak'))})
 }
 foreach($file in $changes){[IO.File]::Copy($file.src,$file.backup,$false)}
 $applied=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($file in $changes){
   $applied.Add($file)
   [IO.File]::Copy($file.candidate,$file.src,$true)
   Need ((Blob $file.src) -ceq $file.expected) 'INSTALLED_HASH_CHANGED'
  }
  foreach($file in $files){
   $dest=Join-Path $EngineRoot ([string]$file.relative)
   Need ((Blob $dest) -ceq $file.target) 'TARGET_FILES_NOT_PINNED'
  }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (
   Join-Path $EngineRoot 'windows\Run-No11WeeklyCandidateRefreshReadOnly.ps1') -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'INSTALLED_OFFLINE_SELFTEST'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (
   Join-Path $EngineRoot 'windows\Prepare-No11WeeklyAfterCloseReadOnly.ps1') -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'INSTALLED_NIGHTLY_OFFLINE_SELFTEST'
 }catch{
  for($i=$applied.Count-1;$i -ge 0;$i--){
   $file=$applied[$i]
   [IO.File]::Copy($file.backup,$file.src,$true)
  }
  throw
 }
 Write-Host 'NO11_RSS_AUTOGROUP_INSTALL=PASS'
 Write-Host ('NO11_RSS_AUTOGROUP_BACKUPS='+$backups)
 Write-Host 'NO11_RSS_AUTOGROUP_DEFAULT=100_SYMBOL_GROUPS_30_PHYSICAL_MAX'
 Write-Host 'NO11_RSS_AUTOGROUP_CHART_FUNCTIONS=MAX50_WITH_3_RESERVED'
 Write-Host 'NO11_RSS_AUTOGROUP_TODAY_SOURCE_MODIFIED=False'
 Write-Host 'NO11_RSS_AUTOGROUP_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_RSS_AUTOGROUP_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_RSS_AUTOGROUP_INSTALL_SOURCE_OR_RUNTIME_FAILED'
 }
 Write-Host ('NO11_RSS_AUTOGROUP_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
