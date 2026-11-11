# Immutable, hash-verified release for the explicit pre-registration retry.
# Personal account holdings are preserved, not adopted into ARK ownership.
param(
 [switch]$Start,
 [Alias('IConfirmNoArkOrdersFillsOrPositions')]
 [switch]$IConfirmNoOrdersFillsOrPositions,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$SourceCommit='6da33e9b2a436eeaf6470129c7f98875e0262498'
$Pins=[ordered]@{
 'Request-No11PrestartSourceRetry.ps1'='1c28704e3b942fdbb6aabecb0156f1f3ca34532b0d36df2397c10f62ba97bf01'
 'no11_prestart_source_retry.py'='50874c230c3793c5d4500fa84b732c23faea576b569dd433a168417836ccf54e'
 'no11_weekly_filtered_lineage.py'='7d2ee90b71316c85a6217e7e08b40f96a7723a2325ed51c9389d7acc77db24c1'
 'no11_manual_reconnect_review.py'='abb1421c328489b3c234309bb58ed42cfa175554ab71306056cb9191b5a9ecf9'
}
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_PRESTART_RELEASE_'+$reason)}
}
function HashBytes([byte[]]$bytes){
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$algorithm.Dispose()}
}
function VerifyBytes([byte[]]$bytes,[string]$expected){
 Need ($bytes.Length -gt 0 -and $expected -cmatch '^[a-f0-9]{64}$' -and
       (HashBytes $bytes) -ceq $expected) 'PIN_MISMATCH'
}
function SafeDirectory([string]$path){
 $node=[IO.DirectoryInfo]::new([IO.Path]::GetFullPath($path))
 while($null -ne $node){
  if($node.Exists){
   Need (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_DIRECTORY'
  }
  $node=$node.Parent
 }
}
function WriteNew([string]$path,[byte[]]$bytes){
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
try{
 Need ($SourceCommit -cmatch '^[a-f0-9]{40}$' -and $Pins.Count -eq 4) 'SOURCE_PINS_INVALID'
 foreach($name in $Pins.Keys){
  Need ($name -cmatch '^[A-Za-z0-9_.-]+$' -and
        $Pins[$name] -cmatch '^[a-f0-9]{64}$') 'SOURCE_PINS_INVALID'
 }
 Need (-not $Start -or $IConfirmNoOrdersFillsOrPositions) 'EXPLICIT_NO_ACTIVITY_CONFIRMATION_REQUIRED'
 Need ($Start -or -not $IConfirmNoOrdersFillsOrPositions) 'CONFIRMATION_WITHOUT_START'
 if($OfflineSelfTest){
  Need (-not $Start -and -not $IConfirmNoOrdersFillsOrPositions) 'SELFTEST_FLAGS'
  $data=[Text.Encoding]::ASCII.GetBytes('abc')
  $expected='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
  VerifyBytes $data $expected
  $blocked=$false;try{VerifyBytes ([Text.Encoding]::ASCII.GetBytes('changed')) $expected}catch{$blocked=$true}
  Need $blocked 'TAMPER_REJECTION_TEST'
  $temporary=Join-Path ([IO.Path]::GetTempPath()) ('ark-prestart-release-test-'+[guid]::NewGuid().ToString('N'))
  SafeDirectory $temporary
  [void][IO.Directory]::CreateDirectory($temporary)
  try{
   $file=Join-Path $temporary 'only-new.bin'
   WriteNew $file $data
   $blocked=$false;try{WriteNew $file ([Text.Encoding]::ASCII.GetBytes('overwrite'))}catch{$blocked=$true}
   Need $blocked 'CREATE_NEW_TEST'
   VerifyBytes ([IO.File]::ReadAllBytes($file)) $expected
  }finally{[IO.Directory]::Delete($temporary,$true)}
  Write-Host 'NO11_PRESTART_RETRY_RELEASE_SELFTEST=PASS'
  Write-Host 'DOWNLOADS=False'
  Write-Host 'EXCEL_ACCESSED=False'
  Write-Host 'TRADE_REQUESTED=False'
  exit 0
 }
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 Need ([IO.Directory]::Exists($store)) 'EXISTING_LAUNCHER_REQUIRED'
 $base=Join-Path $store 'prestart-retry-release'
 SafeDirectory $base
 [void][IO.Directory]::CreateDirectory($base)
 $release=Join-Path $base ($SourceCommit+'-'+[guid]::NewGuid().ToString('N'))
 Need (-not [IO.Directory]::Exists($release) -and -not [IO.File]::Exists($release)) 'NEW_RELEASE_DIRECTORY_REQUIRED'
 [void][IO.Directory]::CreateDirectory($release)
 SafeDirectory $release
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 foreach($name in $Pins.Keys){
  $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$SourceCommit+'/research/no11-morning-master-20261103/'+$name
  $temporary=Join-Path $release ($name+'.download')
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $temporary -ErrorAction Stop
  $bytes=[IO.File]::ReadAllBytes($temporary)
  VerifyBytes $bytes $Pins[$name]
  $destination=Join-Path $release $name
  WriteNew $destination $bytes
  VerifyBytes ([IO.File]::ReadAllBytes($destination)) $Pins[$name]
  [IO.File]::Delete($temporary)
 }
 Write-Host 'NO11_PRESTART_RETRY_RELEASE=VERIFIED'
 Write-Host ('NO11_PRESTART_RETRY_SOURCE_COMMIT='+$SourceCommit)
 $entry=Join-Path $release 'Request-No11PrestartSourceRetry.ps1'
 if($Start){& $entry -Start -IConfirmNoOrdersFillsOrPositions}
 else{& $entry}
 exit $LASTEXITCODE
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_PRESTART_RELEASE_DOWNLOAD_OR_LOCAL_IO_FAILED'}
 Write-Host $reason
 Write-Host 'NO11_PRESTART_RETRY_RELEASE_COMPLETED=False'
 exit 2
}
