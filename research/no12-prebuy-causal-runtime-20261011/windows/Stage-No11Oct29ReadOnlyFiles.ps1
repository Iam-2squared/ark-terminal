# 2026-10-29 No11 source-only installer. Read-only; no Excel/model/order access.
# Downloads exact reviewed Git blobs, retains backups and rolls back failed installs.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='07de76726065f505c215e97bdd5e3f3bac1f8204'
$pins=@(
 @('tools\no11_reference_fields_diagnostic.mjs','72b4c4b440dd70d7e7c8fa7bd57a470f4ae2d3cd'),
 @('tools\no11_oct29_preopen_doctor.mjs','66c6de5063654b51434dabc408bf453e709bf5ea'),
 @('windows\Run-No11Oct29ReferenceOneShotReadOnly.ps1','182aa998af2b0997a58255ae533f4c7f8f8bcd47'),
 @('windows\Capture-No11SessionReferenceReadOnly.ps1','94b13a2589b0e2c23d97c8e5c425f3e13581a23f')
)
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_OCT29_STAGE_'+$reason)}
}
if($OfflineSelfTest){
 Need ($pins.Count -eq 4 -and $revision -cmatch '^[a-f0-9]{40}$') 'PINS'
 foreach($pin in $pins){Need ([string]$pin[1] -cmatch '^[a-f0-9]{40}$') 'BLOB_PIN'}
 Write-Host 'NO11_OCT29_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OCT29_EXCEL_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_MISSING'
 foreach($program in @('git','node','powershell.exe')){
  [void](Get-Command $program -ErrorAction Stop)
 }
 $active=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {
   $_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(?:Capture-No11SessionReferenceReadOnly|Run-No11Oct29ReferenceOneShotReadOnly|Prepare-No11WeeklyAfterCloseReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Prepare-No11PreviousArchiveReadOnly|Run-No11ReceivedSessionReadOnly)\.ps1'
  })
 Need ($active.Count -eq 0) 'COLLECTOR_RUNNING_MUST_STOP_NORMALLY'
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct29-readonly-source-stage\'+[guid]::NewGuid().ToString('N'))
 $stage=Join-Path $root 'staged';$backups=Join-Path $root 'backups'
 [void][IO.Directory]::CreateDirectory($stage)
 [void][IO.Directory]::CreateDirectory($backups)
 # Download and verify every source before touching installed code.
 $records=@()
 foreach($pin in $pins){
  $relative=[string]$pin[0];$expected=[string]$pin[1]
  $source=Join-Path $stage ($relative.Replace('\','_'))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
       '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $source
  $actual=(& git hash-object --no-filters $source)
  Need ($LASTEXITCODE -eq 0 -and $actual.Trim() -ceq $expected) 'DOWNLOAD_BLOB_HASH'
  $dest=Join-Path $EngineRoot $relative
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'DESTINATION_PARENT_MISSING'
  Need (-not (Test-Path -LiteralPath $dest -PathType Container)) 'DESTINATION_IS_DIRECTORY'
  $exists=Test-Path -LiteralPath $dest -PathType Leaf
  if($exists -and $relative -cne 'windows\Capture-No11SessionReferenceReadOnly.ps1'){
   $current=(& git hash-object --no-filters $dest)
   Need ($LASTEXITCODE -eq 0 -and $current.Trim() -ceq $expected) 'EXISTING_NEW_FILE_CONFLICT'
  }
  $backup=Join-Path $backups ($relative.Replace('\','_')+'.bak')
  if($exists){[IO.File]::Copy($dest,$backup,$false)}
  $records+=@([pscustomobject]@{relative=$relative;source=$source;dest=$dest;
    expected=$expected;exists=$exists;backup=$backup})
 }
 Write-Host 'NO11_OCT29_STAGE_DOWNLOAD=4_OF_4_PINNED'
 $touched=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($entry in $records){
   [IO.File]::Copy($entry.source,$entry.dest,$true)
   $touched.Add($entry)
   $installed=(& git hash-object --no-filters $entry.dest)
   Need ($LASTEXITCODE -eq 0 -and $installed.Trim() -ceq $entry.expected) 'INSTALL_BLOB_HASH'
  }
  foreach($entry in $records){
   if($entry.dest.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
    & node --check $entry.dest
    Need ($LASTEXITCODE -eq 0) 'NODE_PARSE_FAILED'
   }else{
    $tokens=$null;$errors=$null
    [void][Management.Automation.Language.Parser]::ParseFile(
      $entry.dest,[ref]$tokens,[ref]$errors)
    Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
   }
  }
  foreach($name in @('Capture-No11SessionReferenceReadOnly.ps1',
                     'Run-No11Oct29ReferenceOneShotReadOnly.ps1')){
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $EngineRoot ('windows\'+$name)) -OfflineSelfTest
   Need ($LASTEXITCODE -eq 0) 'SOURCE_SELFTEST_FAILED'
  }
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){
   $entry=$touched[$i]
   if($entry.exists){[IO.File]::Copy($entry.backup,$entry.dest,$true)}
   elseif(Test-Path -LiteralPath $entry.dest -PathType Leaf){Remove-Item -LiteralPath $entry.dest -Force}
  }
  throw
 }
 Write-Host 'NO11_OCT29_SOURCE_STAGE=PASS'
 Write-Host ('NO11_OCT29_STAGE_BACKUPS='+$backups)
 Write-Host 'NO11_OCT29_G1_OR_PREVIOUS_RSS_RUN=False'
 Write-Host 'NO11_OCT29_FROZEN_MODELS_MODIFIED=False'
 Write-Host 'NO11_OCT29_SHADOW_PREFLIGHT=NOT_PASSED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_OCT29_STAGE_[A-Z0-9_]+$'){
  $reason='NO11_OCT29_STAGE_SOURCE_OR_RUNTIME_FAILED'
 }
 Write-Host ('NO11_OCT29_SOURCE_STAGE=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
