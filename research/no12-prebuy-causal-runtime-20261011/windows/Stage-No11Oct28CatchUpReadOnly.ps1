# Stage ONLY three ADDITIVE Oct28 historical D100 recovery helpers.
# Never overwrite originals/local modifications, rewrite historical timestamps,
# touch Excel or enable trading. Reparse-safe, SHA-pinned and offline tested.
param(
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$revision='fb0c413f3adf0ddfc21b80f877478eac9f1ac767'
$files=@(
 @{relative='tools\no11_weekly_g1_catchup_20261028.mjs';sha='a2421d4f4ad4d596f771c6732a3b38610496637a'},
 @{relative='windows\Run-No11WeeklyCandidateCatchUpReadOnly.ps1';sha='1c81294e8542043b1208c71d78e4583921088394'},
 @{relative='windows\Run-No11Oct28CatchUpReadOnly.ps1';sha='a0b17c2a1dcceced006432cc7af29415fdf1244b'}
)
function Need([bool]$yes,[string]$label){if(-not $yes){throw ('NO11_CATCHUP_STAGE_'+$label)}}
function GitHash([string]$p){
 $hash=(& git hash-object --no-filters $p)
 Need ($LASTEXITCODE -eq 0 -and $hash -is [string] -and $hash.Trim() -match '^[a-f0-9]{40}$') 'GIT_HASH_FAILED'
 return $hash.Trim()
}
function SafePath([string]$p){
 $cursor=[IO.Path]::GetFullPath($p)
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break}
  $cursor=$parent
 }
}
if($OfflineSelfTest){
 Need ($files.Count -eq 3 -and $revision -cmatch '^[a-f0-9]{40}$') 'SELFTEST_CONTRACT'
 foreach($item in $files){Need ([string]$item.sha -cmatch '^[a-f0-9]{40}$') 'SELFTEST_BLOB'}
 Write-Host 'NO11_CATCHUP_STAGE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_CATCHUP_STAGE_EXCEL_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
try{
 Need (Test-Path -LiteralPath $EngineRoot -PathType Container) 'ENGINE_MISSING'
 SafePath $EngineRoot
 [void](Get-Command git -ErrorAction Stop)
 [void](Get-Command node -ErrorAction Stop)
 $root=Join-Path $env:LOCALAPPDATA ('ArkTerminal\No12\oct28-catchup-stage\'+[guid]::NewGuid().ToString('N'))
 $stage=Join-Path $root 'staged'
 [void][IO.Directory]::CreateDirectory($stage)
 $install=@()
 foreach($entry in $files){
  $dest=Join-Path $EngineRoot ([string]$entry.relative)
  Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'DESTINATION_PARENT'
  SafePath $dest
  if(Test-Path -LiteralPath $dest -PathType Leaf){
   Need ((GitHash $dest) -ceq $entry.sha) 'EXISTING_HELPER_DIVERGED'
   continue
  }
  $candidate=Join-Path $stage ([IO.Path]::GetFileName($dest))
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$revision+
   '/research/no12-prebuy-causal-runtime-20261011/'+([string]$entry.relative).Replace('\','/')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $candidate
  Need ((GitHash $candidate) -ceq $entry.sha) 'DOWNLOAD_HASH_MISMATCH'
  if($candidate.EndsWith('.mjs',[StringComparison]::OrdinalIgnoreCase)){
   & node --check $candidate
   Need ($LASTEXITCODE -eq 0) 'NODE_PARSE_FAILED'
  }else{
   $tokens=$null;$errors=$null
   [void][Management.Automation.Language.Parser]::ParseFile($candidate,[ref]$tokens,[ref]$errors)
   Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest
   Need ($LASTEXITCODE -eq 0) 'POWERSHELL_SELFTEST_FAILED'
  }
  $install+=@([pscustomobject]@{dest=$dest;source=$candidate;sha=$entry.sha})
 }
 # All candidates passed SHA, parse and offline checks before any install.
 $touched=New-Object 'System.Collections.Generic.List[object]'
 try{
  foreach($entry in $install){
   Need (-not (Test-Path -LiteralPath $entry.dest)) 'RACE_DESTINATION_APPEARED'
   $touched.Add($entry)
   [IO.File]::Copy($entry.source,$entry.dest,$false)
   Need ((GitHash $entry.dest) -ceq $entry.sha) 'POST_INSTALL_HASH_MISMATCH'
  }
 }catch{
  for($i=$touched.Count-1;$i -ge 0;$i--){
   $entry=$touched[$i]
   if(Test-Path -LiteralPath $entry.dest -PathType Leaf){[IO.File]::Delete($entry.dest)}
  }
  throw
 }
 Write-Host 'NO11_OCT28_CATCHUP_STAGE=PASS'
 Write-Host ('NO11_OCT28_CATCHUP_STAGE_SOURCE='+$revision)
 Write-Host ('NO11_OCT28_CATCHUP_STAGE_NEW_FILES='+$install.Count)
 Write-Host 'NO11_OCT28_CATCHUP_STAGE_ORIGINAL_FILES_CHANGED=False'
 Write-Host 'NO11_OCT28_CATCHUP_STAGE_REAL_RSS_STARTED=False'
 Write-Host 'NO11_OCT28_CATCHUP_STAGE_ORDER_TRANSMISSION=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $msg=$_.Exception.Message
 if($msg -cnotmatch '^NO11_CATCHUP_STAGE_[A-Z0-9_]+$'){$msg='NO11_CATCHUP_STAGE_PRIVATE_SOURCE_OR_RUNTIME_FAILURE'}
 Write-Host ('NO11_OCT28_CATCHUP_STAGE=BLOCKED|'+$msg)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
