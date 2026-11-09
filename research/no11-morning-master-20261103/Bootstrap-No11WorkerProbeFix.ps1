# Fixed-source, one-command correction for false old-worker/query collision.
# A separate, byte-pinned DATA-only package. Approved WHITE GUI, model and
# Trade/EXIT/order functions remain unchanged. No receipt deletion or restart.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_WORKER_PROBE_BOOTSTRAP_'+$why)}}
function GitBlob([byte[]]$raw){
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $data=New-Object byte[] ($prefix.Length+$raw.Length)
 [array]::Copy($prefix,0,$data,0,$prefix.Length)
 [array]::Copy($raw,0,$data,$prefix.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($data))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='feaf90be3d71e1803e8a781d61a7d4b6759e0d4d'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='5101f03b1b0d289b3d6c722cf39ada3e21a03df8'
 'install_no11_worker_probe_fix.py'='75ed509de3160bbfaf15e6cbbcd8e0074da33244'
 'Run-No11ResumableNightly.ps1'='5fb604c9316f7f483800c657b0c44306582973ac'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 4) 'SELFTEST_ARGUMENTS'
 foreach($sha in $files.Values){Need ([string]$sha -cmatch '^[a-f0-9]{40}$') 'PIN_NOT_SHA1'}
 Write-Host 'NO11_WORKER_PROBE_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bfile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bfile -PathType Leaf) 'BINDING_REQUIRED'
$b=Get-Content -LiteralPath $bfile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $b.orderTransmission -eq $false) 'BINDING_NOT_DATA_ONLY'
$py=[string]$b.python
Need ([IO.Path]::IsPathRooted($py) -and (Test-Path -LiteralPath $py -PathType Leaf)) 'PYTHON_NOT_BOUND'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$tmp=Join-Path $env:TEMP ('ARK-No11-Worker-Fix-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($tmp)
try{
 foreach($name in $files.Keys){
  $dest=Join-Path $tmp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($dest))) -ceq [string]$files[$name]) 'RELEASE_BYTES_UNEXPECTED'
 }
 Write-Host ('NO11_WORKER_PROBE_RELEASE='+$release)
 $tool=Join-Path $tmp 'install_no11_worker_probe_fix.py'
 $options=@('-B','-X','utf8',$tool,'--store',$store,'--source-dir',$tmp)
 if($Apply){$options+=@('--apply')}
 & $py @options
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'NO11_WEEKLY_WORKER_PROBE_UPDATE=PASS'}
 else{Write-Host 'NO11_WEEKLY_WORKER_PROBE_UPDATE=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $tmp -PathType Container){
  Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
