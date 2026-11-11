# Install the XLSB-capable DATA registry for the three existing open workbooks.
# No workbook Open/Save/SaveAs/Close, no trading approval and no RSS capture.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$Ok,[string]$Why){if(-not $Ok){throw ('NO11_DATA_BOOK_BOOTSTRAP_'+$Why)}}
function GitBlob([byte[]]$Bytes){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$Bytes.Length)+[char]0)
 $all=New-Object byte[] ($head.Length+$Bytes.Length)
 [array]::Copy($head,0,$all,0,$head.Length)
 [array]::Copy($Bytes,0,$all,$head.Length,$Bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$release='b9ae17d9976e93cf2f78a34d9124dc16807c6a0e'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_nightly_resume_workeraware.py'='892477d57e0fe1dc6b1774b238fc01ea7d113ffc'
 'nightly_workbook_compat.py'='2a91aafdfd41bae90ae553d7ce4e4c17dd76ecea'
 'No11DataWorkbookRegistry.ps1'='46baff432eefbc63062d3ff36d6a5090a30d935e'
 'install_no11_data_workbook_registration.py'='58fe2a5f32712e5354fa9219c6962025f87220b4'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 5) 'SELFTEST_ARGS'
 foreach($sha in $files.Values){Need ([string]$sha -cmatch '^[a-f0-9]{40}$') 'SOURCE_PIN'}
 Need ((GitBlob (New-Object byte[] 0)) -ceq 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391') 'HASH_IMPLEMENTATION'
 Write-Host 'NO11_DATA_BOOK_BOOTSTRAP_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$binding=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $binding -PathType Leaf) 'BINDING_MISSING'
$b=Get-Content -LiteralPath $binding -Raw -Encoding UTF8|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $b.orderTransmission -eq $false) 'BINDING_MODE'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'BOUND_PYTHON'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$release+'/research/no11-morning-master-20261103/'
$temp=Join-Path $env:TEMP ('ARK-Data-Books-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $files.Keys){
  $destination=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $destination -UseBasicParsing -ErrorAction Stop
  Need ((GitBlob ([IO.File]::ReadAllBytes($destination))) -ceq [string]$files[$name]) 'RELEASE_HASH_MISMATCH'
 }
 Write-Host ('NO11_DATA_BOOK_RELEASE='+$release)
 $arguments=@('-B','-X','utf8',(Join-Path $temp 'install_no11_data_workbook_registration.py'),
              '--store',$store,'--source-dir',$temp)
 if($Apply){$arguments+=@('--apply')}
 & $python @arguments
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'ARK_DATA_WORKBOOK_REGISTRATION=PASS'}
 else{Write-Host 'ARK_DATA_WORKBOOK_REGISTRATION=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
}
