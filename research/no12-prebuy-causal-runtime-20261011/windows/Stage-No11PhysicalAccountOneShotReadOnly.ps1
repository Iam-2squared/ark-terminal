# Install ONLY missing, byte-pinned official branch local source readers.
# Refuse modified existing files and rollback newly created files after failure.
# No Excel access, workbook change, order permission or order sending.
param([string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$revision='05e4e147a641e3d0516435bc5b78ba5321372fa7'
$pins=@(
 @('research/no12-prebuy-causal-runtime-20261011/windows/Run-No11PhysicalAccountOneShotReadOnly.ps1','9e8608daf95c368dd95ea6e8f9922c29b697e355'),
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
function Need([bool]$pass,[string]$code){if(-not $pass){throw ('NO11_PHYSICAL_STAGE_'+$code)}}
function Blob([string]$f){
 $a=@(& git hash-object --no-filters $f)
 Need ($LASTEXITCODE -eq 0 -and $a.Count -eq 1 -and [string]$a[0] -cmatch '^[a-f0-9]{40}$') 'GIT_HASH_FAILED'
 return [string]$a[0]
}
function Safe([string]$p){
 $cur=[IO.Path]::GetFullPath($p)
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  if(Test-Path -LiteralPath $cur){
   Need (((Get-Item -LiteralPath $cur -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $p2=Split-Path -Parent $cur;if($p2 -ceq $cur){break};$cur=$p2
 }
}
if($OfflineSelfTest){
 Need ($pins.Count -eq 10 -and $revision -cmatch '^[a-f0-9]{40}$') 'STATIC_PIN_COUNT'
 foreach($p in $pins){Need ([string]$p[1] -cmatch '^[a-f0-9]{40}$') 'PIN_FORMAT'}
 Write-Host 'NO11_PHYSICAL_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_PHYSICAL_STAGE_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 [void](Get-Command git -ErrorAction Stop);[void](Get-Command node -ErrorAction Stop)
 Need ([IO.Path]::IsPathRooted($EngineRoot) -and
  (Test-Path -LiteralPath $EngineRoot -PathType Container)) 'ENGINE_ROOT'
 $repo=[IO.Path]::GetFullPath((Join-Path $EngineRoot '..\..'))
 Safe $repo
 Need (Test-Path -LiteralPath (Join-Path $repo 'integration\no1-1-msii') -PathType Container) 'ORIGINAL_REPO_ROOT_MISSING'
 $stage=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\physical-stage\'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($stage)
 $records=@()
 foreach($pin in $pins){
  $rel=[string]$pin[0];$sha=[string]$pin[1]
  $dest=Join-Path $repo ($rel.Replace('/','\'))
  Safe $dest
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'SOURCE_PARENT_MISSING'
  $exists=Test-Path -LiteralPath $dest -PathType Leaf
  Need (-not (Test-Path -LiteralPath $dest -PathType Container)) 'DESTINATION_IS_DIR'
  if($exists){
   $actual=Blob $dest
   Need ($actual -ceq $sha) 'EXISTING_LOCAL_FILE_CHANGED_NO_OVERWRITE'
  }
  $download=Join-Path $stage ($rel.Replace('/','_'))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+'/'+$rel
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $download
  Need ((Blob $download) -ceq $sha) 'DOWNLOAD_HASH_MISMATCH'
  if($dest.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $download
   Need ($LASTEXITCODE -eq 0) 'NODE_PARSE'
  }else{
   $tok=$null;$parseErrors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($download,[ref]$tok,[ref]$parseErrors)
   Need ($parseErrors.Count -eq 0) 'PS_PARSE'
  }
  $records+=@([pscustomobject]@{dest=$dest;download=$download;exists=$exists;sha=$sha})
 }
 Write-Host ('NO11_PHYSICAL_STAGE_VERIFIED_FILES='+$records.Count)
 $created=@()
 try{
  foreach($f in $records){
   if($f.exists){continue}
   $created+=@($f.dest)
   [IO.File]::Copy($f.download,$f.dest,$false)
   Need ((Blob $f.dest) -ceq $f.sha) 'INSTALL_HASH'
  }
  $reader=Join-Path $EngineRoot 'windows\Run-No11PhysicalAccountOneShotReadOnly.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reader -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'ONE_SHOT_SELFTEST_FAILED'
 }catch{
  foreach($f in $created){if(Test-Path -LiteralPath $f -PathType Leaf){[IO.File]::Delete($f)}}
  throw
 }
 Write-Host 'NO11_PHYSICAL_STAGE=PASS'
 Write-Host ('NO11_PHYSICAL_STAGE_NEW_FILES='+$created.Count)
 Write-Host 'NO11_PHYSICAL_STAGE_ORIGINAL_SOURCE_OVERWRITTEN=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $why=$_.Exception.Message
 if($why -cnotmatch '^NO11_PHYSICAL_STAGE_[A-Z0-9_]+$'){$why='NO11_PHYSICAL_STAGE_LOCAL_OR_DOWNLOAD_FAILURE'}
 Write-Host ('NO11_PHYSICAL_STAGE=BLOCKED|'+$why)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
