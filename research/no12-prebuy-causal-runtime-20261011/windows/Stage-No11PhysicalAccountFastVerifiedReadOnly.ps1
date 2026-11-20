# User-PC / private overlay ONLY. Keep original 429 RSS captures and original
# Ark code intact. Upgrade two exact pinned read-only account reader files:
# 50 rows + Excel-native full 5000-row empty-tail proof, twice per snapshot.
# If any remaining material exists, never call the limited table complete.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$revision='b08550e676f1576d1e8e9a0db7799abd56f6ffd3'
$items=@(
 @{Name='Read-No11BrokerSnapshot.ps1';Old='56ceba7bc51f53c7430cbba35beaa3da11bdf442';New='38d75fb2da74cb1c395b512b8fb3babc6a17557a'},
 @{Name='Observe-No11AccountReadOnly.ps1';Old='30ad74a6dc28ef85ab8346bc752ffd2c8bd4bc49';New='4a2e6cf56229d4387a03a45105c10d20958ce67f'}
)
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_FAST_ACCOUNT_STAGE_'+$code)}}
function Digest([string]$path){
 $h=@(& git hash-object --no-filters $path)
 Need ($LASTEXITCODE -eq 0 -and $h.Count -eq 1 -and [string]$h[0] -cmatch '^[0-9a-f]{40}$') 'GIT_BLOB_FAILED'
 return [string]$h[0]
}
function Safe([string]$path){
 $p=[IO.Path]::GetFullPath($path)
 $cursor=$p
 while(-not [string]::IsNullOrEmpty($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $cursor;if($parent -ceq $cursor){break};$cursor=$parent
 }
 return $p
}
if($OfflineSelfTest){
 Need ($items.Count -eq 2 -and $revision -cmatch '^[a-f0-9]{40}$') 'STATIC_CONFIG'
 foreach($t in $items){Need ($t.Old -cmatch '^[a-f0-9]{40}$' -and $t.New -cmatch '^[a-f0-9]{40}$') 'STATIC_HASH'}
 Write-Host 'NO11_FAST_ACCOUNT_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_FAST_ACCOUNT_STAGE_EXCEL_TOUCHED=False'
 Write-Host 'NO11_FAST_ACCOUNT_STAGE_ORIGINAL_ARK_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $root=Safe (Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\physical-account-overlay\source\research\no12-prebuy-causal-runtime-20261011')
 Need (Test-Path -LiteralPath $root -PathType Container) 'PRIVATE_OVERLAY_MISSING'
 $win=Safe (Join-Path $root 'windows')
 Need (Test-Path -LiteralPath $win -PathType Container) 'WINDOWS_SOURCE_DIR_MISSING'
 $launcher=Safe (Join-Path $win 'Run-No11PhysicalAccountOneShotReadOnly.ps1')
 $original=Safe (Join-Path $root '..\..\integration\no1-1-msii\windows\Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1')
 foreach($p in @($launcher,$original)){Need (Test-Path -LiteralPath $p -PathType Leaf) 'PINNED_SOURCE_MISSING'}
 Need ((Digest $launcher) -ceq '89ea56ab1ee7c25fad8cebb36a5043e3a853ded3') 'PHYSICAL_LAUNCHER_CHANGED'
 Need ((Digest $original) -ceq 'f8be4d704ebad539762471ba62476c32b02a65b1') 'ORIGINAL_V3_SOURCE_CHANGED'
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop|
  Where-Object {$_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Observe-No11AccountReadOnly|Run-No11PhysicalAccountOneShotReadOnly)\.ps1'})
 Need ($busy.Count -eq 0) 'READER_RUNNING_STOP_FIRST'
 $folder=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\physical-account-overlay\fast-read-upgrade\'+[guid]::NewGuid().ToString('N'))
 $staged=Join-Path $folder 'stage';$backup=Join-Path $folder 'backups'
 [void][IO.Directory]::CreateDirectory($staged);[void][IO.Directory]::CreateDirectory($backup)
 Safe $staged;Safe $backup
 $prepared=@()
 foreach($item in $items){
  $dest=Safe (Join-Path $win ([string]$item.Name))
  Need (Test-Path -LiteralPath $dest -PathType Leaf) 'READER_FILE_MISSING'
  $actual=Digest $dest
  Write-Host ('NO11_FAST_ACCOUNT_ORIGINAL_BLOB_'+$item.Name+'='+$actual)
  Need ($actual -ceq $item.Old -or $actual -ceq $item.New) 'LOCAL_READER_FILE_CHANGED_NO_OVERWRITE'
  if($actual -ceq $item.New){continue}
  $new=Join-Path $staged ([string]$item.Name)
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
    '/research/no12-prebuy-causal-runtime-20261011/windows/'+$item.Name
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $new
  Need ((Digest $new) -ceq $item.New) 'PINNED_DOWNLOAD_MISMATCH'
  $tokens=$null;$errors=$null
  [void][Management.Automation.Language.Parser]::ParseFile($new,[ref]$tokens,[ref]$errors)
  Need ($errors.Count -eq 0) 'PS_PARSE_FAILED'
  $prepared+=@([pscustomobject]@{
   from=$dest;new=$new;hash=$item.New;old=$item.Old
   backup=(Join-Path $backup ($item.Name+'.bak'))
  })
 }
 foreach($item in $prepared){[IO.File]::Copy($item.from,$item.backup,$false)}
 $touched=@()
 try{
  foreach($item in $prepared){
   $touched+=@($item)
   [IO.File]::Copy($item.new,$item.from,$true)
   Need ((Digest $item.from) -ceq $item.hash) 'COPY_HASH_CHANGED'
  }
  $source=Join-Path $win 'Read-No11BrokerSnapshot.ps1'
  $reader=Join-Path $win 'Observe-No11AccountReadOnly.ps1'
  Need ((Digest $source) -ceq $items[0].New -and
   (Digest $reader) -ceq $items[1].New) 'FINAL_SOURCE_HASH'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $source -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'BROKER_READER_OFFLINE_SELFTEST_FAILED'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reader -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'ACCOUNT_OBSERVER_OFFLINE_SELFTEST_FAILED'
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){[IO.File]::Copy($touched[$i].backup,$touched[$i].from,$true)}
  throw
 }
 Write-Host 'NO11_FAST_ACCOUNT_STAGE=PASS'
 Write-Host ('NO11_FAST_ACCOUNT_STAGE_BACKUP='+$backup)
 Write-Host 'NO11_FAST_ACCOUNT_MAX_ROWS=50_WITH_FULL_5000_TAIL_COUNT_PROOF'
 Write-Host 'NO11_FAST_ACCOUNT_STAGE_EXCEL_TOUCHED=False'
 Write-Host 'NO11_FAST_ACCOUNT_STAGE_ORIGINAL_ARK_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_FAST_ACCOUNT_STAGE_[A-Z0-9_]+$'){$reason='NO11_FAST_ACCOUNT_STAGE_LOCAL_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_FAST_ACCOUNT_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
