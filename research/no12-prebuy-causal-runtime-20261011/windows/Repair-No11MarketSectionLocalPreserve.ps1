# Order-OFF repair for real RSS fullwidth P/S/G, retaining local master edits.
param([string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
      [switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sourceRevision='973820bc197a6add66412a3feaa947bd6534b10d'
$localOld='e03b6fc28aa5fba793aacc243002de89afa2a8d5'
$diagHash='2c10c5c2d17ca1e4dff30d1437d207d368ecf8ce'
$known=@(
 @{file='tools\no11_review_queue_from_actual_rss.py';old='c463f5d3a59c893acc062161eabb11f131565e6b';new='3c52d1eb6930d7d4744176b0492754bc3ab88641'},
 @{file='tools\no11_oct28_preopen_doctor.mjs';old='1957469b17a7aa68799282706ecadad07c9156e3';new='1e3a8e3b7021bea04dd8cebeabe981fcadde61a2'}
)
function Need([bool]$ok,[string]$reason){if(-not $ok){throw ('NO11_SECTION_REPAIR_'+$reason)}}
function Hash([string]$filename){
 $v=(& git hash-object --no-filters $filename)
 Need ($LASTEXITCODE -eq 0 -and $v -is [string] -and $v.Trim() -cmatch '^[a-f0-9]{40}$') 'HASH_FAILED'
 return $v.Trim()
}
function Safe([string]$filename){
 $p=[IO.Path]::GetFullPath($filename)
 while(-not [string]::IsNullOrEmpty($p)){
  if(Test-Path -LiteralPath $p){
   $info=Get-Item -LiteralPath $p -Force
   Need (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $p
  if($parent -ceq $p){break}
  $p=$parent
 }
}
function SectionMaps{
 $market=-join [char[]]@(0x6771,0x8A3C)
 $p=[string][char]0xFF30;$s=[string][char]0xFF33;$g=[string][char]0xFF27
 $before="SECTIONS = {'"+$market+"P': 'PRIME', '"+$market+"S': 'STANDARD', '"+$market+"G': 'GROWTH'}"
 $after="SECTIONS = {'"+$market+"P': 'PRIME', '"+$market+$p+"': 'PRIME', '"+$market+"S': 'STANDARD', '"+$market+$s+"': 'STANDARD', '"+$market+"G': 'GROWTH', '"+$market+$g+"': 'GROWTH'}"
 return @{before=$before;after=$after}
}
function OneLinePatch([string]$text){
 $m=SectionMaps
 Need ([regex]::Matches($text,'(?m)^'+[regex]::Escape($m.before)+'\r?$').Count -eq 1) 'LOCAL_DICTIONARY_UNEXPECTED'
 $patched=$text.Replace($m.before,$m.after)
 Need ($patched -cne $text -and [regex]::Matches($patched,'(?m)^'+[regex]::Escape($m.after)+'\r?$').Count -eq 1) 'LOCAL_PATCH_INVALID'
 return $patched
}
if($OfflineSelfTest){
 $m=SectionMaps;$nl=[string][char]13+[string][char]10
 $old='x'+$nl+$m.before+$nl+'y'+$nl
 Need ((OneLinePatch $old) -ceq ('x'+$nl+$m.after+$nl+'y'+$nl)) 'SINGLE_LINE_SELFTEST'
 $blocked=$false
 try{[void](OneLinePatch ($old+$m.before+$nl))}catch{$blocked=$true}
 Need $blocked 'DUPLICATE_LINE_SELFTEST'
 Write-Host 'NO11_SECTION_LOCAL_PRESERVE_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_NOT_FOUND'
 Safe $EngineRoot
 foreach($x in @('git','node','powershell.exe')){[void](Get-Command $x -ErrorAction Stop)}
 $py=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 Need (Test-Path -LiteralPath $py -PathType Leaf) 'PYTHON_NOT_FOUND'
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
  Where-Object {$_.ProcessId -ne $PID -and [string]$_.CommandLine -match '(?i)(Run-No11ReceivedSessionReadOnly|Prepare-No11ReceivedInputsReadOnly|Run-No11Oct29ReferenceOneShotReadOnly|Capture-No11SessionReferenceReadOnly|Prepare-No11WeeklyAfterCloseReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Prepare-No11PreviousArchiveReadOnly)\.ps1'})
 Need ($busy.Count -eq 0) 'COLLECTOR_RUNNING'
 $diag=Join-Path $EngineRoot 'tools\no11_reference_fields_diagnostic.mjs'
 $local=Join-Path $EngineRoot 'tools\no11_prepare_received_inputs.py'
 foreach($v in @($diag,$local)){Safe $v;Need (Test-Path -LiteralPath $v -PathType Leaf) 'SOURCE_MISSING'}
 Need ((Hash $diag) -ceq $diagHash) 'DIAG_VERSION_UNEXPECTED'
 Need ((Hash $local) -ceq $localOld) 'LOCAL_SOURCE_HAS_CHANGED'
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\local-market-section-repair\'+[guid]::NewGuid().ToString('N'))
 $staging=Join-Path $root 'stage';$backups=Join-Path $root 'backups'
 [void][IO.Directory]::CreateDirectory($staging)
 [void][IO.Directory]::CreateDirectory($backups)
 $utf8=New-Object Text.UTF8Encoding($false,$true)
 $source=$utf8.GetString([IO.File]::ReadAllBytes($local))
 $patched=OneLinePatch $source
 $prepared=Join-Path $staging 'no11_prepare_received_inputs.py'
 [IO.File]::WriteAllBytes($prepared,$utf8.GetBytes($patched))
 & $py -B -m ast $prepared | Out-Null
 Need ($LASTEXITCODE -eq 0) 'LOCAL_PYTHON_SYNTAX'
 $patchedHash=Hash $prepared
 Need ($patchedHash -cne $localOld) 'LOCAL_PATCH_NO_CHANGE'
 $updates=@([pscustomobject]@{destination=$local;staged=$prepared;newHash=$patchedHash;backup=(Join-Path $backups 'local_preparer.bak')})
 foreach($item in $known){
  $dest=Join-Path $EngineRoot ([string]$item.file)
  Safe $dest
  Need (Test-Path -LiteralPath $dest -PathType Leaf) 'PINNED_FILE_MISSING'
  $current=Hash $dest
  Need (($current -ceq $item.old) -or ($current -ceq $item.new)) 'PINNED_FILE_CHANGED'
  if($current -ceq $item.new){continue}
  $stage=Join-Path $staging ([IO.Path]::GetFileName([string]$item.file))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$sourceRevision+
   '/research/no12-prebuy-causal-runtime-20261011/'+([string]$item.file).Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $stage
  Need ((Hash $stage) -ceq $item.new) 'PINNED_REMOTE_HASH'
  if($stage.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){& node --check $stage}
  else{& $py -B -m ast $stage | Out-Null}
  Need ($LASTEXITCODE -eq 0) 'PINNED_REMOTE_SYNTAX'
  $updates+=@([pscustomobject]@{destination=$dest;staged=$stage;newHash=$item.new;
    backup=(Join-Path $backups ([string]$item.file).Replace('\','_'))})
 }
 foreach($change in $updates){
  [IO.File]::Copy($change.destination,$change.backup,$false)
  Need (Test-Path -LiteralPath $change.backup -PathType Leaf) 'BACKUP_FAILED'
 }
 $touched=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($change in $updates){
   $touched.Add($change)
   [IO.File]::Copy($change.staged,$change.destination,$true)
   Need ((Hash $change.destination) -ceq $change.newHash) 'INSTALLED_HASH_MISMATCH'
  }
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){
   $v=$touched[$i]
   [IO.File]::Copy($v.backup,$v.destination,$true)
  }
  throw
 }
 Write-Host 'NO11_SECTION_LOCAL_PRESERVED=PASS'
 Write-Host ('NO11_SECTION_NEW_PREPARER_SHA='+$patchedHash)
 Write-Host ('NO11_SECTION_OTHER_FILES_UPDATED='+($updates.Count-1))
 Write-Host ('NO11_SECTION_BACKUPS='+$backups)
 Write-Host 'NO11_SECTION_RAW_REFERENCE_UNCHANGED=True'
 Write-Host 'NO11_SECTION_EXTERNAL_REVIEW=STILL_REQUIRED'
 Write-Host 'NO11_SECTION_SHADOW_PREFLIGHT=NOT_PASSED'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $code=$_.Exception.Message
 if($code -cnotmatch '^NO11_SECTION_REPAIR_[A-Z0-9_]+$'){$code='NO11_SECTION_REPAIR_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_SECTION_LOCAL_PRESERVED=BLOCKED|'+$code)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
