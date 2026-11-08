# Official No11: one version-pinned delivery of updated native launcher,
# 47-slot weekly/daily/previous-minute collectors and interrupted-job recovery.
# The installed user's WHITE OneClick GUI is never overwritten.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$v,[string]$c){if(-not $v){throw ('NO11_UNIFIED_BOOTSTRAP_'+$c)}}
function BlobHash([byte[]]$raw){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$raw.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($raw,0,$all,$header.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_selection_status.py'='8817fce287624083c465b7e8caacc12a4a81d1af'
 'patch_no11_transport_resilience.py'='b74b52111c6c786049623df093623ac4ff0ed92e'
 'Run-No11ResumableNightly.ps1'='5fb604c9316f7f483800c657b0c44306582973ac'
 'install_no11_week_resilience.py'='633e68c8aabf37d61f08dfe36f05af9e9ed33f24'
 'no11_update_path.py'='f67f214dc672c384707b0c12d37a130481796133'
 'install_no11_launcher_update.py'='df2fe77b08fa30958f63e0070964d980a02706d4'
 'install_no11_unified_update.py'='c20284ae375a31106be5cea4b0715dfe448e6b71'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_MUST_BE_READ_ONLY'
 Need ($files.Count -eq 8 -and $files.Contains('install_no11_unified_update.py')) 'FILES_MANIFEST'
 foreach($item in $files.Values){Need ([string]$item -cmatch '^[a-f0-9]{40}$') 'BLOB_PIN'}
 Write-Host 'NO11_UNIFIED_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_ONECLICK_GUI_CHANGED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingPath=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingPath -PathType Leaf) 'EXISTING_INSTALL_REQUIRED'
$b=Get-Content -LiteralPath $bindingPath -Raw -Encoding UTF8|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $b.orderTransmission -eq $false) 'BINDING_CONTRACT'
$python=[string]$b.python
Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'BOUND_PYTHON'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$commit='dcfc9a17727812f9f6440d849f11de12771c3689'
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$commit+'/research/no11-morning-master-20261103/'
$tmp=Join-Path $env:TEMP ('ARK-No11-Release-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($tmp)
try{
 foreach($name in $files.Keys){
  $file=Join-Path $tmp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $file -UseBasicParsing -ErrorAction Stop
  $actual=BlobHash ([IO.File]::ReadAllBytes($file))
  Need ($actual -ceq [string]$files[$name]) ('RELEASE_SOURCE_CHANGED_'+$name.Replace('.','_').ToUpperInvariant())
 }
 Write-Host ('NO11_UNIFIED_RELEASE_PIN='+$commit)
 $tool=Join-Path $tmp 'install_no11_unified_update.py'
 $args=@('-B','-X','utf8',$tool,'--store',$store,'--source-dir',$tmp)
 if($Apply){$args+=@('--apply')}
 & $python @args
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){
  Write-Host 'NO11_UNIFIED_LAUNCHER_UPDATE=PASS_OR_ALREADY_APPLIED'
  Write-Host 'RUN_NEXT_DATA_UPDATE_FROM_THE_EXISTING_WHITE_ONECLICK=True'
 }else{
  Write-Host 'NO11_UNIFIED_LAUNCHER_UPDATE=AUDIT_ONLY'
 }
}finally{
 if(Test-Path -LiteralPath $tmp -PathType Container){
  Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
