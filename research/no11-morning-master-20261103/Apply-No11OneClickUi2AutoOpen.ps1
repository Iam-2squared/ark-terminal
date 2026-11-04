# Surgical PowerShell hotfix: preserve the locally approved white OneClick.
# No broker, Excel, frozen strategy, ledger or stop-marker modifications.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){
 if(-not $ok){throw ('NO11_ONECLICK_UI2_INSTALL_'+$why)}
}
function GitBlob([byte[]]$raw){
 $text=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $crlf=([string][char]13)+([string][char]10)
 $canonical=[Text.Encoding]::UTF8.GetBytes($text.Replace($crlf,[string][char]10))
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$canonical.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$canonical.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($canonical,0,$all,$header.Length,$canonical.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function Parse([string]$file){
 $tok=$null;$errs=$null
 [void][Management.Automation.Language.Parser]::ParseFile($file,[ref]$tok,[ref]$errs)
 Need ($errs.Count -eq 0) 'POWERSHELL_PARSE'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 Write-Host 'NO11_ONECLICK_UI2_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'ONECLICK_UI_MODIFIED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$oneclick=Join-Path $store 'oneclick'
$target=Join-Path $oneclick 'Start-No11OneClick.ps1'
$watch=Join-Path $oneclick 'Watch-No11OneClickTradeUi.ps1'
Need (Test-Path -LiteralPath $target -PathType Leaf) 'ONECLICK_NOT_INSTALLED'
function AssertStopped{
 $active=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Watch-No11OneClickTradeUi[.]ps1'
 })
 Need ($active.Count -eq 0) 'CLOSE_ONECLICK_AND_ARK_ENGINE_FIRST'
}
AssertStopped
$ref='17d344d700dc77a0af30af5b0c4aadbc0b56d97e'
$watchBlob='09750f93dcb1f10c3f0df7e4082d86ec92da61b8'
$url='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+'/research/no11-morning-master-20261103/Watch-No11OneClickTradeUi.ps1'
$tmp=Join-Path $env:TEMP ('ark-ui2-watch-'+[guid]::NewGuid().ToString('N')+'.ps1')
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -ErrorAction Stop
 $watchBytes=[IO.File]::ReadAllBytes($tmp)
 Need ((GitBlob $watchBytes) -ceq $watchBlob) 'WATCH_SOURCE_HASH_CHANGED'
 Parse $tmp
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tmp -OfflineSelfTest|Out-Null
 Need ($LASTEXITCODE -eq 0) 'WATCH_OFFLINE_SELFTEST'
 $hadWatch=Test-Path -LiteralPath $watch -PathType Leaf
 if($hadWatch){
  Need ((GitBlob ([IO.File]::ReadAllBytes($watch))) -ceq $watchBlob) 'LOCALLY_MODIFIED_WATCHER'
 }
 $orig=[IO.File]::ReadAllBytes($target)
 $origHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
 $bom=$orig.Length -ge 3 -and $orig[0] -eq 239 -and $orig[1] -eq 187 -and $orig[2] -eq 191
 $offset=if($bom){3}else{0}
 $encoding=[Text.UTF8Encoding]::new($false,$true)
 $source=$encoding.GetString($orig,$offset,$orig.Length-$offset)
 $marker='ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1'
 if($source.Contains($marker)){
  Need $hadWatch 'PATCH_PRESENT_BUT_WATCHER_MISSING'
  Write-Host 'NO11_ONECLICK_UI2_AUTOOPEN=ALREADY_APPLIED'
  Write-Host 'ONECLICK_THEME_REPLACED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 $crlf=([string][char]13)+([string][char]10)
 $lf=[string][char]10
 $newline=if($source.Contains($crlf)){$crlf}else{$lf}
 $normal=$source.Replace($crlf,$lf)
 $anchor=@'
 Need ($null -ne $p -and $p.Id -gt 0) 'CHILD_NOT_STARTED'
 return $p.Id
'@
 $replacement=@'
 Need ($null -ne $p -and $p.Id -gt 0) 'CHILD_NOT_STARTED'
 # ARK_NO11_ONECLICK_TRADE_UI2_AUTOOPEN_WATCH_V1
 # The native Trade launcher opens UI2; retry ONLY the read-only UI if it failed.
 if($runMode -eq 'Trade'){
  $watch=Join-Path $PSScriptRoot 'Watch-No11OneClickTradeUi.ps1'
  $script:LastUi2Monitor='NOT_INSTALLED'
  if(Test-Path -LiteralPath $watch -PathType Leaf){
   $watchArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',(Quote $watch),'-NativeLog',(Quote $files[0]))
   $watchLogs=LogFiles 'Ui2'
   try{
    $monitor=Start-Process -FilePath 'powershell.exe' -ArgumentList ($watchArgs -join ' ') -WorkingDirectory $PSScriptRoot -RedirectStandardOutput $watchLogs[0] -RedirectStandardError $watchLogs[1] -PassThru -WindowStyle Hidden
    $script:LastUi2Monitor=if($null -ne $monitor -and $monitor.Id -gt 0){'STARTED'}else{'MONITOR_UNAVAILABLE'}
   }catch{
    $script:LastUi2Monitor='MONITOR_UNAVAILABLE'
   }
  }
 }
 return $p.Id
'@
 $anchor=$anchor.Replace($crlf,$lf)
 $replacement=$replacement.Replace($crlf,$lf)
 Need (([regex]::Matches($normal,[regex]::Escape($anchor))).Count -eq 1) 'LOCAL_STARTORIGINAL_ANCHOR_NOT_FOUND'
 $updated=$normal.Replace($anchor,$replacement).Replace($lf,$newline)
 $body=$encoding.GetBytes($updated)
 if($bom){
  $result=New-Object byte[] ($body.Length+3)
  [array]::Copy($orig,0,$result,0,3)
  [array]::Copy($body,0,$result,3,$body.Length)
 }else{$result=$body}
 $candidate=Join-Path $oneclick ('Start-No11OneClick.ui2candidate-'+[guid]::NewGuid().ToString('N')+'.ps1')
 [IO.File]::WriteAllBytes($candidate,$result)
 Parse $candidate
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $candidate -OfflineSelfTest|Out-Null
 Need ($LASTEXITCODE -eq 0) 'ONECLICK_OFFLINE_SELFTEST'
 AssertStopped
 Need ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ceq $origHash) 'CONCURRENT_ONECLICK_CHANGE'
 $backup=Join-Path $store ('oneclick-ui2-autoopen-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Start-No11OneClick.before.ps1'),$orig)
 $watchInstalled=$false
 $uiInstalled=$false
 try{
  if(-not $hadWatch){
   [IO.File]::WriteAllBytes($watch,$watchBytes)
   $watchInstalled=$true
  }
  # .NET Framework on Windows PowerShell 5.1 requires a valid backup path.
  # Never pass $null as File.Replace's third argument.
  $replaceBackup=Join-Path $backup 'Start-No11OneClick.replace-original.ps1'
  [IO.File]::Replace($candidate,$target,$replaceBackup)
  $uiInstalled=$true
  $resultHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  $expectedHash=[BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($result)).Replace('-','')
  Need ($resultHash -ceq $expectedHash) 'POSTWRITE_VERIFICATION'
  Write-Host 'NO11_ONECLICK_UI2_AUTOOPEN=PASS'
  Write-Host 'NATIVE_TRADE_AUTOOPEN=PRESERVED'
  Write-Host 'UI2_FAILURE_RETRY=READ_ONLY_ONCE'
  Write-Host 'WHITE_ONECLICK_THEME_REPLACED=False'
  Write-Host 'EXCEL_TOUCHED=False'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  Write-Host ('BACKUP_ROOT='+$backup)
 }catch{
  if($uiInstalled){[IO.File]::WriteAllBytes($target,$orig)}
  if($watchInstalled -and (Test-Path -LiteralPath $watch -PathType Leaf)){
   Remove-Item -LiteralPath $watch -Force
  }
  throw
 }
}finally{
 if(Test-Path -LiteralPath $tmp -PathType Leaf){Remove-Item -LiteralPath $tmp -Force}
}
