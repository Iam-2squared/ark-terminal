# Exact release for the 2026-11-10 11:16 Excel 1004 BD4 format write.
# No orders, no Excel cell writes, no RSS recapture, no LIVE approval.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_BD4_BOOTSTRAP_'+$code)}
}
function GitBlob([byte[]]$data){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $body=New-Object byte[] ($header.Length+$data.Length)
 [array]::Copy($header,0,$body,0,$header.Length)
 [array]::Copy($data,0,$body,$header.Length,$data.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($body))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='c3efd927fb09475ccf6807bf7138af2ee321ae7c'
$pins=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_transport_format_guard.py'='483bc2a264530551bda1a1526049c889d63268cb'
 'install_no11_transport_format_guard.py'='5d4a45e442a0de5c1a37d478658d08d3cefd26ba'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $pins.Count -eq 3) 'TEST_OPTIONS'
 foreach($hash in $pins.Values){Need ([string]$hash -cmatch '^[a-f0-9]{40}$') 'PIN_FORMAT'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'BLOB_HASH'
 Write-Host 'NO11_BD4_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_MISSING'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$python=[string]$binding.python
Need ([IO.Path]::IsPathRooted($python) -and
      (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_NOT_PINNED'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$temp=Join-Path $env:TEMP ('ARK-BD4-Format-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $pins.Keys){
  $file=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $file -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($file))) -ceq [string]$pins[$name]) 'PIN_MISMATCH'
 }
 $args=@('-B','-X','utf8',(Join-Path $temp 'install_no11_transport_format_guard.py'),
         '--store',$store)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_BLOCKED'
 Write-Host ('ARK_TRANSPORT_BD4_FORMAT_SAFE='+$(if($Apply){'INSTALLED'}else{'AUDIT_ONLY'}))
 Write-Host 'SAME_DAY_BROKER_APPROVAL_STILL_REQUIRED=True'
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
