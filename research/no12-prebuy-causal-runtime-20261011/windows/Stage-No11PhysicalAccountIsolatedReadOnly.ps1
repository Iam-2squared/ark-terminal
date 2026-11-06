# Standalone, pinned and isolated REAL account RSS observer source installer.
# Uses a separate %LOCALAPPDATA% source tree; NEVER overwrites any current
# Ark source, original Excel book, private model, RSS receipt, or broker ledger.
# The only downloaded sources are pinned read-only account inspection modules.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$revision='24a6349b509a34542a8897d83cb7abdf675fa5ea'
$pins=@(
 @('research/no12-prebuy-causal-runtime-20261011/windows/Run-No11PhysicalAccountOneShotReadOnly.ps1','89ea56ab1ee7c25fad8cebb36a5043e3a853ded3'),
 @('research/no12-prebuy-causal-runtime-20261011/windows/New-No11BrokerReadOnlyWorkbook.ps1','4c6a7b3ead2916f56370be3f8e2ba4444c5fe999'),
 @('research/no12-prebuy-causal-runtime-20261011/windows/Observe-No11AccountReadOnly.ps1','6c930116bf155b56e6182976f0f2a853d6f76629'),
 @('research/no12-prebuy-causal-runtime-20261011/windows/Read-No11BrokerSnapshot.ps1','56ceba7bc51f53c7430cbba35beaa3da11bdf442'),
 @('research/no12-prebuy-causal-runtime-20261011/tools/no11_account_connection_diagnostic_readonly.mjs','198ab24918b6b71999e5b9fdc10684b3caee256e'),
 @('research/no12-prebuy-causal-runtime-20261011/tools/no11_broker_snapshot.mjs','172f548afcd26bb24dad45bc01f3fdc66671fc51'),
 @('research/no12-prebuy-causal-runtime-20261011/tools/no11_broker_order_state.mjs','03d52ee302a360b29a2eb1d2b5949557a0aecad3'),
 @('research/no12-prebuy-causal-runtime-20261011/runtime/no11_order_boundary.mjs','b7a418279c19a2c6c9ec816a15a8967626100d7a'),
 @('integration/no1-1-msii/runtime/locked_intent.mjs','817c37c884675df85f695e085ba869528d67250c'),
 @('integration/no1-1-msii/windows/Ark-No11-CaptureReadOnly-v3-CANDIDATE.ps1','f8be4d704ebad539762471ba62476c32b02a65b1')
)
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_PHYSICAL_ISOLATED_'+$reason)}
}
function Safe([string]$candidate){
 $p=[IO.Path]::GetFullPath($candidate)
 while(-not [string]::IsNullOrWhiteSpace($p)){
  if(Test-Path -LiteralPath $p){
   Need (((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_POINT'
  }
  $parent=Split-Path -Parent $p
  if($parent -ceq $p){break};$p=$parent
 }
}
function Blob([string]$path){
 $v=@(& git hash-object --no-filters $path)
 Need ($LASTEXITCODE -eq 0 -and $v.Count -eq 1 -and [string]$v[0] -cmatch '^[a-f0-9]{40}$') 'HASH_UNAVAILABLE'
 return [string]$v[0]
}
if($OfflineSelfTest){
 Need ($pins.Count -eq 10 -and $revision -cmatch '^[a-f0-9]{40}$') 'STATIC_PINS'
 Need (@($pins|Where-Object {([string]$_[0]).StartsWith('integration/no1-1-msii/')}).Count -eq 2) 'ORIGINAL_BLOB_COVERAGE'
 Write-Host 'NO11_PHYSICAL_ISOLATED_SELFTEST=PASS'
 Write-Host 'NO11_PHYSICAL_ISOLATED_EXISTING_ARK_FILES_TOUCHED=False'
 Write-Host 'NO11_PHYSICAL_ISOLATED_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 $local=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'))
 $original=[IO.Path]::GetFullPath('C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011')
 $root=Join-Path $local 'physical-account-overlay\source'
 Need (-not $root.Equals($original,[StringComparison]::OrdinalIgnoreCase) -and
  -not $root.StartsWith($original+'\',[StringComparison]::OrdinalIgnoreCase) -and
  -not $original.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) 'ISOLATED_PATH_REQUIRED'
 Safe $root
 [void][IO.Directory]::CreateDirectory($root)
 Safe $root
 $engine=Join-Path $root 'research\no12-prebuy-causal-runtime-20261011'
 $staging=Join-Path $local ('physical-account-overlay\staging\'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($staging)
 Safe $staging
 $items=@()
 foreach($pin in $pins){
  $relative=[string]$pin[0];$expected=[string]$pin[1]
  Need ($expected -cmatch '^[a-f0-9]{40}$' -and
   ($relative.StartsWith('research/no12-prebuy-causal-runtime-20261011/') -or
    $relative.StartsWith('integration/no1-1-msii/')) -and
    $relative -cnotmatch '\.\.') 'PIN_SCOPE_INVALID'
  $dest=[IO.Path]::GetFullPath((Join-Path $root $relative.Replace('/','\')))
  Need ($dest.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) 'DESTINATION_OUTSIDE_ISOLATED_ROOT'
  Safe $dest
  if(Test-Path -LiteralPath $dest -PathType Leaf){
   if((Blob $dest) -cne $expected){
    Write-Host ('NO11_PHYSICAL_ISOLATED_CONFLICT_FILE='+$relative)
    throw 'NO11_PHYSICAL_ISOLATED_EXISTING_OVERLAY_CONFLICT_NO_OVERWRITE'
   }
   $items+=@([pscustomobject]@{dest=$dest;source='';expected=$expected;exists=$true})
   continue
  }
  Need (-not (Test-Path -LiteralPath $dest -PathType Container)) 'DESTINATION_DIRECTORY'
  $source=Join-Path $staging ($relative.Replace('/','_'))
  $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$relative
  Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $source
  Need ((Blob $source) -ceq $expected) 'DOWNLOADED_BLOB_DIFFERS'
  if($dest.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $source
   Need ($LASTEXITCODE -eq 0) 'NODE_SYNTAX_FAILED'
  }else{
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_SYNTAX_FAILED'
  }
  $items+=@([pscustomobject]@{dest=$dest;source=$source;expected=$expected;exists=$false})
 }
 Write-Host ('NO11_PHYSICAL_ISOLATED_SOURCE_CHECK='+$items.Count+'/10')
 $newFiles=@()
 try{
  foreach($item in $items){
   if($item.exists){continue}
   $parent=Split-Path -Parent $item.dest
   [void][IO.Directory]::CreateDirectory($parent)
   Safe $parent
   $newFiles+=@($item.dest)
   [IO.File]::Copy($item.source,$item.dest,$false)
   Need ((Blob $item.dest) -ceq $item.expected) 'COPIED_BLOB_CHANGED'
  }
  $oneShot=Join-Path $engine 'windows\Run-No11PhysicalAccountOneShotReadOnly.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $oneShot -EngineRoot $engine -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'ONE_SHOT_SELFTEST_FAILED'
  $make=Join-Path $engine 'windows\New-No11BrokerReadOnlyWorkbook.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $make -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'BROKER_BOOK_SELFTEST_FAILED'
 }catch{
  foreach($file in $newFiles){if(Test-Path -LiteralPath $file -PathType Leaf){[IO.File]::Delete($file)}}
  throw
 }
 Write-Host 'NO11_PHYSICAL_ISOLATED_STAGE=PASS'
 Write-Host ('NO11_PHYSICAL_ISOLATED_NEW_FILES='+$newFiles.Count)
 Write-Host ('NO11_PHYSICAL_ISOLATED_ENGINE='+$engine)
 Write-Host 'NO11_PHYSICAL_ISOLATED_EXISTING_ARK_FILES_TOUCHED=False'
 # Prepare is only an offline, inert third workbook; it does NOT open Excel.
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $oneShot -EngineRoot $engine -Prepare
 Need ($LASTEXITCODE -eq 0) 'BROKER_READONLY_BOOK_PREPARE_FAILED'
 Write-Host 'NO11_PHYSICAL_ISOLATED_READY_FOR_USER_OPEN_THIRD_BOOK=TRUE'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $why=$_.Exception.Message
 if($why -cnotmatch '^NO11_PHYSICAL_ISOLATED_[A-Z0-9_]+$'){$why='NO11_PHYSICAL_ISOLATED_LOCAL_OR_DOWNLOAD_FAILURE'}
 Write-Host ('NO11_PHYSICAL_ISOLATED_STAGE=BLOCKED|'+$why)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
