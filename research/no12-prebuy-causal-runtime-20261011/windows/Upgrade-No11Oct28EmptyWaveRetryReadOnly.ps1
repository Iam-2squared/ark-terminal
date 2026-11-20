# Optional bounded RSS empty-wave retry upgrade; NOT a trading entry point.
# Call only after prior batch stopped; never edit a running Excel collector.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='1a7e134910cb07485f6df82b05806af09299931f'
$old='1c81294e8542043b1208c71d78e4583921088394'
$updated='bd8df4a0f40e0f2eafdf60958b9e1d63571eefb7'
$relative='windows\Run-No11WeeklyCandidateCatchUpReadOnly.ps1'
function Need([bool]$valid,[string]$code){if(-not $valid){throw ('NO11_EMPTY_RETRY_UPGRADE_'+$code)}}
function Digest([string]$file){
 $out=(& git hash-object --no-filters $file)
 Need ($LASTEXITCODE -eq 0 -and [string]$out -cmatch '^[0-9a-f]{40}$') 'GIT_BLOB_UNAVAILABLE'
 return ([string]$out).Trim()
}
function Safe([string]$target){
 $p=[IO.Path]::GetFullPath($target)
 while(-not [string]::IsNullOrWhiteSpace($p)){
  if(Test-Path -LiteralPath $p){
   Need (((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $q=Split-Path -Parent $p
  if($q -ceq $p){break}
  $p=$q
 }
}
if($OfflineSelfTest){
 Need ($revision -cmatch '^[0-9a-f]{40}$' -and $old -cmatch '^[0-9a-f]{40}$' -and
  $updated -cmatch '^[0-9a-f]{40}$') 'INVALID_PINS'
 Write-Host 'NO11_EMPTY_RETRY_UPGRADE_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_NOT_FOUND'
 Safe $EngineRoot
 [void](Get-Command git -ErrorAction Stop)
 $destination=Join-Path $EngineRoot $relative
 Safe $destination
 Need (Test-Path -LiteralPath $destination -PathType Leaf) 'COLLECTOR_NOT_INSTALLED'
 $running=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Run-No11Oct28CatchUpReadOnly|Run-No11WeeklyCandidateCatchUpReadOnly)\.ps1'})
 Need ($running.Count -eq 0) 'RUNNING_COLLECTOR_MUST_FINISH'
 $existing=Digest $destination
 Need ($existing -ceq $old -or $existing -ceq $updated) 'LOCAL_COLLECTOR_SOURCE_DIVERGED'
 if($existing -ceq $updated){
  Write-Host 'NO11_EMPTY_RETRY_UPGRADE=ALREADY_PRESENT'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $folder=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct28-empty-wave-retry\'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($folder)
 $tmp=Join-Path $folder 'Run-No11WeeklyCandidateCatchUpReadOnly.ps1'
 $backup=Join-Path $folder 'original-catchup-collector.bak'
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
  '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
 Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
 Need ((Digest $tmp) -ceq $updated) 'DOWNLOADED_SOURCE_HASH_MISMATCH'
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($tmp,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'SOURCE_POWERSHELL_PARSE_FAILED'
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $tmp -OfflineSelfTest
 Need ($LASTEXITCODE -eq 0) 'SOURCE_OFFLINE_SELFTEST_FAILED'
 [IO.File]::Copy($destination,$backup,$false)
 try{
  [IO.File]::Copy($tmp,$destination,$true)
  Need ((Digest $destination) -ceq $updated) 'POST_INSTALL_HASH_MISMATCH'
 }catch{
  [IO.File]::Copy($backup,$destination,$true)
  throw
 }
 Write-Host 'NO11_EMPTY_RETRY_UPGRADE=PASS'
 Write-Host ('NO11_EMPTY_RETRY_UPGRADE_BACKUP='+$backup)
 Write-Host 'NO11_EMPTY_RETRY_UPGRADE_LIMIT=2_EMPTY_WAVE_RETRIES'
 Write-Host 'NO11_EMPTY_RETRY_UPGRADE_EXISTING_20_CAPTURED_SOURCES_RETAINED=True'
 Write-Host 'NO11_EMPTY_RETRY_UPGRADE_ORIGINAL_FROZEN_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_EMPTY_RETRY_UPGRADE_[A-Z0-9_]+$'){$reason='NO11_EMPTY_RETRY_UPGRADE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_EMPTY_RETRY_UPGRADE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
