# One-time graphical theme update for an already-installed ARK OneClick.
# Does not touch Excel, native Trade/Weekly routes, broker settings, live ledger or markers.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OfflineSelfTest){
 if($Apply){throw 'NO11_ONECLICK_THEME_SELFTEST_FLAGS'}
 Write-Host 'NO11_ONECLICK_THEME_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if(-not $Apply){throw 'NO11_ONECLICK_THEME_EXPLICIT_APPLY_REQUIRED'}
$oneclick=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\oneclick'
$target=Join-Path $oneclick 'Start-No11OneClick.ps1'
if(-not (Test-Path -LiteralPath $target -PathType Leaf)){throw 'NO11_ONECLICK_THEME_NOT_INSTALLED'}
$active=@(Get-CimInstance Win32_Process | Where-Object {
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(powershell|pwsh)(\.exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick\.ps1'
})
if($active.Count -gt 0){throw 'NO11_ONECLICK_THEME_CLOSE_ONECLICK_WINDOW_FIRST'}
function BlobHash([byte[]]$bytes){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$bytes.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($bytes,0,$all,$header.Length,$bytes.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
$oldBlob='6d1f91d2470e96df28a181f5ebd89b0151fabf67'
$newBlob='4a8c299cfc80d7c116b5b997c5f3aa27f074ab48'
$source=[IO.File]::ReadAllBytes($target)
$before=BlobHash $source
if($before -ceq $newBlob){
 Write-Host 'NO11_ONECLICK_THEME=ALREADY_INSTALLED'
 Write-Host 'ORIGINAL_LIVE_ENGINE_CHANGED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if($before -cne $oldBlob){throw 'NO11_ONECLICK_THEME_LOCAL_UI_CHANGED_REQUIRES_REVIEW'}
$url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/de0fbc04313334020d625204756b6536b7f62715/research/no11-morning-master-20261103/Start-No11OneClick.ps1'
$staging=Join-Path $oneclick ('theme-candidate-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 Invoke-WebRequest -Uri $url -OutFile $staging -UseBasicParsing -ErrorAction Stop
 $replacement=[IO.File]::ReadAllBytes($staging)
 if((BlobHash $replacement) -cne $newBlob){throw 'NO11_ONECLICK_THEME_REMOTE_SOURCE_HASH_CHANGED'}
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($staging,[ref]$tokens,[ref]$errors)
 if($errors.Count -ne 0){throw 'NO11_ONECLICK_THEME_POWERSHELL_PARSE_FAILED'}
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $staging -OfflineSelfTest | Out-Null
 if($LASTEXITCODE -ne 0){throw 'NO11_ONECLICK_THEME_OFFLINE_SELFTEST_FAILED'}
 if((BlobHash ([IO.File]::ReadAllBytes($target))) -cne $before){throw 'NO11_ONECLICK_THEME_CONCURRENT_MODIFICATION'}
 $backup=Join-Path $oneclick ('Start-No11OneClick.before-theme-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.ps1')
 [IO.File]::Replace($staging,$target,$backup)
 if((BlobHash ([IO.File]::ReadAllBytes($target))) -cne $newBlob){throw 'NO11_ONECLICK_THEME_REPLACEMENT_UNVERIFIED'}
 Write-Host 'NO11_ONECLICK_THEME=PASS'
 Write-Host 'THEME=GRAPHITE_ICEBLUE'
 Write-Host 'READABLE_STATUS=ENABLED'
 Write-Host 'FLAT_BUTTONS=ENABLED'
 Write-Host 'BACKUP_CREATED=True'
 Write-Host 'ORIGINAL_LIVE_ENGINE_CHANGED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 Write-Host 'NO11_ONECLICK_THEME=BLOCKED'
 throw
}finally{
 if(Test-Path -LiteralPath $staging){Remove-Item -LiteralPath $staging -Force}
}
