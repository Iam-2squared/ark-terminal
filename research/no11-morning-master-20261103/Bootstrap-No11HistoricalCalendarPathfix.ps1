# Fix the one-line Windows calendar script path, preserving all 2026-11-09
# receipts and failed checkpoint. This bootstrap ONLY installs offline code.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Need([bool]$value,[string]$reason){
 if(-not $value){throw ('NO11_FRIDAY_CHILD_PATHFIX_BOOTSTRAP_'+$reason)}
}
function GitBlob([byte[]]$data){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $bytes=New-Object byte[] ($head.Length+$data.Length)
 [array]::Copy($head,0,$bytes,0,$head.Length)
 [array]::Copy($data,0,$bytes,$head.Length,$data.Length)
 $h=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}

$release='5e563e3bdb1af249976f3161c28f30aba82241a8'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='892477d57e0fe1dc6b1774b238fc01ea7d113ffc'
 'install_no11_historical_calendar_pathfix.py'='75856729794a57795661bf62256972f4953a4375'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 3) 'SELFTEST_ARGUMENTS'
 foreach($val in $files.Values){Need ([string]$val -cmatch '^[a-f0-9]{40}$') 'PIN_INVALID'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq
   'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'GIT_SHA_IMPLEMENTATION'
 Write-Host 'NO11_FRIDAY_CHILD_PATHFIX_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$binding=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $binding -PathType Leaf) 'BINDING_MISSING'
$b=Get-Content -LiteralPath $binding -Raw -Encoding UTF8 | ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $b.orderTransmission -eq $false) 'NOT_READ_ONLY_DATA_BINDING'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and
      (Test-Path -LiteralPath $python -PathType Leaf)) 'PINNED_PYTHON_MISSING'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$temp=Join-Path $env:TEMP ('ARK-Friday-Child-Pathfix-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $files.Keys){
  $dest=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($dest))) -ceq
        [string]$files[$name]) 'DOWNLOADED_SOURCE_HASH_FAILED'
 }
 Write-Host ('NO11_FRIDAY_CHILD_PATHFIX_SOURCE='+$release)
 $args=@('-B','-X','utf8',(Join-Path $temp 'install_no11_historical_calendar_pathfix.py'),
         '--store',$store)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'ARK_NO11_FRIDAY_CHILD_PATHFIX=PASS'}
 else{Write-Host 'ARK_NO11_FRIDAY_CHILD_PATHFIX=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
