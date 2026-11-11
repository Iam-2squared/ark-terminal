# Immutable one-command real-RSS missing-Friday recovery for installed WHITE OneClick.
# Only DATA; never launches Excel, capture, Trade, or orders at installation.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why) {
 if(-not $ok){throw ('NO11_REAL_FRIDAY_BOOTSTRAP_'+$why)}
}
function GitBlob([byte[]]$bytes) {
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($head.Length+$bytes.Length)
 [array]::Copy($head,0,$all,0,$head.Length)
 [array]::Copy($bytes,0,$all,$head.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try {return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally {$sha.Dispose()}
}
$release='aa77fd12d0ffb8c47af9066305b661a161d68f09'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='892477d57e0fe1dc6b1774b238fc01ea7d113ffc'
 'no11_missing_friday_recovery_transform.py'='c1f1f0d0f2e87a6782bbf8f276938fb07de559f4'
 'install_no11_missing_friday_recovery.py'='2bc312cc4aee97887e9a95778045cb15399f46da'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 4) 'SELFTEST_ARGS'
 foreach($pin in $files.Values){Need ([string]$pin -cmatch '^[a-f0-9]{40}$') 'PIN_INVALID'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq
   'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'GIT_SHA1_FUNCTION'
 Write-Host 'NO11_REAL_FRIDAY_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$binding=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $binding -PathType Leaf) 'BINDING_MISSING'
$b=Get-Content -LiteralPath $binding -Encoding UTF8 -Raw|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
 $b.orderTransmission -eq $false) 'BINDING_NOT_DATA_ONLY'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and
 (Test-Path -LiteralPath $python -PathType Leaf)) 'BOUND_PYTHON_MISSING'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$tmp=Join-Path $env:TEMP ('ARK-RealFriday-RSS-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($tmp)
try {
 foreach($name in $files.Keys){
  $dest=Join-Path $tmp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($dest))) -ceq [string]$files[$name]) 'DOWNLOADED_SOURCE_MISMATCH'
 }
 Write-Host ('NO11_REAL_FRIDAY_RECOVERY_SOURCE='+$release)
 $args=@('-B','-X','utf8',(Join-Path $tmp 'install_no11_missing_friday_recovery.py'),
          '--store',$store)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_FAILED'
 if($Apply){Write-Host 'ARK_REAL_FRIDAY_RSS_RECOVERY_UPGRADE=PASS'}
 else{Write-Host 'ARK_REAL_FRIDAY_RSS_RECOVERY_UPGRADE=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $tmp -PathType Container){
  Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
