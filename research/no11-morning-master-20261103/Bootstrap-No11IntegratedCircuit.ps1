# Single, version-pinned integrated circuit repair for an existing max47 install.
# Does not call Excel, refresh data, grant approval, start trading or alter UI.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_CIRCUIT_BOOTSTRAP_'+$why)}}
function GitBlob([byte[]]$bytes){
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($prefix.Length+$bytes.Length)
 [array]::Copy($prefix,0,$all,0,$prefix.Length)
 [array]::Copy($bytes,0,$all,$prefix.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='f407081234e37172dc91b0bf38263c304d8f5b40'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='892477d57e0fe1dc6b1774b238fc01ea7d113ffc'
 'no11_circuit_repair.py'='b517ed2dbd05d22c60153046aabe399d8472cf67'
 'install_no11_circuit_audit_release.py'='1f7ddcffa951fe97df75e54e1d56229c6d672a9f'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 4) 'SELFTEST_ARGUMENTS'
 foreach($pin in $files.Values){Need ([string]$pin -cmatch '^[a-f0-9]{40}$') 'SOURCE_PIN'}
 $empty=New-Object byte[] 0
 Need ((GitBlob $empty) -ceq 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'GIT_BLOB_IMPLEMENTATION'
 Write-Host 'NO11_INTEGRATED_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$binding=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $binding -PathType Leaf) 'BINDING_MISSING'
$b=Get-Content -LiteralPath $binding -Raw -Encoding UTF8 | ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $b.orderTransmission -eq $false) 'BINDING_CONTRACT'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'BOUND_PYTHON_MISSING'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$tmp=Join-Path $env:TEMP ('ARK-Circuit-Release-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($tmp)
try{
 foreach($name in $files.Keys){
  $destination=Join-Path $tmp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $destination -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($destination))) -ceq [string]$files[$name]) ('SOURCE_HASH_'+$name.Replace('.','_').ToUpperInvariant())
 }
 Write-Host ('NO11_INTEGRATED_RELEASE='+$release)
 $tool=Join-Path $tmp 'install_no11_circuit_audit_release.py'
 $arguments=@('-B','-X','utf8',$tool,'--store',$store,'--source-dir',$tmp)
 if($Apply){$arguments+=@('--apply')}
 & $python @arguments
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'ARK_INTEGRATED_CIRCUIT_UPDATE=PASS'}
 else{Write-Host 'ARK_INTEGRATED_CIRCUIT_UPDATE=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $tmp -PathType Container){
  Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
