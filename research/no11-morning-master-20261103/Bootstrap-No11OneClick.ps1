# One-time pinned download/install of Ark No11 OneClick desktop UI.
# No model, broker, ledger, Excel, trading order or existing launcher changes.
param([switch]$Apply,[switch]$EnableNightlyTask,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OfflineSelfTest){
 if($Apply -or $EnableNightlyTask){throw 'NO11_ONECLICK_BOOTSTRAP_SELFTEST_FLAGS'}
 Write-Host 'NO11_ONECLICK_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if(-not $Apply){throw 'NO11_ONECLICK_BOOTSTRAP_EXPLICIT_APPLY_REQUIRED'}
$repo='Iam-2squared/ark-terminal'
$commit='dcf38ac0ed807e118decac13e789dce9c42956f1'
$path='research/no11-morning-master-20261103'
$pins=[ordered]@{
 'oneclick_status.py'='1f5611336abc8d68731a44243fa67a6c6a4ebf9f'
 'Start-No11OneClick.ps1'='6d1f91d2470e96df28a181f5ebd89b0151fabf67'
 'Review-No11RecoveryReadOnly.ps1'='e0ba60daa329a4c301ac0db62ab980d55096feec'
 'no11_same_day_reconcile.py'='e26e0cdf8d6af186cc1d1ec40aca75f02e71589f'
 'Install-No11OneClick.ps1'='b8d6146a8dba5d9a42a885fde162f3fd92f560e3'
}
function BlobHash([byte[]]$bytes){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$bytes.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($bytes,0,$all,$header.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
$dir=Join-Path $store ('oneclick-installer-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($dir)
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
foreach($name in $pins.Keys){
 $url='https://raw.githubusercontent.com/'+$repo+'/'+$commit+'/'+$path+'/'+$name
 $dest=Join-Path $dir $name
 Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop
 $bytes=[IO.File]::ReadAllBytes($dest)
 if((BlobHash $bytes) -cne $pins[$name]){throw ('NO11_ONECLICK_BOOTSTRAP_HASH_MISMATCH_'+$name)}
}
$installer=Join-Path $dir 'Install-No11OneClick.ps1'
$argsList=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
            '-File',$installer,'-Apply','-SourceDir',$dir)
if($EnableNightlyTask){$argsList+=@('-EnableNightlyTask')}
& powershell.exe @argsList
if($LASTEXITCODE -ne 0){throw 'NO11_ONECLICK_BOOTSTRAP_INSTALL_FAILED'}
Write-Host 'NO11_ONECLICK_BOOTSTRAP=PASS'
Write-Host 'EXISTING_TRADE_SOURCE_UNMODIFIED=True'
Write-Host 'TRADE_LAUNCHED=False'
Write-Host 'ORDER_TRANSMISSION=False'
