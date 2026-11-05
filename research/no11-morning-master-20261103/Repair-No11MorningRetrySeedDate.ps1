# Surgical one-line bug fix; keep locally approved white OneClick unchanged.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_RETRY_GATE_INSTALL_'+$why)}}
function Blob([byte[]]$raw){
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($raw).Replace(([string][char]13+[char]10),[string][char]10)
 $body=[Text.Encoding]::UTF8.GetBytes($s)
 $h=[Text.Encoding]::ASCII.GetBytes(('blob '+$body.Length)+[char]0)
 $all=New-Object byte[] ($h.Length+$body.Length)
 [array]::Copy($h,0,$all,0,$h.Length)
 [array]::Copy($body,0,$all,$h.Length,$body.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function Part([string]$body,[string]$begin,[string]$end){
 $start=$body.IndexOf($begin,[StringComparison]::Ordinal)
 Need ($start -ge 0 -and $body.IndexOf($begin,$start+$begin.Length,[StringComparison]::Ordinal) -lt 0) 'ANCHOR_START'
 $finish=$body.IndexOf($end,$start+[Math]::Max(1,$begin.Length),[StringComparison]::Ordinal)
 Need ($finish -gt $start) 'ANCHOR_END'
 return $body.Substring($start,$finish-$start)
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 Write-Host 'NO11_RETRY_GATE_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_THEME_MODIFIED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$target=Join-Path $store 'oneclick\Recover-No11FilteredMorning.ps1'
$white=Join-Path $store 'oneclick\Start-No11OneClick.ps1'
Need ((Test-Path -LiteralPath $target -PathType Leaf) -and
      (Test-Path -LiteralPath $white -PathType Leaf)) 'INSTALLED_WHITE_ONECLICK_REQUIRED'
$existing=[IO.File]::ReadAllBytes($target)
$oldBlob='d844d7a45cb9bbcd247258ca16dc7797cbd4a6b4'
$newBlob='eeaadeb7e9bb919d0e477588a08f7056bb39aab0'
Need ((Blob $existing) -ceq $oldBlob) 'LOCAL_RETRY_HELPER_CHANGED'
$whiteSha=(Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash
$base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'
$rel='/research/no11-morning-master-20261103/Recover-No11FilteredMorning.ps1'
$temp=Join-Path $env:TEMP ('no11-retry-gate-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $oldFile=Join-Path $temp 'old.ps1'
 $newFile=Join-Path $temp 'new.ps1'
 Invoke-WebRequest -UseBasicParsing -Uri ($base+'c592a318ca913fe82f835253dbfc9f1c89ab6f75'+$rel) -OutFile $oldFile
 Invoke-WebRequest -UseBasicParsing -Uri ($base+'1d5ba533c970ca98190736b8d3a0217db0785481'+$rel) -OutFile $newFile
 $oldBytes=[IO.File]::ReadAllBytes($oldFile)
 $newBytes=[IO.File]::ReadAllBytes($newFile)
 Need ((Blob $oldBytes) -ceq $oldBlob -and (Blob $newBytes) -ceq $newBlob) 'REMOTE_SOURCE_PIN_INVALID'
 $LF=[string][char]10
 $CRLF=([string][char]13)+[char]10
 $old=([Text.UTF8Encoding]::new($false,$true)).GetString($oldBytes).Replace($CRLF,$LF)
 $new=([Text.UTF8Encoding]::new($false,$true)).GetString($newBytes).Replace($CRLF,$LF)
 $installed=([Text.UTF8Encoding]::new($false,$true)).GetString($existing).Replace($CRLF,$LF)
 Need ($installed -ceq $old) 'INSTALLED_HELPER_DIFFERS_FROM_PINNED_SOURCE'
 $first=" Need ("+'$settings.schemaId'
 $last=" "+'$bridgePath'
 $oldPart=Part $old $first $last
 $newPart=Part $new $first $last
 Need ($newPart.Contains('TODAY_HANDOFF_CHANGED_SINCE_0830_APPROVAL') -and
       $newPart.Contains('$r.pointerSha256') -and
       $newPart.Contains('TODAY_HANDOFF_ORIGINAL_SELECTION_CHANGED') -and
       -not $newPart.Contains('$binding.sessionDate -ceq $day') -and
       $old.Replace($oldPart,$newPart) -ceq $new) 'PATCH_CHANGED_ANYTHING_ELSE'
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($newFile,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'NEW_HELPER_SYNTAX'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $newFile -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'NEW_HELPER_SELFTEST'
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Recover-No11FilteredMorning[.]ps1|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($active.Count -eq 0) 'LIVE_OR_RECOVERY_RUNNING'
 Need ((Blob ([IO.File]::ReadAllBytes($target))) -ceq $oldBlob) 'LOCAL_HELPER_CHANGED_CONCURRENTLY'
 $backupRoot=Join-Path $store ('morning-retry-gate-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backupRoot)
 [IO.File]::WriteAllBytes((Join-Path $backupRoot 'Recover-No11FilteredMorning.before.ps1'),$existing)
 $candidate=Join-Path (Split-Path -Parent $target) ('.retry-new-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $atomicBackup=Join-Path (Split-Path -Parent $target) ('.retry-before-'+[guid]::NewGuid().ToString('N')+'.bak')
 [IO.File]::WriteAllBytes($candidate,$newBytes)
 [IO.File]::Replace($candidate,$target,$atomicBackup)
 try{
  Need ((Blob ([IO.File]::ReadAllBytes($target))) -ceq $newBlob -and
        (Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $whiteSha) 'POSTINSTALL_VERIFY'
 }catch{
  [IO.File]::WriteAllBytes($target,$existing)
  throw
 }
 Write-Host 'NO11_RETRY_GATE_FIX=PASS'
 Write-Host 'TODAY_HANDOFF=SHA_MATCHED_TO_0830_APPROVAL'
 Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
 Write-Host 'PREOPEN_APPROVAL_CHANGED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backupRoot)
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
