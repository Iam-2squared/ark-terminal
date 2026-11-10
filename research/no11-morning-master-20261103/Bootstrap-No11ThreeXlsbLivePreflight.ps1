# V2: explicit enrollment of the three currently open, saved role-checked books.
# Synchronizes DATA/LIVE paths; preserves completed daily pointers and receipts.
# Does not save/convert/close Excel, collect RSS, launch Trade or approve orders.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_LIVE_XLSB_BOOTSTRAP_'+$code)}
}
function GitBlob([byte[]]$data){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $combined=New-Object byte[] ($head.Length+$data.Length)
 [array]::Copy($head,0,$combined,0,$head.Length)
 [array]::Copy($data,0,$combined,$head.Length,$data.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($combined))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='735a3925d6b70f03747b2b592c76c1f8e06bab4a'
$pins=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='2fe73374a372eeaf1bcda0f4d19a5016bbfe0467'
 'no11_live_xlsb_contract.py'='97a34624c2cf46b78dd88f9206fa73649b2f3f3e'
 'no11_live_book_path_rebind.py'='e8c2bc6998a24f102c6c189e14cd4815f6dce162'
 'install_no11_live_xlsb_preflight.py'='385b280bc262735e5c8467938fad10067ab2bb55'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $pins.Count -eq 5) 'BAD_OFFLINE_CONTRACT'
 foreach($sha in $pins.Values){Need ([string]$sha -cmatch '^[a-f0-9]{40}$') 'PIN_FORMAT'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'GIT_HASH'
 Write-Host 'NO11_LIVE_XLSB_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_OPEN_BOOK_REGISTRATION_VERSION=2'
 Write-Host 'EXCEL_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_MISSING'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'BINDING_CHANGED'
$python=[string]$binding.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_MISSING'
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$temp=Join-Path $env:TEMP ('ark-open-books-v2-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $pins.Keys){
  $dest=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($dest))) -ceq [string]$pins[$name]) 'PINNED_SOURCE_MISMATCH'
 }
 Write-Host ('NO11_LIVE_XLSB_RELEASE='+$release)
 $args=@('-B','-X','utf8',(Join-Path $temp 'install_no11_live_xlsb_preflight.py'),
         '--store',$store)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 Write-Host ('ARK_LIVE_THREE_XLSB_PREFLIGHT='+$(if($Apply){'INSTALLED'}else{'AUDITED'}))
 Write-Host 'NO11_DATA_RECAPTURED=False'
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
