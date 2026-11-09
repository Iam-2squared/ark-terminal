# Fully versioned automatic bad 1M entry exclusion, built on real RSS receipts.
# One install: registers permanent skip behavior and (only if already fully
# captured) attempts to finish the saved 2026-11-10 DATA handoff without RSS.
# Frozen BUY/EXIT, OneClick white UI, brokerage settings, workbook files intact.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Need([bool]$v,[string]$code){
 if(-not $v){throw ('NO11_AUTO_MINUTE_BOOTSTRAP_'+$code)}
}
function GitBlob([byte[]]$data){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $all=New-Object byte[] ($head.Length+$data.Length)
 [array]::Copy($head,0,$all,0,$head.Length)
 [array]::Copy($data,0,$all,$head.Length,$data.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='1b3d6d5fbddcf0e0402ec4ef997550ede8422170'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='892477d57e0fe1dc6b1774b238fc01ea7d113ffc'
 'no11_combined_nightly_parser.py'='e2a93de33f044ee58e9c97d0a61f2f822e02471c'
 'no11_auto_minute_cycle_transform.py'='a0a290a2edee4542ee8268fe3eaa7faded88b025'
 'no11_auto_minute_worker_transform.py'='1e7a2f91c99b05e1bacc696efab916056f1abdfd'
 'no11_auto_minute_exclusion.py'='5c3c5e837b031e6df66ac94ae6e56c6eec7049b9'
 'install_no11_auto_minutes_release.py'='36e96df82d3cd234b547ad84735a5b293d4448a6'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 7) 'SELFTEST_OPTIONS'
 foreach($sha in $files.Values){Need ([string]$sha -cmatch '^[a-f0-9]{40}$') 'FILE_PIN_INVALID'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'GIT_BLOB_CHECK'
 Write-Host 'NO11_AUTO_MINUTE_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'BROKER_OR_EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bind=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bind -PathType Leaf) 'ACTIVE_BINDING_MISSING'
$b=Get-Content -LiteralPath $bind -Raw -Encoding UTF8|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $b.orderTransmission -eq $false) 'DATA_BINDING_MODE'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'BOUND_PYTHON_MISSING'

[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$temp=Join-Path $env:TEMP ('ARK-AutomaticMinuteSkip-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $files.Keys){
  $dest=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($dest))) -ceq [string]$files[$name]) 'SOURCE_DIGEST_DIFFERENT'
 }
 Write-Host ('NO11_AUTO_MINUTE_RELEASE='+$release)
 $args=@('-B','-X','utf8',(Join-Path $temp 'install_no11_auto_minutes_release.py'),
          '--store',$store,'--source-dir',$temp)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'ARK_AUTO_BAD_MINUTE_EXCLUSION=INSTALLED'}
 else{Write-Host 'ARK_AUTO_BAD_MINUTE_EXCLUSION=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
   Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
