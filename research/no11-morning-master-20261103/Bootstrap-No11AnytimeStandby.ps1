# Audit-first, source-pinned, after-hours deploy of same-day 00:00–08:59 standby.
# Neither this bootstrap nor the installer can launch Trade or touch Excel.
param(
 [switch]$Apply,
 [switch]$IConfirmArkStoppedAndBrokerOrdersPositionsReviewed,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$v,[string]$code){
 if(-not $v){throw ('NO11_ANYTIME_BOOTSTRAP_'+$code)}
}
function Blob([byte[]]$raw){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $buffer=New-Object byte[] ($head.Length+$raw.Length)
 [array]::Copy($head,0,$buffer,0,$head.Length)
 [array]::Copy($raw,0,$buffer,$head.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($buffer))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
# Every downloaded module was reviewed at exactly this source commit.
$commit='004772db151598d493b745bcb311bac4e1659cc8'
$files=[ordered]@{
 'install_no11_anytime_preopen.py'='780c8011a0332c2fa4e2813e7cec7b25863e96e1'
 'no11_anytime_preopen.py'='e5b1c2c5263e525092a1028d9c734c2a14f4efac'
 'no11_nightly_resume.py'='6c3668c47991e1407464c7049cd662ff9985ad35'
 'no11_oneclick_display_transform.py'='4c8ce6fb796320c00e80f0385437162925cb3921'
 'no11_oneclick_display_v2.py'='f285ae780e9e2605003c23c3729b5099adbbf3d3'
 'install_no11_oneclick_display_v2.py'='1b4923fb948a0e30fcfe8cb4a281f77a4e4fdef5'
 'install_no11_oneclick_display_overlay_compat.py'='e234c9fee85703329d9cd41444e64660468bee16'
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $IConfirmArkStoppedAndBrokerOrdersPositionsReviewed) 'SELFTEST_FLAGS'
 Need ($commit -cmatch '^[a-f0-9]{40}$' -and $files.Count -eq 7) 'PIN_LIST'
 foreach($entry in $files.GetEnumerator()){
  Need ($entry.Key -cmatch '^[a-z0-9_]+[.]py$' -and
        $entry.Value -cmatch '^[a-f0-9]{40}$') 'PIN_SHAPE'
 }
 Write-Host 'NO11_ANYTIME_BOOTSTRAP_OFFLINE_SELFTEST=PASS'
 Write-Host 'PC_INSTALL_PERFORMED=False'
 Write-Host 'TRADE_STARTED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need (-not $IConfirmArkStoppedAndBrokerOrdersPositionsReviewed -or $Apply) 'CONFIRMATION_ONLY_WITH_APPLY'
if($Apply){
 Need $IConfirmArkStoppedAndBrokerOrdersPositionsReviewed 'MANUAL_STOP_AND_BROKER_REVIEW_REQUIRED'
 $now=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
 Need (-not ($now.ToString('HH:mm:ss') -ge '08:00:00' -and
             $now.ToString('HH:mm:ss') -le '15:40:00')) 'AFTER_HOURS_ONLY'
}
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$temp=Join-Path $env:TEMP ('ark-no11-anytime-pinned-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 Need (Test-Path -LiteralPath $store -PathType Container) 'LOCAL_ONECLICK_REQUIRED'
 $bindingFile=Join-Path $store 'automatic-inputs.json'
 Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'BINDING_MISSING'
 $binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8 | ConvertFrom-Json
 Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
       $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
 $python=[string]$binding.python
 Need ([IO.Path]::IsPathRooted($python)) 'PYTHON_NOT_ABSOLUTE'
 $python=[IO.Path]::GetFullPath($python)
 Need (([IO.Path]::GetFileName($python) -ieq 'python.exe') -and
       (Test-Path -LiteralPath $python -PathType Leaf) -and
       (((Get-Item -LiteralPath $python -Force).Attributes -band
          [IO.FileAttributes]::ReparsePoint) -eq 0)) 'PYTHON_BINARY_UNVERIFIED'
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$commit+
       '/research/no11-morning-master-20261103/'
 foreach($name in $files.Keys){
  $dest=Join-Path $temp $name
  Invoke-WebRequest -Uri ($base+$name) -OutFile $dest -UseBasicParsing -ErrorAction Stop
  $actual=Blob ([IO.File]::ReadAllBytes($dest))
  Need ($actual -ceq [string]$files[$name]) ('PIN_CHANGED_'+$name.Replace('.','_').ToUpperInvariant())
 }
 Write-Host ('NO11_ANYTIME_PINNED_SOURCE_COMMIT='+$commit)
 $installer=Join-Path $temp 'install_no11_anytime_preopen.py'
 $arguments=@('-B','-X','utf8',$installer,'--store',$store)
 if($Apply){$arguments+='--apply'}
 & $python @arguments
 Need ($LASTEXITCODE -eq 0) 'INSTALLER_BLOCKED_PRESERVE_RECEIPTS'
 if($Apply){
  Write-Host 'NO11_ANYTIME_BOOTSTRAP=APPLY_VERIFIED'
 }else{
  Write-Host 'NO11_ANYTIME_BOOTSTRAP=AUDIT_VERIFIED_NO_WRITES'
 }
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_ANYTIME_BOOTSTRAP_[A-Z0-9_]+$'){
  $reason='NO11_ANYTIME_BOOTSTRAP_UNVERIFIED_SOURCE_OR_IO'
 }
 Write-Host ('NO11_ANYTIME_BOOTSTRAP=BLOCKED|'+$reason)
 Write-Host 'PRESERVE_OLD_RECEIPTS_ORDERS_AND_CLAIMS=True'
 exit 2
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Force -Recurse -ErrorAction SilentlyContinue
 }
 Write-Host 'TRADE_STARTED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}
