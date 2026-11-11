# Permanent latest-completed-session DATA update upgrade. No trading launch.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_COMPLETED_BOOTSTRAP_'+$code)}}
function BlobHash([byte[]]$raw){
 $h=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $all=New-Object byte[] ($h.Length+$raw.Length)
 [array]::Copy($h,0,$all,0,$h.Length)
 [array]::Copy($raw,0,$all,$h.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$commit='3e2ee622c9aa38686bd287784c486a8ceeed60df'
$files=[ordered]@{
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_update_path.py'='fc109357c56dff383e9e08d774a1c11f5eba4f82'
 'install_no11_completed_session_update.py'='55661323e0389d033eeb440462aef538b32a593c'
}
if($OfflineSelfTest){
 Need (-not $Apply -and $files.Count -eq 3) 'SELFTEST_ARGUMENTS'
 foreach($pin in $files.Values){Need ([string]$pin -cmatch '^[a-f0-9]{40}$') 'SOURCE_PIN'}
 Write-Host 'NO11_COMPLETED_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$b=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
Need ($b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $b.orderTransmission -eq $false) 'BINDING'
$py=[string]$b.python
Need ([IO.Path]::IsPathRooted($py) -and (Test-Path -LiteralPath $py -PathType Leaf)) 'PYTHON'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$commit+'/research/no11-morning-master-20261103/'
$temp=Join-Path $env:TEMP ('ARK-Completed-Update-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 foreach($name in $files.Keys){
  $file=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $file -UseBasicParsing
  Need ((BlobHash ([IO.File]::ReadAllBytes($file))) -ceq [string]$files[$name]) 'SOURCE_BYTES_CHANGED'
 }
 Write-Host ('NO11_COMPLETED_UPDATE_RELEASE='+$commit)
 $arguments=@('-B','-X','utf8',(Join-Path $temp 'install_no11_completed_session_update.py'),'--store',$store)
 if($Apply){$arguments+=@('--apply')}
 & $py @arguments
 Need ($LASTEXITCODE -eq 0) 'INSTALL_OR_AUDIT_FAILED'
 if($Apply){Write-Host 'NO11_NORMAL_DATA_UPDATE_UPGRADE=PASS'}
 else{Write-Host 'NO11_NORMAL_DATA_UPDATE_UPGRADE=AUDIT_ONLY'}
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
}
