# Oct28 No11 read-only five-file source-only update.
# Original models, market data, Excel books, old UI and broker remain untouched.
param([string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
      [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='729a7e93163529bdb0df224b9196a098479756e3'
$pins=@(
  @('tools\no11_weekly_g1_refresh.mjs','8b9d1ed70284be8fb2a41aec711482417c1e15a7'),
  @('windows\Run-No11WeeklyCandidateRefreshReadOnly.ps1','b4dfbc4556e3cc54002d5d16c62f465b4f463975'),
  @('windows\Prepare-No11WeeklyAfterCloseReadOnly.ps1','15204f78a9b03f1db9094072597f0243b7991ece'),
  @('windows\Prepare-No11PreviousArchiveReadOnly.ps1','513593167bd92761a0f19c2b4609ae82d85a8519'),
  @('tools\no11_oct28_preopen_doctor.mjs','1957469b17a7aa68799282706ecadad07c9156e3')
)
if($OfflineSelfTest){
 if($pins.Count -ne 5){throw 'NO11_PATCH_SOURCE_LIST_INVALID'}
 Write-Host 'NO11_OCT28_SOURCE_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if(-not (Test-Path -LiteralPath $EngineRoot -PathType Container)){
 throw 'NO11_OCT28_ENGINE_ROOT_MISSING'
}
$old=$ErrorActionPreference
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\oct28-source-upgrade'
$tag=[guid]::NewGuid().ToString('N')
$staging=Join-Path $root ('staged-'+$tag)
$backups=Join-Path $root ('backup-'+$tag)
[void][IO.Directory]::CreateDirectory($staging)
[void][IO.Directory]::CreateDirectory($backups)
foreach($item in $pins){
 $relative=[string]$item[0];$expected=[string]$item[1]
 $local=Join-Path $staging ([IO.Path]::GetFileName($relative))
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
      '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
 Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $local
 $hash=(& git hash-object --no-filters $local)
 if($LASTEXITCODE -ne 0 -or $hash.Trim() -cne $expected){
  throw 'NO11_OCT28_DOWNLOAD_GIT_BLOB_MISMATCH'
 }
}
Write-Host 'NO11_OCT28_DOWNLOAD=5_OF_5_PINNED'
foreach($item in $pins){
 $relative=[string]$item[0];$expected=[string]$item[1]
 $dest=Join-Path $EngineRoot $relative
 $source=Join-Path $staging ([IO.Path]::GetFileName($relative))
 if(-not (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container)){
  throw 'NO11_OCT28_SOURCE_PARENT_MISSING'
 }
 if(Test-Path -LiteralPath $dest -PathType Leaf){
  $current=(& git hash-object --no-filters $dest).Trim()
  if($current -cne $expected){
   $bak=Join-Path $backups ($relative.Replace('\','_')+'.bak')
   [IO.File]::Copy($dest,$bak,$false)
   if(-not [IO.File]::Exists($bak)){throw 'NO11_OCT28_SOURCE_BACKUP_FAILED'}
  }
 }
 [IO.File]::Copy($source,$dest,$true)
 if((& git hash-object --no-filters $dest).Trim() -cne $expected){
  throw 'NO11_OCT28_INSTALLED_GIT_BLOB_MISMATCH'
 }
}
foreach($name in @('Run-No11WeeklyCandidateRefreshReadOnly.ps1',
                   'Prepare-No11WeeklyAfterCloseReadOnly.ps1',
                   'Prepare-No11PreviousArchiveReadOnly.ps1')){
 $p=Join-Path $EngineRoot ('windows\'+$name)
 & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p -OfflineSelfTest
 if($LASTEXITCODE -ne 0){throw 'NO11_OCT28_SOURCE_OFFLINE_TEST_FAILED'}
}
Write-Host 'NO11_OCT28_SOURCE_STAGE=PASS'
Write-Host ('NO11_OCT28_BACKUPS='+$backups)
Write-Host 'NO11_OCT28_FROZEN_CODE_CHANGED=False'
Write-Host 'ORDER_TRANSMISSION=False'
