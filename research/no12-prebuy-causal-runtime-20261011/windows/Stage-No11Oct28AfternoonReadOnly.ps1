# Install only the Oct28 same-day read-only weekly->Frozen Shadow bridge.
# Existing bootstrap gets a byte-pinned backup; no original models/Excel/orders.
param([string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
      [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='298d3c2640547956836c0a5a9ace642cff7ebcb1'
$files=@(
 @{relative='tools\no11_received_session_bootstrap.py';before='ebb8a025294faecd32d5717c41719a767a94c700';after='35cdeedc9151fcb57fde32c6373331afea43f05b'},
 @{relative='tools\no11_verified_weekly_shadow_scope.mjs';before='';after='7763beb8abbdf0935c96a66198ae498ef428df9b'},
 @{relative='windows\Run-No11Oct28AfternoonShadowReadOnly.ps1';before='';after='c1d8514fa17b8169576427403dd687acbf62b5f5'}
)
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_TODAY_STAGE_'+$code)}}
function Hash([string]$p){
 $out=(& git hash-object --no-filters $p)
 Need ($LASTEXITCODE -eq 0 -and $out -is [string] -and $out.Trim() -cmatch '^[a-f0-9]{40}$') 'HASH_UNAVAILABLE'
 return $out.Trim()
}
function Safe([string]$p){
 $cursor=[IO.Path]::GetFullPath($p)
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $next=Split-Path -Parent $cursor;if($next -ceq $cursor){break};$cursor=$next
 }
}
if($OfflineSelfTest){
 Need ($files.Count -eq 3 -and $revision -cmatch '^[a-f0-9]{40}$') 'SELFTEST_CONTRACT'
 foreach($f in $files){Need ([string]$f.after -cmatch '^[a-f0-9]{40}$') 'PIN'}
 Write-Host 'NO11_TODAY_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_TODAY_STAGE_EXCEL_OPENED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_NOT_FOUND'
 Safe $EngineRoot
 foreach($exe in @('git','node','powershell.exe')){[void](Get-Command $exe -ErrorAction Stop)}
 $python=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $python -PathType Leaf) 'PYTHON_NOT_INSTALLED'
 $active=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='python.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Run-No11ReceivedSessionReadOnly|no11_received_session_controller|no11_received_session_bootstrap|Run-No11Oct28AfternoonShadowReadOnly)\.(?:ps1|py)'})
 Need ($active.Count -eq 0) 'ORIGINAL_SHADOW_IS_RUNNING'
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct28-afternoon-bridge\'+[guid]::NewGuid().ToString('N'))
 $stage=Join-Path $root 'stage';$backups=Join-Path $root 'backups'
 [void][IO.Directory]::CreateDirectory($stage)
 [void][IO.Directory]::CreateDirectory($backups)
 $changes=@()
 foreach($item in $files){
  $relative=[string]$item.relative;$dest=Join-Path $EngineRoot $relative
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'DEST_PARENT_NOT_FOUND'
  Safe $dest
  $present=Test-Path -LiteralPath $dest -PathType Leaf
  $old=if($present){Hash $dest}else{''}
  if($present){
   Need ($old -ceq $item.before -or $old -ceq $item.after) 'LOCAL_SOURCE_DIVERGED_INSPECT_FIRST'
  }else{
   Need (-not [string]::IsNullOrWhiteSpace([string]$item.after) -and
        [string]::IsNullOrWhiteSpace([string]$item.before)) 'REQUIRED_OLD_FILE_MISSING'
  }
  if($old -ceq $item.after){continue}
  $staged=Join-Path $stage ($relative.Replace('\','_'))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
   '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $staged
  Need ((Hash $staged) -ceq $item.after) 'STAGED_GIT_BLOB_MISMATCH'
  if($staged.EndsWith('.py',[StringComparison]::OrdinalIgnoreCase)){
   & $python -B -m ast $staged | Out-Null
   Need ($LASTEXITCODE -eq 0) 'PYTHON_SOURCE_PARSE'
  }elseif($staged.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $staged
   Need ($LASTEXITCODE -eq 0) 'NODE_SOURCE_PARSE'
  }else{
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($staged,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_SOURCE_PARSE'
  }
  $changes+=@([pscustomobject]@{dest=$dest;src=$staged;expected=$item.after;
    present=$present;backup=(Join-Path $backups ($relative.Replace('\','_')+'.bak'))})
 }
 foreach($item in $changes){
  if($item.present){[IO.File]::Copy($item.dest,$item.backup,$false)}
 }
 $done=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($item in $changes){
   $done.Add($item)
   [IO.File]::Copy($item.src,$item.dest,$true)
   Need ((Hash $item.dest) -ceq $item.expected) 'INSTALLED_HASH_MISMATCH'
  }
  foreach($name in @('Run-No11Oct28AfternoonShadowReadOnly.ps1')){
   $test=Join-Path $EngineRoot ('windows\'+$name)
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $test -OfflineSelfTest
   Need ($LASTEXITCODE -eq 0) 'AFTER_INSTALL_SELFTEST'
  }
 }catch{
  for($i=$done.Count-1;$i -ge 0;$i--){
   $item=$done[$i]
   if($item.present){[IO.File]::Copy($item.backup,$item.dest,$true)}
   elseif(Test-Path -LiteralPath $item.dest -PathType Leaf){Remove-Item -LiteralPath $item.dest -Force}
  }
  throw
 }
 Write-Host 'NO11_TODAY_BRIDGE_STAGE=PASS'
 Write-Host ('NO11_TODAY_BRIDGE_BACKUPS='+$backups)
 Write-Host 'NO11_TODAY_BRIDGE_SESSION=2026-10-28'
 Write-Host 'NO11_TODAY_BRIDGE_ORIGINAL_FROZEN_CHANGED=False'
 Write-Host 'NO11_TODAY_BRIDGE_SOURCE_PREFLIGHT=NOT_YET_RUN'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $message=$_.Exception.Message
 if($message -cnotmatch '^NO11_TODAY_STAGE_[A-Z0-9_]+$'){$message='NO11_TODAY_STAGE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_TODAY_BRIDGE_STAGE=BLOCKED|'+$message)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
