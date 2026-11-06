# AFTER the original 28-Oct reference child has exited: apply the faster
# 47-symbol RSS reference capture and live-progress parent ONLY.
# Strict Git blob whitelist, original copies backed up, rollback on failure.
# Does not start Excel, fetch market data, change Frozen, or send orders.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='51ff793e395dd0f9583897bdda83d516c5b8742b'
$files=@(
 @{
  relative='windows\Capture-No11SessionReferenceReadOnly.ps1'
  accepted=@('94b13a2589b0e2c23d97c8e5c425f3e13581a23f',
             '26d2a79c912d4bfd2422bcb82562004794b50487')
  target='26d2a79c912d4bfd2422bcb82562004794b50487'
 },
 @{
  relative='windows\Run-No11Oct28AfternoonShadowReadOnly.ps1'
  accepted=@('b73141c81c31b5493aaee5df0dbca019429c930f',
             'c1d8514fa17b8169576427403dd687acbf62b5f5',
             'b253086835cf76ab6bfe0fbe9f7f4c0c3cc36b74')
  target='b253086835cf76ab6bfe0fbe9f7f4c0c3cc36b74'
 }
)
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_REFERENCE_BULK_INSTALL_'+$code)}
}
function GitBlob([string]$path){
 $result=@(& git hash-object --no-filters $path)
 Need ($LASTEXITCODE -eq 0 -and $result.Count -eq 1 -and
  [string]$result[0] -cmatch '^[0-9a-f]{40}$') 'GIT_HASH_FAILED'
 return [string]$result[0]
}
function SafePath([string]$candidate){
 Need ([IO.Path]::IsPathRooted($candidate)) 'ABSOLUTE_PATH'
 $cursor=[IO.Path]::GetFullPath($candidate)
 while(-not [string]::IsNullOrEmpty($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band
      [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $p=Split-Path -Parent $cursor
  if($p -ceq $cursor){break}
  $cursor=$p
 }
}

# Exactly one line in a KNOWN GitHub legacy parent is changed. All other
# content, including custom original Shadow control, remains untouched.
function PatchKnownLegacyParent([string]$src,[string]$dest){
 $old='  $output=@(& powershell.exe @args)'
 $new=@'
  $output=@(& powershell.exe @args | ForEach-Object {
   $line=[string]$_
   if($line -match '^(NO11_REFERENCE_STAGE=|NO11_REFERENCE_FORMULA_SCAN_SHEET=|NO11_SESSION_REFERENCE=BLOCKED)'){
    Write-Host $line
   }
   $line
  })
'@
 $raw=[IO.File]::ReadAllText($src,[Text.UTF8Encoding]::new($false))
 $i=$raw.IndexOf($old,[StringComparison]::Ordinal)
 Need ($i -ge 0 -and $raw.LastIndexOf($old,[StringComparison]::Ordinal) -eq $i) 'LEGACY_PARENT_EXACT_ANCHOR_REQUIRED'
 Need ($raw.Contains('ACTUAL_RSS_REFERENCE_FAILED') -and
  $raw.Contains('NO11_SESSION_REFERENCE_FILE=') -and
  $raw.Contains('NO11_TODAY_SHADOW_REFERENCE=OBSERVED_NOT_EXTERNALLY_REVIEWED') -and
  $raw.Contains('ORDER_TRANSMISSION=False') -and
  $raw.Contains('if($CaptureReference){')) 'LEGACY_PARENT_SAFETY_ANCHORS_MISSING'
 $patched=$raw.Replace($old,$new)
 Need (($patched.Length-$raw.Length) -eq ($new.Length-$old.Length) -and
  $patched.Contains($new)) 'LEGACY_PARENT_PATCH_SCOPE_CHANGED'
 [IO.File]::WriteAllText($dest,$patched,[Text.UTF8Encoding]::new($false))
 Write-Host 'NO11_REFERENCE_BULK_LEGACY_PARENT=EXACT_ONE_ANCHOR_PATCHED_OTHER_TEXT_PRESERVED'
}

if($OfflineSelfTest){
 Need ($files.Count -eq 2) 'SOURCE_COUNT'
 foreach($f in $files){
  Need ($f.target -cin $f.accepted -and $f.target -cmatch '^[0-9a-f]{40}$') 'BAD_PINS'
 }
 Need ('c1d8514fa17b8169576427403dd687acbf62b5f5' -cin $files[1].accepted) 'PINNED_KNOWN_LEGACY_REQUIRED'
 Write-Host 'NO11_REFERENCE_BULK_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_REFERENCE_BULK_INSTALL_EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_ROOT_MISSING'
 SafePath $EngineRoot
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command powershell.exe -ErrorAction Stop)
 # Never replace a script already executing; Ctrl+C in its original window,
 # then ensure both parent and child processes are gone.
 $busy=@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction Stop |
   Where-Object {$_.ProcessId -ne $PID -and
    [string]$_.CommandLine -match '(?i)(Capture-No11SessionReferenceReadOnly|Run-No11Oct28AfternoonShadowReadOnly)\.ps1'})
 Need ($busy.Count -eq 0) 'PARENT_OR_CHILD_RUNNING_STOP_ORIGINAL_FIRST'
 $job=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\reference-bulk-repair\'+[guid]::NewGuid().ToString('N'))
 $staging=Join-Path $job 'stage'
 $backup=Join-Path $job 'backups'
 [void][IO.Directory]::CreateDirectory($staging)
 [void][IO.Directory]::CreateDirectory($backup)
 $changes=@()
 $finalHashes=@{}
 foreach($item in $files){
  $original=Join-Path $EngineRoot ([string]$item.relative)
  SafePath $original
  Need (Test-Path -LiteralPath $original -PathType Leaf) 'ORIGINAL_FILE_MISSING'
  $actual=GitBlob $original
  Write-Host ('NO11_REFERENCE_BULK_ORIGINAL_BLOB_'+[IO.Path]::GetFileName($original)+'='+$actual)
  Need ($actual -cin $item.accepted) 'LOCAL_FILE_DIFFERENT_NO_OVERWRITE'
  if($actual -ceq $item.target){
   $finalHashes[$original]=$item.target
   continue
  }
  $new=Join-Path $staging ([IO.Path]::GetFileName($original))
  $expected=$item.target
  if($actual -ceq 'c1d8514fa17b8169576427403dd687acbf62b5f5' -and
    $original.EndsWith('Run-No11Oct28AfternoonShadowReadOnly.ps1',
      [StringComparison]::OrdinalIgnoreCase)){
   # Old working-tree Shadow code is a verified GitHub blob: preserve it.
   PatchKnownLegacyParent $original $new
   $expected=GitBlob $new
  }else{
   $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
    '/research/no12-prebuy-causal-runtime-20261011/'+([string]$item.relative).Replace('\','/')
   Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $new
   Need ((GitBlob $new) -ceq $item.target) 'DOWNLOADED_SHA_MISMATCH'
  }
  $finalHashes[$original]=$expected
  $tokens=$null;$parseErrors=$null
  [void][Management.Automation.Language.Parser]::ParseFile($new,[ref]$tokens,[ref]$parseErrors)
  Need ($parseErrors.Count -eq 0) 'POWERSHELL_PARSE_ERRORS'
  if($original.EndsWith('Capture-No11SessionReferenceReadOnly.ps1',[StringComparison]::OrdinalIgnoreCase)){
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $new -OfflineSelfTest
   Need ($LASTEXITCODE -eq 0) 'COLLECTOR_OFFLINE_SELFTEST_FAILED'
  }
  $changes+=@([pscustomobject]@{
    from=$original;new=$new;sha=$expected
    backup=(Join-Path $backup ([IO.Path]::GetFileName($original)+'.bak'))
  })
 }
 foreach($item in $changes){[IO.File]::Copy($item.from,$item.backup,$false)}
 $applied=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($item in $changes){
   $applied.Add($item)
   [IO.File]::Copy($item.new,$item.from,$true)
   Need ((GitBlob $item.from) -ceq $item.sha) 'INSTALL_HASH_MISMATCH'
  }
  foreach($item in $files){
   $path=Join-Path $EngineRoot ([string]$item.relative)
   Need ((GitBlob $path) -ceq $finalHashes[$path]) 'FINAL_TARGET_HASH_FAILED'
  }
  $collector=Join-Path $EngineRoot 'windows\Capture-No11SessionReferenceReadOnly.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -OfflineSelfTest
  Need ($LASTEXITCODE -eq 0) 'FINAL_OFFLINE_SELFTEST_FAILED'
 }catch{
  for($i=$applied.Count-1;$i -ge 0;$i--){
   [IO.File]::Copy($applied[$i].backup,$applied[$i].from,$true)
  }
  throw
 }
 Write-Host 'NO11_REFERENCE_BULK_INSTALL=PASS'
 Write-Host ('NO11_REFERENCE_BULK_BACKUPS='+$backup)
 Write-Host 'NO11_REFERENCE_BULK_FORMULA_MODE=PER_SHEET_BULK_READ'
 Write-Host 'NO11_REFERENCE_BULK_DIAGNOSTICS=LIVE_CHILD_STAGES'
 Write-Host 'NO11_REFERENCE_BULK_LOCAL_PARENT_CHANGES=PINNED_LEGACY_PRESERVED'
 Write-Host 'NO11_REFERENCE_BULK_EXCEL_TOUCHED=False'
 Write-Host 'NO11_REFERENCE_BULK_PREVIOUS_ARCHIVE_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_REFERENCE_BULK_INSTALL_[A-Z0-9_]+$'){
  $reason='NO11_REFERENCE_BULK_INSTALL_SOURCE_OR_WINDOWS_FAILURE'
 }
 Write-Host ('NO11_REFERENCE_BULK_INSTALL=BLOCKED|'+$reason)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
