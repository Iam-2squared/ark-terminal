# Hash-pinned after-hours source repair. NEVER starts Trade, Excel or orders.
# Default: audit only. -Apply: guarded two-file install with preserved originals.
param(
 [switch]$Apply,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$SourceCommit='ffc5cf7ab5e2b2592e4af431dc775f8721bd7374'
$Pins=[ordered]@{
 'install_no11_afterclose_source_repair.py'='e38cce6b19b40d487b7717e22351e5e340a285614ccafa15cac3d886e74df719'
 'no11_rss_opening_source_wait.py'='34a160a50a6678400e7416bb36b95b1c5e54b5284d150b8ad9da504568b42a53'
 'no11_weekly_filtered_lineage.py'='7d2ee90b71316c85a6217e7e08b40f96a7723a2325ed51c9389d7acc77db24c1'
 'no11_nightly_resume.py'='7e1a9cb3c8744a43ed58fd30b191c69cc49c18d9dc3f5f742286e2abd864a634'
}
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_AFTERCLOSE_RELEASE_'+$reason)}
}
function HashBytes([byte[]]$bytes){
 $hash=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
}
function VerifyBytes([byte[]]$bytes,[string]$expected){
 Need ($bytes.Length -gt 0 -and $expected -cmatch '^[a-f0-9]{64}$' -and
       (HashBytes $bytes) -ceq $expected) 'PIN_MISMATCH'
}
function SafeDirectory([string]$path){
 Need ([IO.Path]::IsPathRooted($path)) 'ABSOLUTE_PATH_REQUIRED'
 $node=[IO.DirectoryInfo]::new([IO.Path]::GetFullPath($path))
 while($null -ne $node){
  if($node.Exists){
   Need (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_DIRECTORY'
  }
  $node=$node.Parent
 }
}
function WriteNew([string]$path,[byte[]]$bytes){
 $f=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
try{
 Need ($SourceCommit -cmatch '^[a-f0-9]{40}$' -and $Pins.Count -eq 4) 'SOURCE_PINS_INVALID'
 foreach($name in $Pins.Keys){
  Need ($name -cmatch '^[A-Za-z0-9_.-]+[.]py$' -and $Pins[$name] -cmatch '^[a-f0-9]{64}$') 'SOURCE_PINS_INVALID'
 }
 if($OfflineSelfTest){
  Need (-not $Apply) 'SELFTEST_CANNOT_APPLY'
  $data=[Text.Encoding]::ASCII.GetBytes('abc')
  $expected='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
  VerifyBytes $data $expected
  $blocked=$false
  try{VerifyBytes ([Text.Encoding]::ASCII.GetBytes('tampered')) $expected}catch{$blocked=$true}
  Need $blocked 'TAMPER_REJECTION_TEST'
  $temporary=Join-Path ([IO.Path]::GetTempPath()) ('ark-afterclose-selftest-'+[guid]::NewGuid().ToString('N'))
  SafeDirectory $temporary
  [void][IO.Directory]::CreateDirectory($temporary)
  try{
   $file=Join-Path $temporary 'new-only.bin'
   WriteNew $file $data
   $blocked=$false
   try{WriteNew $file ([Text.Encoding]::ASCII.GetBytes('overwrite'))}catch{$blocked=$true}
   Need $blocked 'CREATE_NEW_TEST'
   VerifyBytes ([IO.File]::ReadAllBytes($file)) $expected
  }finally{[IO.Directory]::Delete($temporary,$true)}
  Write-Host 'NO11_AFTERCLOSE_RELEASE_SELFTEST=PASS'
  Write-Host 'DOWNLOADS=False'
  Write-Host 'EXCEL_ACCESSED=False'
  Write-Host 'TRADE_STARTED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 Need (Test-Path -LiteralPath $store -PathType Container) 'EXISTING_LAUNCHER_REQUIRED'
 SafeDirectory $store
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'BINDING_CONTRACT'
 $python=[string]$binding.python
 Need ([IO.Path]::IsPathRooted($python) -and [IO.Path]::GetFileName($python) -ieq 'python.exe' -and
       (Test-Path -LiteralPath $python -PathType Leaf)) 'PINNED_PYTHON_REQUIRED'
 SafeDirectory ([IO.Path]::GetDirectoryName($python))
 Need (((Get-Item -LiteralPath $python).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'PYTHON_REPARSE_PATH'
 $base=Join-Path $store 'afterclose-source-repair-release'
 SafeDirectory $base
 [void][IO.Directory]::CreateDirectory($base)
 $release=Join-Path $base ($SourceCommit+'-'+[guid]::NewGuid().ToString('N'))
 Need (-not (Test-Path -LiteralPath $release)) 'NEW_RELEASE_DIRECTORY_REQUIRED'
 [void][IO.Directory]::CreateDirectory($release)
 SafeDirectory $release
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 foreach($name in $Pins.Keys){
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$SourceCommit+'/research/no11-morning-master-20261103/'+$name
  $temporary=Join-Path $release ($name+'.download')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temporary -TimeoutSec 30 -ErrorAction Stop
  $bytes=[IO.File]::ReadAllBytes($temporary)
  VerifyBytes $bytes $Pins[$name]
  $destination=Join-Path $release $name
  WriteNew $destination $bytes
  VerifyBytes ([IO.File]::ReadAllBytes($destination)) $Pins[$name]
  [IO.File]::Delete($temporary)
 }
 Write-Host 'NO11_AFTERCLOSE_REPAIR_RELEASE=VERIFIED'
 Write-Host ('NO11_AFTERCLOSE_REPAIR_SOURCE_COMMIT='+$SourceCommit)
 $entry=Join-Path $release 'install_no11_afterclose_source_repair.py'
 $arguments=@()
 if($Apply){$arguments+=@('--apply')}
 & $python -B -X utf8 $entry --store $store @arguments
 exit $LASTEXITCODE
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_AFTERCLOSE_RELEASE_DOWNLOAD_OR_LOCAL_IO_FAILED'}
 Write-Host ('NO11_AFTERCLOSE_SOURCE_REPAIR=BLOCKED|'+$reason)
 Write-Host 'PRESERVE_INSTALL_JOURNAL_AND_DO_NOT_START_TRADE=True'
 Write-Host 'TRADE_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}
