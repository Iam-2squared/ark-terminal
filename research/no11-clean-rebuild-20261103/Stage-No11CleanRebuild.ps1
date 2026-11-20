# Fresh source-only package; no previous Operational/EXIT package is loaded.
# Default: audit. -Stage: isolated payload only, never live installation.
param(
 [Parameter(Mandatory=$true)][string]$SourceRoot,
 [switch]$Stage,
 [string]$Destination=''
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$Ok,[string]$Reason){if(-not $Ok){throw ('NO11_CLEAN_STAGE_'+$Reason)}}
function CanonicalBlob([byte[]]$Bytes){
 $utf8=[Text.UTF8Encoding]::new($false,$true)
 $canonical=$utf8.GetBytes($utf8.GetString($Bytes).Replace("`r`n","`n"))
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$canonical.Length)+[char]0)
 $buffer=New-Object byte[] ($prefix.Length+$canonical.Length)
 [array]::Copy($prefix,0,$buffer,0,$prefix.Length)
 [array]::Copy($canonical,0,$buffer,$prefix.Length,$canonical.Length)
 $hash=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($hash.ComputeHash($buffer))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
}
function PayloadSha256([string]$Path){
 $hash=[Security.Cryptography.SHA256]::Create()
 $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
 try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
 finally{$stream.Dispose();$hash.Dispose()}
}
function SafePath([string]$Value){
 Need ([IO.Path]::IsPathRooted($Value)) 'ABSOLUTE_PATH_REQUIRED'
 $p=[IO.Path]::GetFullPath($Value)
 $cursor=$p
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   Need (((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_POINT'
  }
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break};$cursor=$parent
 }
 return $p
}
$root=SafePath $SourceRoot
Need (Test-Path -LiteralPath $root -PathType Container) 'SOURCE_ROOT_REQUIRED'
$manifestPath=Join-Path $PSScriptRoot 'manifest.json'
Need (Test-Path -LiteralPath $manifestPath -PathType Leaf) 'NEW_PACKAGE_MANIFEST_REQUIRED'
$m=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
Need ($m.schemaId -ceq 'ARK_NO11_CLEAN_REBUILD_PACKAGE_V1' -and
 $m.baseCommit -ceq '24b906e19a2623e45701311ca3fbb20dafe11c80' -and
 $m.oldPackagesUsed -eq $false -and $m.orderTransmission -eq $false -and
 $m.productionReady -eq $false -and @($m.files).Count -eq 10) 'MANIFEST_CONTRACT'
$entries=@();$seen=@{};$original=0;$rebuilt=0;$new=0
foreach($entry in $m.files){
 $relative=[string]$entry.path
 $valid=($relative -cmatch '^research/no12-prebuy-causal-runtime-20261011/(tools|windows)/[A-Za-z0-9_.-]+\.(py|ps1)$')
 Need ($valid -and -not $seen.ContainsKey($relative)) 'TARGET_PATH'
 $seen[$relative]=$true
 $payload=SafePath (Join-Path (Join-Path $PSScriptRoot 'payload') $relative)
 Need (Test-Path -LiteralPath $payload -PathType Leaf) 'PAYLOAD_MISSING'
 Need ((PayloadSha256 $payload) -ceq [string]$entry.outputSha256) 'PAYLOAD_HASH'
 $target=SafePath (Join-Path $root $relative)
 $exists=Test-Path -LiteralPath $target -PathType Leaf
 if($exists){
  $b=CanonicalBlob ([IO.File]::ReadAllBytes($target))
  if($b -ceq [string]$entry.outputGitBlob){$rebuilt++}
  elseif($null -ne $entry.sourceGitBlob -and $b -ceq [string]$entry.sourceGitBlob){$original++}
  else{throw 'NO11_CLEAN_STAGE_LOCAL_FILE_DIFFERS'}
 }else{
  Need ($null -eq $entry.sourceGitBlob) 'SOURCE_FILE_MISSING';$new++
 }
 $entries+=@([pscustomobject]@{relative=$relative;payload=$payload})
}
Need (($original -eq 7 -and $new -eq 3 -and $rebuilt -eq 0) -or $rebuilt -eq 10) 'MIXED_INSTALLATION_REQUIRES_REVIEW'
Write-Host 'NO11_CLEAN_SOURCE_AUDIT=PASS'
if($Stage){
 if([string]::IsNullOrWhiteSpace($Destination)){
  $parent=Join-Path $env:LOCALAPPDATA 'ArkTerminal/No12'
  Need (Test-Path -LiteralPath $parent -PathType Container) 'PRIVATE_PARENT_MISSING'
  $Destination=Join-Path $parent ('clean-rebuild-stage-'+[guid]::NewGuid().ToString('N'))
 }
 $dest=SafePath $Destination
 Need (-not (Test-Path -LiteralPath $dest)) 'DESTINATION_ALREADY_EXISTS'
 Need (Test-Path -LiteralPath (Split-Path -Parent $dest) -PathType Container) 'DESTINATION_PARENT_MISSING'
 $slash=[IO.Path]::DirectorySeparatorChar
 Need (-not $dest.Equals($root,[StringComparison]::OrdinalIgnoreCase) -and
  -not $dest.StartsWith($root.TrimEnd('\','/')+$slash,[StringComparison]::OrdinalIgnoreCase)) 'STAGE_MUST_BE_OUTSIDE_SOURCE'
 [void][IO.Directory]::CreateDirectory($dest)
 foreach($entry in $entries){
  $file=Join-Path $dest $entry.relative
  [void][IO.Directory]::CreateDirectory((Split-Path -Parent $file))
  $bytes=[IO.File]::ReadAllBytes($entry.payload)
  $handle=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$handle.Write($bytes,0,$bytes.Length);$handle.Flush($true)}finally{$handle.Dispose()}
 }
 [IO.File]::Copy($manifestPath,(Join-Path $dest 'manifest.json'),$false)
 Write-Host ('NO11_CLEAN_STAGE_ROOT='+$dest)
 Write-Host 'NO11_CLEAN_STAGE=PAYLOAD_ONLY_NOT_A_RUNNABLE_ENGINE'
}else{Write-Host 'NO11_CLEAN_STAGE=AUDIT_ONLY'}
Write-Host 'LIVE_INSTALLATION_MODIFIED=False'
Write-Host 'LAUNCHER_CHANGED=False'
Write-Host 'ORDER_TRANSMISSION=False'
