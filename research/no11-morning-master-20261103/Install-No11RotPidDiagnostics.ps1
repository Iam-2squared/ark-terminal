# Install ONE fail-closed PID-diagnostic patch for the existing Clean collector.
# No day-scoped approval, no retry, no Excel, no order, no UI file mutation.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$label){
 if(-not $ok){throw ('NO11_PID_DIAG_INSTALL_'+$label)}
}
function GitBlob([byte[]]$raw){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $joined=New-Object byte[] ($head.Length+$raw.Length)
 [array]::Copy($head,0,$joined,0,$head.Length)
 [array]::Copy($raw,0,$joined,$head.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($joined))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function CanonicalBlob([byte[]]$bytes){
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($bytes)
 $s=$s.Replace(([string][char]13+[char]10),[string][char]10)
 Need (-not $s.Contains([char]13)) 'UNKNOWN_LINE_ENDING'
 $newBytes=[Text.Encoding]::UTF8.GetBytes($s)
 if($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191){
  $bom=[byte[]]@(239,187,191)
  $joined=New-Object byte[] ($bom.Length+$newBytes.Length)
  [array]::Copy($bom,0,$joined,0,$bom.Length)
  [array]::Copy($newBytes,0,$joined,$bom.Length,$newBytes.Length)
  $newBytes=$joined
 }
 return (GitBlob $newBytes)
}
function ParsePs([string]$p){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 $a=[Text.Encoding]::UTF8.GetBytes(('hello'+[char]13+[char]10))
 $b=[Text.Encoding]::UTF8.GetBytes(('hello'+[char]10))
 Need ((CanonicalBlob $a) -ceq (CanonicalBlob $b)) 'CANONICALIZATION'
 Write-Host 'NO11_PID_DIAG_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'WHITE_ONECLICK_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need (Test-Path -LiteralPath $bindingFile -PathType Leaf) 'AUTOMATIC_BINDING_MISSING'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.engine) -and
      [IO.Path]::IsPathRooted([string]$binding.python)) 'BOUND_SOURCE_UNSAFE'
$reference=Join-Path ([string]$binding.engine) 'windows\Capture-No11SessionReferenceReadOnly.ps1'
$clean=Join-Path ([string]$binding.engine) 'windows\No11CleanCompatibility.ps1'
$white=Join-Path $store 'oneclick\Start-No11OneClick.ps1'
foreach($p in @($reference,$clean,$white,[string]$binding.python)){
 Need (Test-Path -LiteralPath $p -PathType Leaf) 'REQUIRED_LOCAL_SOURCE_MISSING'
}
$old=[IO.File]::ReadAllBytes($reference)
$oldSha=CanonicalBlob $old
Write-Host ('NO11_PID_DIAG_OLD_SOURCE='+$oldSha)
Need ($oldSha -ceq 'd52794cc647c8552a9953dc0c3352e08076cf716') 'UNKNOWN_INSTALLED_REFERENCE_DO_NOT_TOUCH'
$whiteSha=(Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash
$cleanSha=(Get-FileHash -LiteralPath $clean -Algorithm SHA256).Hash
$busy=@(Get-CimInstance Win32_Process|Where-Object{
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Retry-No11OneClickPreorder'
})
Need ($busy.Count -eq 0) 'NATIVE_LIVE_OR_RETRY_IN_PROGRESS'
$temp=Join-Path $env:TEMP ('no11-pid-diagnostic-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $commit='5233c70cf2269c48483c351dfd21bc93cae6e20d'
 $uri='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$commit+'/research/no11-morning-master-20261103/patch_local_rot_pid_probe.py'
 $patcher=Join-Path $temp 'patch.py'
 Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $patcher -ErrorAction Stop
 Need ((GitBlob ([IO.File]::ReadAllBytes($patcher))) -ceq 'da97aee2bc29c8bedcc40b2b61c185544ccaba3e') 'DOWNLOADED_PATCH_HASH_CHANGED'
 $candidate=Join-Path $temp 'candidate.ps1'
 & ([string]$binding.python) -B $patcher --original $reference --candidate $candidate
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $candidate -PathType Leaf)) 'CANDIDATE_NOT_VERIFIED'
 ParsePs $candidate
 $new=[IO.File]::ReadAllBytes($candidate)
 Need ((CanonicalBlob $new) -cne $oldSha -and
       [Math]::Abs($old.Length-$new.Length) -lt 5000) 'PATCH_SCOPE_UNEXPECTED'
 $referenceText=([Text.UTF8Encoding]::new($false,$true)).GetString($new)
 foreach($needle in @(
  'No11CleanCompatibility.ps1','CONFIGURED_BROKER_BOOK_IDENTITY',
  'Read-No11CleanReferenceRows','ConvertTo-No11CleanJson',
  'EXCEL_ROT_PID_MISMATCH','NO11_REFERENCE_ROT_PID_PROBE=')){
  Need ($referenceText.Contains($needle)) 'EXISTING_CLEAN_OR_BROKER_GUARD_MISSING'
 }
 Need ((CanonicalBlob ([IO.File]::ReadAllBytes($reference))) -ceq $oldSha -and
       (Get-FileHash -LiteralPath $clean -Algorithm SHA256).Hash -ceq $cleanSha -and
       (Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $whiteSha) 'FILES_CHANGED_DURING_INSTALL'
 $backup=Join-Path $store ('rot-pid-diagnostic-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Capture-No11SessionReferenceReadOnly.before.ps1'),$old)
 $replacement=Join-Path (Split-Path -Parent $reference) ('.no11-pid-new-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $winBackup=Join-Path (Split-Path -Parent $reference) ('.no11-pid-old-'+[guid]::NewGuid().ToString('N')+'.bak')
 try{
  [IO.File]::WriteAllBytes($replacement,$new)
  [IO.File]::Replace($replacement,$reference,$winBackup)
  Need ((CanonicalBlob ([IO.File]::ReadAllBytes($reference))) -ceq (CanonicalBlob $new) -and
        (Get-FileHash -LiteralPath $clean -Algorithm SHA256).Hash -ceq $cleanSha -and
        (Get-FileHash -LiteralPath $white -Algorithm SHA256).Hash -ceq $whiteSha) 'POSTINSTALL_SOURCE_CHANGED'
 }catch{
  [IO.File]::WriteAllBytes($reference,$old)
  throw
 }
 Write-Host 'NO11_ROT_PID_DIAGNOSTIC_INSTALL=PASS'
 Write-Host 'PID_MISMATCH_CHECK_STILL_MANDATORY=True'
 Write-Host 'PID_STABILITY_DOUBLE_SAMPLE=True'
 Write-Host 'MAX_PROBES=3'
 Write-Host 'CLEAN_AND_BROKER_GATES_CHANGED=False'
 Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
