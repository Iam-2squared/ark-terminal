# Upgrade just the pinned physical-account READ-ONLY observer in the private
# isolated overlay. Preserves original Ark files, Excel books, source receipts,
# real holdings, balances, model weights, and broker order permissions.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='5f95f34f70ef4e080ef3ca1b8d379fd44df8e9f9'
$old='6c930116bf155b56e6182976f0f2a853d6f76629'
$new='30ad74a6dc28ef85ab8346bc752ffd2c8bd4bc49'
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_ACCOUNT_REASON_STAGE_'+$reason)}
}
function GitBlob([string]$filename){
 $hash=@(& git hash-object --no-filters $filename)
 Need ($LASTEXITCODE -eq 0 -and $hash.Count -eq 1 -and
  [string]$hash[0] -cmatch '^[0-9a-f]{40}$') 'GIT_HASH_FAILED'
 return [string]$hash[0]
}
function Safe([string]$filename){
 $file=[IO.Path]::GetFullPath($filename)
 $cursor=$file
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break}
  $cursor=$parent
 }
 return $file
}
if($OfflineSelfTest){
 Need ($revision -cmatch '^[0-9a-f]{40}$' -and
  $old -cmatch '^[0-9a-f]{40}$' -and
  $new -cmatch '^[0-9a-f]{40}$') 'STATIC_PIN_INVALID'
 Need ($old -cne $new) 'SAME_VERSION'
 Write-Host 'NO11_ACCOUNT_REASON_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_ACCOUNT_REASON_STAGE_EXCEL_TOUCHED=False'
 Write-Host 'NO11_ACCOUNT_REASON_STAGE_ARK_ORIGINAL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $base=Safe (Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\physical-account-overlay\source\research\no12-prebuy-causal-runtime-20261011')
 Need (Test-Path -LiteralPath $base -PathType Container) 'ISOLATED_OVERLAY_MISSING'
 $observer=Safe (Join-Path $base 'windows\Observe-No11AccountReadOnly.ps1')
 $helper=Safe (Join-Path $base 'windows\Read-No11BrokerSnapshot.ps1')
 $original=Safe (Join-Path $base '..\..\integration\no1-1-msii\windows\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1')
 foreach($file in @($observer,$helper,$original)){Need (Test-Path -LiteralPath $file -PathType Leaf) 'SOURCE_NOT_FOUND'}
 Need ((GitBlob $helper) -ceq '56ceba7bc51f53c7430cbba35beaa3da11bdf442') 'ACCOUNT_READER_CHANGED'
 Need ((GitBlob $original) -ceq 'f8be4d704ebad539762471ba62476c32b02a65b1') 'ORIGINAL_CAPTURE_SOURCE_CHANGED'
 $running=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Observe-No11AccountReadOnly|Run-No11PhysicalAccountOneShotReadOnly)\.ps1'})
 Need ($running.Count -eq 0) 'ACCOUNT_OBSERVER_STILL_RUNNING'
 $actual=GitBlob $observer
 Write-Host ('NO11_ACCOUNT_REASON_STAGE_SOURCE_BLOB='+$actual)
 Need ($actual -ceq $old -or $actual -ceq $new) 'LOCAL_FILE_DIFFERENT_NO_OVERWRITE'
 if($actual -ceq $new){
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $observer -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'OFFLINE_SELFTEST_FAILED'
  Write-Host 'NO11_ACCOUNT_REASON_STAGE=ALREADY_INSTALLED'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $folder=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\physical-account-overlay\reason-repair\'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($folder)
 $download=Join-Path $folder 'Observe-No11AccountReadOnly.ps1'
 $backup=Join-Path $folder 'original-observer.bak'
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
  '/research/no12-prebuy-causal-runtime-20261011/windows/Observe-No11AccountReadOnly.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $download
 Need ((GitBlob $download) -ceq $new) 'DOWNLOAD_BLOB_HASH_MISMATCH'
 $tokens=$null;$parseErrors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($download,[ref]$tokens,[ref]$parseErrors)
 Need ($parseErrors.Count -eq 0) 'POWER_SHELL_PARSE_FAILED'
 [IO.File]::Copy($observer,$backup,$false)
 try{
  [IO.File]::Copy($download,$observer,$true)
  Need ((GitBlob $observer) -ceq $new) 'INSTALLED_BLOB_MISMATCH'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $observer -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'OFFLINE_SELFTEST_FAILED'
 }catch{
  [IO.File]::Copy($backup,$observer,$true)
  throw
 }
 Write-Host 'NO11_ACCOUNT_REASON_STAGE=PASS'
 Write-Host ('NO11_ACCOUNT_REASON_STAGE_BACKUP='+$backup)
 Write-Host 'NO11_ACCOUNT_REASON_STAGE_EXISTING_ARK_ORIGINALS_TOUCHED=False'
 Write-Host 'NO11_ACCOUNT_REASON_STAGE_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $why=$_.Exception.Message
 if($why -cnotmatch '^NO11_ACCOUNT_REASON_STAGE_[A-Z0-9_]+$'){$why='NO11_ACCOUNT_REASON_STAGE_PRIVATE_SOURCE_OR_RUNTIME_FAILED'}
 Write-Host ('NO11_ACCOUNT_REASON_STAGE=BLOCKED|'+$why)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
