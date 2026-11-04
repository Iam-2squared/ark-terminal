# Transactional preopen integration for the user's locally approved white UI.
# Replaces NO UI/theme source. Only 4 named trade/control-flow anchors change.
# Original trade/Excel/ledger/marker code and local UI colors are protected.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_PREOPEN_INSTALL_'+$why)}
}
function Blob([byte[]]$raw){
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $crlf=([string][char]13)+([string][char]10)
 $canonical=[Text.Encoding]::UTF8.GetBytes($s.Replace($crlf,[string][char]10))
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$canonical.Length)+[char]0)
 $all=New-Object byte[] ($head.Length+$canonical.Length)
 [array]::Copy($head,0,$all,0,$head.Length)
 [array]::Copy($canonical,0,$all,$head.Length,$canonical.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function NeedOnce([string]$body,[string]$anchor,[string]$why){
 Need (([regex]::Matches($body,[regex]::Escape($anchor))).Count -eq 1) $why
}
function Parse([string]$f){
 $t=$null;$e=$null
 [void][Management.Automation.Language.Parser]::ParseFile($f,[ref]$t,[ref]$e)
 Need ($e.Count -eq 0) 'SYNTAX'
}
function AssertNoLiveProcess{
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly'
 })
 Need ($active.Count -eq 0) 'CLOSE_ONECLICK_AND_ARK_BEFORE_APPLY'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_MODE'
 Write-Host 'NO11_PREOPEN_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'ONECLICK_WHITE_THEME_CHANGED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$oneclick=Join-Path $store 'oneclick'
$target=Join-Path $oneclick 'Start-No11OneClick.ps1'
$worker=Join-Path $oneclick 'Start-No11PreopenStandby.ps1'
Need ((Test-Path -LiteralPath $target -PathType Leaf) -and
      (Test-Path -LiteralPath (Join-Path $oneclick 'oneclick_status.py') -PathType Leaf)) 'ONECLICK_NOT_INSTALLED'
AssertNoLiveProcess
$ref='6ff84f979b92b72aa9b3d72131e12430768f6f43'
$pins=[ordered]@{
 'Start-No11PreopenStandby.ps1'='bc474fdf36c903ccb87018f2549f6a6b7ca398df'
 'Start-No11OneClick.ps1'='e4cb96d6b7192b25ce0298cb91632e3f8db611a7'
}
$temp=Join-Path $env:TEMP ('ark-preopen-pins-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $sources=@{}
 foreach($name in $pins.Keys){
  $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+'/research/no11-morning-master-20261103/'+$name
  $file=Join-Path $temp $name
  Invoke-WebRequest -Uri $uri -OutFile $file -UseBasicParsing -ErrorAction Stop
  $raw=[IO.File]::ReadAllBytes($file)
  Need ((Blob $raw) -ceq $pins[$name]) 'REMOTE_PIN_INVALID'
  Parse $file
  $sources[$name]=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 }
 $scriptPath=Join-Path $temp 'Start-No11PreopenStandby.ps1'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'WORKER_SELFTEST'
 $whiteBytes=[IO.File]::ReadAllBytes($target)
 $whiteHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
 $hasBom=$whiteBytes.Length -ge 3 -and $whiteBytes[0] -eq 239 -and $whiteBytes[1] -eq 187 -and $whiteBytes[2] -eq 191
 $offset=if($hasBom){3}else{0}
 $utf8=[Text.UTF8Encoding]::new($false,$true)
 $white=$utf8.GetString($whiteBytes,$offset,$whiteBytes.Length-$offset)
 $crlf=([string][char]13)+([string][char]10)
 $lf=[string][char]10
 $newline=if($white.Contains($crlf)){$crlf}else{$lf}
 $local=$white.Replace($crlf,$lf)
 $reference=$sources['Start-No11OneClick.ps1'].Replace($crlf,$lf)
 $marker='# ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1'
 if($local.Contains($marker)){
  Need ((Test-Path -LiteralPath $worker -PathType Leaf) -and
        (Blob ([IO.File]::ReadAllBytes($worker))) -ceq $pins['Start-No11PreopenStandby.ps1']) 'PARTIAL_OR_CHANGED_PREOPEN'
  Write-Host 'NO11_PREOPEN_STANDBY_INSTALL=ALREADY_APPLIED'
  Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need (-not (Test-Path -LiteralPath $worker)) 'UNKNOWN_PREEXISTING_PREOPEN_WORKER'
 # Extract the exact new functions from a verified upstream blob. Do NOT use
 # that blob as a replacement for the locally approved white OneClick.
 $refStart=$reference.IndexOf($marker,[StringComparison]::Ordinal)
 $refEnd=$reference.IndexOf('function RefreshUi{',$refStart,[StringComparison]::Ordinal)
 Need ($refStart -ge 0 -and $refEnd -gt $refStart) 'PINNED_FUNCTIONS_MISSING'
 $insert=$reference.Substring($refStart,$refEnd-$refStart)
 NeedOnce $local 'function RefreshUi{' 'LOCAL_REFRESH_ANCHOR_CHANGED'
 $patched=$local.Replace('function RefreshUi{',$insert+'function RefreshUi{')
 $trading="  "+'$trading=if($s.mode -ceq ''AFTER_CLOSE''){''Closed for today''}elseif($s.canRequestTrade -eq $true){''Awaiting same-day approval''}else{''Not available''}'
 $recovery="  "+'$recovery=''No current recovery request'''
 NeedOnce $reference $trading 'PINNED_TRADING_ANCHOR_MISSING'
 NeedOnce $patched $trading 'LOCAL_TRADING_ANCHOR_CHANGED'
 $from=$reference.IndexOf($trading,[StringComparison]::Ordinal)+$trading.Length
 $to=$reference.IndexOf($recovery,$from,[StringComparison]::Ordinal)
 Need ($to -gt $from) 'PINNED_STATUS_ADDENDUM_MISSING'
 $addon=$reference.Substring($from,$to-$from).TrimEnd([char]10)
 Need ($addon.Contains('$preopen=CanQueuePreopen $s') -and
       $addon.Contains('$reserved=PreopenReserved $s')) 'PINNED_STATUS_ADDENDUM_INVALID'
 $patched=$patched.Replace($trading,$trading+$addon)
 $oldEnable='  $trade.Enabled=($s.canRequestTrade -eq $true)'
 $newEnable='  $trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen) -and (-not $reserved)'
 NeedOnce $patched $oldEnable 'LOCAL_ENABLE_ANCHOR_CHANGED'
 NeedOnce $reference $newEnable 'PINNED_ENABLE_INVALID'
 $patched=$patched.Replace($oldEnable,$newEnable)
 $oldClick='$trade.Add_Click({' + $lf + ' $s=GetStatus' + $lf +
            ' if($s.canRequestTrade -ne $true){RefreshUi;return}'
 $refClickStart=$reference.IndexOf('$trade.Add_Click({',[StringComparison]::Ordinal)
 $clickEndMarker=' if($s.canRequestTrade -ne $true){RefreshUi;return}'
 $refClickEnd=$reference.IndexOf($clickEndMarker,$refClickStart,[StringComparison]::Ordinal)
 Need ($refClickStart -ge 0 -and $refClickEnd -gt $refClickStart) 'PINNED_CLICK_MISSING'
 $newClick=$reference.Substring($refClickStart,$refClickEnd-$refClickStart+$clickEndMarker.Length)
 Need ($newClick.Contains('NO11_PREOPEN_STANDBY=ARMED') -and
       $newClick.Contains('if(CanQueuePreopen $s)')) 'PINNED_CLICK_INVALID'
 NeedOnce $patched $oldClick 'LOCAL_CLICK_ANCHOR_CHANGED'
 $patched=$patched.Replace($oldClick,$newClick)
 NeedOnce $patched $marker 'PATCH_MARKER_MISSING'
 # Protect the entire pre-existing color/layout region verbatim.
 $styleStart='$form.BackColor='
 $styleEnd='function UiReason('
 $s0=$local.IndexOf($styleStart,[StringComparison]::Ordinal)
 $s1=$local.IndexOf($styleEnd,$s0,[StringComparison]::Ordinal)
 $p0=$patched.IndexOf($styleStart,[StringComparison]::Ordinal)
 $p1=$patched.IndexOf($styleEnd,$p0,[StringComparison]::Ordinal)
 Need ($s0 -ge 0 -and $s1 -gt $s0 -and $p0 -ge 0 -and $p1 -gt $p0 -and
       $local.Substring($s0,$s1-$s0) -ceq $patched.Substring($p0,$p1-$p0)) 'WHITE_THEME_OR_LAYOUT_CHANGED'
 $patched=$patched.Replace($lf,$newline)
 $candidateBytes=$utf8.GetBytes($patched)
 if($hasBom){
  $result=New-Object byte[] ($candidateBytes.Length+3)
  [array]::Copy($whiteBytes,0,$result,0,3)
  [array]::Copy($candidateBytes,0,$result,3,$candidateBytes.Length)
 }else{$result=$candidateBytes}
 $candidate=Join-Path $oneclick ('preopen-ui-candidate-'+[guid]::NewGuid().ToString('N')+'.ps1')
 [IO.File]::WriteAllBytes($candidate,$result)
 Parse $candidate
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'ONECLICK_SELFTEST'
 AssertNoLiveProcess
 Need ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ceq $whiteHash) 'LOCAL_UI_CHANGED_CONCURRENTLY'
 $backup=Join-Path $store ('preopen-0830-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'WhiteOneClick.before.ps1'),$whiteBytes)
 $workerPlaced=$false
 $uiPlaced=$false
 try{
  [IO.File]::WriteAllBytes($worker,[IO.File]::ReadAllBytes($scriptPath))
  $workerPlaced=$true
  $replaceBackup=Join-Path $backup 'WhiteOneClick.atomic-replace-original.ps1'
  [IO.File]::Replace($candidate,$target,$replaceBackup)
  $uiPlaced=$true
  $after=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$expectedHash=([BitConverter]::ToString($sha.ComputeHash($result))).Replace('-','')}
  finally{$sha.Dispose()}
  Need ($after -ceq $expectedHash) 'POSTINSTALL_HASH'
  Write-Host 'NO11_PREOPEN_STANDBY_INSTALL=PASS'
  Write-Host 'STANDBY_WINDOW_JST=08:30-08:59'
  Write-Host 'AUTO_REQUEST_JST=09:00'
  Write-Host 'NATIVE_0900_BROKER_GATES_UNCHANGED=True'
  Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
  Write-Host 'ONECLICK_LAYOUT_CHANGED=False'
  Write-Host 'SAME_DAY_EXPLICIT_APPROVAL_REQUIRED=True'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  Write-Host ('BACKUP_ROOT='+$backup)
 }catch{
  if($uiPlaced){[IO.File]::WriteAllBytes($target,$whiteBytes)}
  if($workerPlaced -and (Test-Path -LiteralPath $worker)){Remove-Item -LiteralPath $worker -Force}
  throw
 }
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
}
