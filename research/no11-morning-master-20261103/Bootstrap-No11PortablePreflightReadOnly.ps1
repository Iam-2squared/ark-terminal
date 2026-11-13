# Download-and-verify original No11 3-workbook/BD4/RSS preflight.
# Unlike a repository checkout assumption, this works from any Windows cmd/PS.
# No trade, Excel cell changes, same-day approval, data refresh or installed changes.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_PORTABLE_PREFLIGHT_'+$code)}
}
function GitBlob([byte[]]$value){
 $prefix=[Text.Encoding]::ASCII.GetBytes(('blob '+$value.Length)+[char]0)
 $data=New-Object byte[] ($prefix.Length+$value.Length)
 [array]::Copy($prefix,0,$data,0,$prefix.Length)
 [array]::Copy($value,0,$data,$prefix.Length,$value.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($data))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$ref='75f2c43248c4f5b168fb41c2e5f55f8fb7749886'
$blob='b02804545cceb592ea613de7cd8e9b48f5bab1b1'
$name='Check-No11StartPrerequisitesReadOnly20261111.ps1'
if($OfflineSelfTest){
 Need (($ref -cmatch '^[a-f0-9]{40}
 Write-Host 'NO11_PORTABLE_PREFLIGHT_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$temp=Join-Path $env:TEMP ('no11-readonly-preflight-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+
      '/research/no11-morning-master-20261103/'+$name
 Invoke-WebRequest -Uri $url -OutFile $temp -UseBasicParsing -ErrorAction Stop
 Need ((GitBlob ([IO.File]::ReadAllBytes($temp))) -ceq $blob) 'SOURCE_HASH_MISMATCH'
 Write-Host ('NO11_PORTABLE_PREFLIGHT_PINNED_COMMIT='+$ref)
 Write-Host 'NO11_PORTABLE_PREFLIGHT_SOURCE_VERIFIED=True'
 # The source's normal runtime path reads Excel COM properties and artifacts,
 # but DOES NOT alter them or send orders. Never pass a LIVE approval flag.
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $temp
 $exit=$LASTEXITCODE
 Need ($exit -eq 0) 'READONLY_PRECHECK_BLOCKED'
 Write-Host 'NO11_PORTABLE_PREFLIGHT=PASS_READ_ONLY'
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_PORTABLE_PREFLIGHT_[A-Z0-9_]+$'){
  $reason='NO11_PORTABLE_PREFLIGHT_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_PORTABLE_PREFLIGHT=BLOCKED|'+$reason)
 Write-Host 'NATIVE_TRADE_NOT_REQUESTED=True'
 exit 2
}finally{
 if(Test-Path -LiteralPath $temp -PathType Leaf){
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
 }
 Write-Host 'NO_INSTALLED_FILES_CHANGED_BY_BOOTSTRAP=True'
 Write-Host 'ORDER_TRANSMISSION=False'
}
) -and ($blob -cmatch '^[a-f0-9]{40}
 Write-Host 'NO11_PORTABLE_PREFLIGHT_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$temp=Join-Path $env:TEMP ('no11-readonly-preflight-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+
      '/research/no11-morning-master-20261103/'+$name
 Invoke-WebRequest -Uri $url -OutFile $temp -UseBasicParsing -ErrorAction Stop
 Need ((GitBlob ([IO.File]::ReadAllBytes($temp))) -ceq $blob) 'SOURCE_HASH_MISMATCH'
 Write-Host ('NO11_PORTABLE_PREFLIGHT_PINNED_COMMIT='+$ref)
 Write-Host 'NO11_PORTABLE_PREFLIGHT_SOURCE_VERIFIED=True'
 # The source's normal runtime path reads Excel COM properties and artifacts,
 # but DOES NOT alter them or send orders. Never pass a LIVE approval flag.
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $temp
 $exit=$LASTEXITCODE
 Need ($exit -eq 0) 'READONLY_PRECHECK_BLOCKED'
 Write-Host 'NO11_PORTABLE_PREFLIGHT=PASS_READ_ONLY'
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_PORTABLE_PREFLIGHT_[A-Z0-9_]+$'){
  $reason='NO11_PORTABLE_PREFLIGHT_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_PORTABLE_PREFLIGHT=BLOCKED|'+$reason)
 Write-Host 'NATIVE_TRADE_NOT_REQUESTED=True'
 exit 2
}finally{
 if(Test-Path -LiteralPath $temp -PathType Leaf){
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
 }
 Write-Host 'NO_INSTALLED_FILES_CHANGED_BY_BOOTSTRAP=True'
 Write-Host 'ORDER_TRANSMISSION=False'
}
) -and ($name -ceq 'Check-No11StartPrerequisitesReadOnly20261111.ps1')) 'PIN_SHAPE'
 Write-Host 'NO11_PORTABLE_PREFLIGHT_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$temp=Join-Path $env:TEMP ('no11-readonly-preflight-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+
      '/research/no11-morning-master-20261103/'+$name
 Invoke-WebRequest -Uri $url -OutFile $temp -UseBasicParsing -ErrorAction Stop
 Need ((GitBlob ([IO.File]::ReadAllBytes($temp))) -ceq $blob) 'SOURCE_HASH_MISMATCH'
 Write-Host ('NO11_PORTABLE_PREFLIGHT_PINNED_COMMIT='+$ref)
 Write-Host 'NO11_PORTABLE_PREFLIGHT_SOURCE_VERIFIED=True'
 # The source's normal runtime path reads Excel COM properties and artifacts,
 # but DOES NOT alter them or send orders. Never pass a LIVE approval flag.
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $temp
 $exit=$LASTEXITCODE
 Need ($exit -eq 0) 'READONLY_PRECHECK_BLOCKED'
 Write-Host 'NO11_PORTABLE_PREFLIGHT=PASS_READ_ONLY'
}catch{
 $reason=[string]$_.Exception.Message
 if($reason -cnotmatch '^NO11_PORTABLE_PREFLIGHT_[A-Z0-9_]+$'){
  $reason='NO11_PORTABLE_PREFLIGHT_UNVERIFIED_SOURCE_OR_RUNTIME'
 }
 Write-Host ('NO11_PORTABLE_PREFLIGHT=BLOCKED|'+$reason)
 Write-Host 'NATIVE_TRADE_NOT_REQUESTED=True'
 exit 2
}finally{
 if(Test-Path -LiteralPath $temp -PathType Leaf){
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
 }
 Write-Host 'NO_INSTALLED_FILES_CHANGED_BY_BOOTSTRAP=True'
 Write-Host 'ORDER_TRANSMISSION=False'
}
