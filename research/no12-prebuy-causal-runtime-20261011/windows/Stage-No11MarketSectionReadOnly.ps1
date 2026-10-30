# No11 selected RSS market-section source-only fix (exact fullwidth P/S/G).
# Installs byte-pinned diagnostics + Python gates; no Excel or order dispatch.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='ec4559b353db8e4c01874ba6dcb42b7cbbbe4452'
$pins=@(
 @{relative='tools\no11_reference_fields_diagnostic.mjs';before='72b4c4b440dd70d7e7c8fa7bd57a470f4ae2d3cd';after='2c10c5c2d17ca1e4dff30d1437d207d368ecf8ce'},
 @{relative='tools\no11_prepare_received_inputs.py';before='c79506f31d007034760d337d1e3d2891d7c8d79f';after='fd8acc72b4d1dbd7626a932baa8b1c2ff4d12be9'},
 @{relative='tools\no11_review_queue_from_actual_rss.py';before='c463f5d3a59c893acc062161eabb11f131565e6b';after='3c52d1eb6930d7d4744176b0492754bc3ab88641'},
 @{relative='tools\no11_oct28_preopen_doctor.mjs';before='1957469b17a7aa68799282706ecadad07c9156e3';after='1e3a8e3b7021bea04dd8cebeabe981fcadde61a2'}
)
function Need([bool]$okay,[string]$code){
 if(-not $okay){throw ('NO11_SECTION_STAGE_'+$code)}
}
function SafePath([string]$full){
 $cursor=[IO.Path]::GetFullPath($full)
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   $item=Get-Item -LiteralPath $cursor -Force
   Need (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_REFUSED'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break}
  $cursor=$parent
 }
}
if($OfflineSelfTest){
 Need ($pins.Count -eq 4 -and $revision -cmatch '^[0-9a-f]{40}$') 'PINS'
 foreach($p in $pins){
  Need ([string]$p.before -cmatch '^[a-f0-9]{40}$' -and
        [string]$p.after -cmatch '^[a-f0-9]{40}$') 'PIN_DIGEST'
 }
 Write-Host 'NO11_SECTION_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_SECTION_EXCEL_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_NOT_FOUND'
 SafePath $EngineRoot
 foreach($command in @('git','node','powershell.exe')){[void](Get-Command $command -ErrorAction Stop)}
 $python=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $python -PathType Leaf) 'PINNED_PYTHON_NOT_FOUND'
 $other=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object { $_.ProcessId -ne $PID -and
   [string]$_.CommandLine -match '(?i)(Run-No11ReceivedSessionReadOnly|Prepare-No11ReceivedInputsReadOnly|Run-No11Oct29ReferenceOneShotReadOnly|Capture-No11SessionReferenceReadOnly|Prepare-No11WeeklyAfterCloseReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Prepare-No11PreviousArchiveReadOnly)\.ps1' })
 Need ($other.Count -eq 0) 'LIVE_COLLECTOR_OR_PREPARATION_RUNNING'
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\section-source-fix\'+[guid]::NewGuid().ToString('N'))
 $staged=Join-Path $root 'stage';$backups=Join-Path $root 'backup'
 [void][IO.Directory]::CreateDirectory($staged)
 [void][IO.Directory]::CreateDirectory($backups)
 $changes=@()
 foreach($pin in $pins){
  $relative=[string]$pin.relative
  $src=Join-Path $staged ($relative.Replace('\','_'))
  $dest=Join-Path $EngineRoot $relative
  SafePath $dest
  Need (Test-Path -LiteralPath $dest -PathType Leaf) 'INSTALLED_SOURCE_MISSING'
  $old=(& git hash-object --no-filters $dest)
  Need ($LASTEXITCODE -eq 0 -and
    ($old.Trim() -ceq $pin.before -or $old.Trim() -ceq $pin.after)) 'INSTALLED_SOURCE_DIVERGED_REVIEW_REQUIRED'
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
       '/research/no12-prebuy-causal-runtime-20261011/'+$relative.Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $src
  $digest=(& git hash-object --no-filters $src)
  Need ($LASTEXITCODE -eq 0 -and $digest.Trim() -ceq $pin.after) 'DOWNLOADED_BLOB_MISMATCH'
  if($relative.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $src
   Need ($LASTEXITCODE -eq 0) 'JAVASCRIPT_SYNTAX'
  }else{
   & $python -B -m ast $src | Out-Null
   Need ($LASTEXITCODE -eq 0) 'PYTHON_SYNTAX'
  }
  if($old.Trim() -cne $pin.after){
   $backup=Join-Path $backups ($relative.Replace('\','_')+'.bak')
   [IO.File]::Copy($dest,$backup,$false)
   $changes+=@([pscustomobject]@{dest=$dest;source=$src;backup=$backup;after=$pin.after})
  }
 }
 Write-Host ('NO11_SECTION_PINNED_DOWNLOAD=4/4|UPDATES='+$changes.Count)
 $touched=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($c in $changes){
   $touched.Add($c)
   [IO.File]::Copy($c.source,$c.dest,$true)
   $installed=(& git hash-object --no-filters $c.dest)
   Need ($LASTEXITCODE -eq 0 -and $installed.Trim() -ceq $c.after) 'INSTALLED_BLOB_MISMATCH'
  }
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){
   $c=$touched[$i]
   [IO.File]::Copy($c.backup,$c.dest,$true)
  }
  throw
 }
 Write-Host 'NO11_SECTION_MARKET_LABEL_FIX=PASS'
 Write-Host ('NO11_SECTION_SOURCE_BACKUPS='+$backups)
 Write-Host 'NO11_SECTION_RAW_RSS_REWRITTEN=False'
 Write-Host 'NO11_SECTION_EXTERNAL_REVIEW=STILL_REQUIRED'
 Write-Host 'NO11_SECTION_SHADOW_PREFLIGHT=NOT_PASSED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_SECTION_STAGE_[A-Z0-9_]+$'){$reason='NO11_SECTION_STAGE_SOURCE_OR_ENVIRONMENT_FAILED'}
 Write-Host ('NO11_SECTION_MARKET_LABEL_FIX=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
