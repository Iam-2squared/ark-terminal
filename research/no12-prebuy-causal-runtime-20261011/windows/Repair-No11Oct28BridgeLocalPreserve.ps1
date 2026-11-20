# No11 Oct28 weekly->Frozen Shadow bridge: retain ALL unknown local bootstrap edits.
# Patch only exact verified anchors, stage+parse+backup, then install atomically
# as one transaction. No Excel, market/order calls, model or evidence changes.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sourceRevision='6ad3bb0034c75456d031b4c3c1f91e7ed48b0f9f'
$patcherSha='f09cf187fcbfe0ebb84b3488d582d6b17aae794b'
$incoming=@(
 @{file='tools\no11_verified_weekly_shadow_scope.mjs';sha='7763beb8abbdf0935c96a66198ae498ef428df9b'},
 @{file='windows\Run-No11Oct28AfternoonShadowReadOnly.ps1';sha='c1d8514fa17b8169576427403dd687acbf62b5f5'}
)
function Need([bool]$yes,[string]$reason){
 if(-not $yes){throw ('NO11_OCT28_LOCAL_BRIDGE_'+$reason)}
}
function Blob([string]$filename){
 $hash=(& git hash-object --no-filters $filename)
 Need ($LASTEXITCODE -eq 0 -and $hash -is [string] -and
       $hash.Trim() -cmatch '^[0-9a-f]{40}$') 'GIT_HASH_FAILED'
 return $hash.Trim()
}
function SafePath([string]$p){
 $cursor=[IO.Path]::GetFullPath($p)
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   $item=Get-Item -LiteralPath $cursor -Force
   Need (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH_REFUSED'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break}
  $cursor=$parent
 }
}
function DownloadSource([string]$relative,[string]$sha,[string]$output){
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$sourceRevision+
  '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
 Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $output
 Need ((Blob $output) -ceq $sha) 'DOWNLOADED_SOURCE_HASH_MISMATCH'
}
if($OfflineSelfTest){
 Need ($incoming.Count -eq 2 -and $sourceRevision -cmatch '^[0-9a-f]{40}$' -and
  $patcherSha -cmatch '^[0-9a-f]{40}$') 'PINS_INVALID'
 Write-Host 'NO11_OCT28_LOCAL_BRIDGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OCT28_LOCAL_BRIDGE_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_NOT_FOUND'
 SafePath $EngineRoot
 foreach($name in @('git','node','powershell.exe')){[void](Get-Command $name -ErrorAction Stop)}
 $python=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $python -PathType Leaf) 'PYTHON_PINNED_MISSING'
 SafePath $python
 # Weekly D100 data collection may continue in Excel. Only block a concurrent
 # Shadow coordinator whose Python source is about to be patched.
 $active=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='python.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Run-No11ReceivedSessionReadOnly|Run-No11Oct28AfternoonShadowReadOnly|no11_received_session_controller|no11_received_session_bootstrap)\.(?:ps1|py)'})
 Need ($active.Count -eq 0) 'SHADOW_RUNNING_DO_NOT_PATCH'

 $original=Join-Path $EngineRoot 'tools\no11_received_session_bootstrap.py'
 Need (Test-Path -LiteralPath $original -PathType Leaf) 'ORIGINAL_BOOTSTRAP_MISSING'
 SafePath $original
 $originalSha=Blob $original
 Write-Host ('NO11_OCT28_LOCAL_BRIDGE_EXISTING_BOOTSTRAP_SHA='+$originalSha)
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct28-weekly-bridge-preserve\'+[guid]::NewGuid().ToString('N'))
 $stage=Join-Path $root 'staged';$backup=Join-Path $root 'backups'
 [void][IO.Directory]::CreateDirectory($stage)
 [void][IO.Directory]::CreateDirectory($backup)

 $patcher=Join-Path $stage 'no11_patch_weekly_bootstrap_local.py'
 DownloadSource 'tools\no11_patch_weekly_bootstrap_local.py' $patcherSha $patcher
 & $python -B -m ast $patcher | Out-Null
 Need ($LASTEXITCODE -eq 0) 'LOCAL_PATCHER_SYNTAX'
 $candidate=Join-Path $stage 'bootstrap-staged.py'
 $check=@(& $python -B $patcher --input $original --staged-output $candidate)
 $checkCode=$LASTEXITCODE
 $check|Where-Object {([string]$_) -match '^(NO11_|ORDER_TRANSMISSION=)'} |
  ForEach-Object {Write-Host $_}
 Need ($checkCode -eq 0 -and (Test-Path -LiteralPath $candidate -PathType Leaf)) 'ANCHOR_PATCH_UNAVAILABLE'
 & $python -B -m ast $candidate | Out-Null
 Need ($LASTEXITCODE -eq 0) 'PATCHED_BOOTSTRAP_SYNTAX'
 $targetSha=Blob $candidate
 $actions=@()
 if($targetSha -cne $originalSha){
  $actions+=@([pscustomobject]@{dest=$original;src=$candidate;
   sha=$targetSha;existed=$true;backup=(Join-Path $backup 'received_bootstrap.original.py')})
 }
 foreach($item in $incoming){
  $dest=Join-Path $EngineRoot $item.file
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'DESTINATION_PARENT'
  SafePath $dest
  $found=Test-Path -LiteralPath $dest -PathType Leaf
  if($found){
   $actual=Blob $dest
   Write-Host ('NO11_OCT28_LOCAL_BRIDGE_EXISTING_'+([IO.Path]::GetFileName($dest))+'='+$actual)
   Need ($actual -ceq $item.sha) 'ALREADY_EXISTING_NEW_FILE_DIVERGED'
   continue
  }
  $staged=Join-Path $stage ([IO.Path]::GetFileName($dest))
  DownloadSource $item.file $item.sha $staged
  if($staged.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $staged
   Need ($LASTEXITCODE -eq 0) 'NODE_SOURCE_SYNTAX'
  }else{
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($staged,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_SOURCE_SYNTAX'
  }
  $actions+=@([pscustomobject]@{dest=$dest;src=$staged;sha=$item.sha;
   existed=$false;backup=''})
 }
 # Entire staging phase completes before touching any installed code.
 foreach($entry in $actions){
  if($entry.existed){[IO.File]::Copy($entry.dest,$entry.backup,$false)}
 }
 $touched=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($entry in $actions){
   $touched.Add($entry)
   [IO.File]::Copy($entry.src,$entry.dest,$true)
   Need ((Blob $entry.dest) -ceq $entry.sha) 'INSTALLED_SOURCE_HASH_MISMATCH'
  }
  $wrapper=Join-Path $EngineRoot 'windows\Run-No11Oct28AfternoonShadowReadOnly.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $wrapper -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'WRAPPER_OFFLINE_SELFTEST'
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){
   $entry=$touched[$i]
   if($entry.existed){[IO.File]::Copy($entry.backup,$entry.dest,$true)}
   elseif(Test-Path -LiteralPath $entry.dest -PathType Leaf){[IO.File]::Delete($entry.dest)}
  }
  throw
 }
 Write-Host 'NO11_TODAY_BRIDGE_STAGE=PASS_LOCAL_MODIFICATIONS_PRESERVED'
 Write-Host ('NO11_TODAY_BRIDGE_BACKUPS='+$backup)
 Write-Host ('NO11_TODAY_BRIDGE_BOOTSTRAP_SHA='+$targetSha)
 Write-Host 'NO11_TODAY_BRIDGE_G1_ACTUAL=NOT_CHECKED_BY_INSTALLER'
 Write-Host 'NO11_TODAY_BRIDGE_ORIGINAL_MODELS_MODIFIED=False'
 Write-Host 'NO11_TODAY_BRIDGE_REAL_ORDERS_ALLOWED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_OCT28_LOCAL_BRIDGE_[A-Z0-9_]+$'){
  $reason='NO11_OCT28_LOCAL_BRIDGE_PRIVATE_SOURCE_OR_RUNTIME_FAILED'
 }
 Write-Host ('NO11_TODAY_BRIDGE_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
