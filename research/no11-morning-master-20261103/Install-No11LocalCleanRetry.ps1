# Nov 5: pinned reversible installer for the ACTUAL local
# No11CleanCompatibility-modified reference collector, plus WHITE OneClick.
# Code installation only: no broker approval/order/Excel mutation.
param([switch]$Apply,[switch]$OpenOneClick,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_CLEAN_RETRY_INSTALL_'+$code)}
}
function Blob([byte[]]$bytes){
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$bytes.Length)+[char]0)
 $data=New-Object byte[] ($head.Length+$bytes.Length)
 [array]::Copy($head,0,$data,0,$head.Length)
 [array]::Copy($bytes,0,$data,$head.Length,$bytes.Length)
 $hash=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($hash.ComputeHash($data))).Replace('-','').ToLowerInvariant()}
 finally{$hash.Dispose()}
}
function BlobFile([string]$name){return Blob ([IO.File]::ReadAllBytes($name))}
function CanonicalBlob([byte[]]$bytes){
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($bytes)
 $s=$s.Replace(([string][char]13+[char]10),[string][char]10)
 Need (-not $s.Contains([char]13)) 'UNKNOWN_LINE_ENDINGS'
 return Blob ([Text.Encoding]::UTF8.GetBytes($s))
}
function ParsePs([string]$name){
 $tok=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($name,[ref]$tok,[ref]$errors)
 Need ($errors.Count -eq 0) 'POWERSHELL_PARSING_ERROR'
}
function AssertStopped {
 $busy=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Recover-No11FilteredMorning[.]ps1|Start-No11AfternoonFilteredRecovery[.]ps1'
 })
 Need ($busy.Count -eq 0) 'CLOSE_RUNNING_ONECLICK_OR_LIVE_PROCESS'
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $OpenOneClick) 'SELFTEST_FLAGS'
 $a=[Text.Encoding]::UTF8.GetBytes(('abc'+[char]13+[char]10))
 $b=[Text.Encoding]::UTF8.GetBytes(('abc'+[char]10))
 Need ((CanonicalBlob $a) -ceq (CanonicalBlob $b)) 'CANONICAL_LF'
 Write-Host 'NO11_LOCAL_CLEAN_RETRY_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_UI_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_INSTALL_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$one=Join-Path $store 'oneclick'
$white=Join-Path $one 'Start-No11OneClick.ps1'
$retry=Join-Path $one 'Retry-No11OneClickPreorder.ps1'
$bindingFile=Join-Path $store 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $white -PathType Leaf) -and
      (Test-Path -LiteralPath $bindingFile -PathType Leaf) -and
      -not (Test-Path -LiteralPath $retry)) 'PREVIOUS_WHITE_ONECLICK_OR_RETRY_CONFLICT'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.engine) -and
      [IO.Path]::IsPathRooted([string]$binding.python)) 'PINNED_BINDING_UNSAFE'
$reference=Join-Path ([string]$binding.engine) 'windows\Capture-No11SessionReferenceReadOnly.ps1'
$clean=Join-Path ([string]$binding.engine) 'windows\No11CleanCompatibility.ps1'
Need ((Test-Path -LiteralPath $reference -PathType Leaf) -and
      (Test-Path -LiteralPath $clean -PathType Leaf)) 'LOCAL_CLEAN_COMPATIBILITY_NOT_FOUND'
$python=[string]$binding.python
Need (Test-Path -LiteralPath $python -PathType Leaf) 'PINNED_PYTHON_MISSING'
$oldReference=[IO.File]::ReadAllBytes($reference)
$oldUi=[IO.File]::ReadAllBytes($white)
$sourceIdentity=CanonicalBlob $oldReference
Write-Host ('LOCAL_REFERENCE_NORMALIZED_BLOB='+$sourceIdentity)
Need ($sourceIdentity -ceq 'b06fbb4194d468313ad450033cb6a7717ea1f5fd') 'UNKNOWN_LOCAL_REFERENCE_DO_NOT_REPLACE'
AssertStopped
$work=Join-Path $env:TEMP ('no11-clean-retry-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($work)
$manifest=[ordered]@{
 'patch_clean.py'=@('research/no11-morning-master-20261103/patch_local_clean_reference_20261105.py','cacdb6e5397e8a91aaf6b11300e822675448390b')
 'patch_white.py'=@('research/no11-morning-master-20261103/patch_oneclick_preorder_retry.py','05f574fb8794ad19bc64c9953f042bab5cda439c')
 'retry_template.ps1'=@('research/no11-morning-master-20261103/Retry-No11OneClickPreorder.ps1','732d17a8b57b2f597b248f02a43839ff4b839a09')
}
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $pinned='8d764a373a0922e71464b7cf7187f0521d11dc11'
 $base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$pinned+'/'
 foreach($name in $manifest.Keys){
  $candidate=Join-Path $work $name
  Invoke-WebRequest -UseBasicParsing -Uri ($base+$manifest[$name][0]) -OutFile $candidate -ErrorAction Stop
  Need ((BlobFile $candidate) -ceq [string]$manifest[$name][1]) ('DOWNLOAD_PIN_'+$name.ToUpperInvariant())
 }
 $refCandidate=Join-Path $work 'candidate-reference.ps1'
 & $python -B (Join-Path $work 'patch_clean.py') --original $reference --candidate $refCandidate
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $refCandidate -PathType Leaf)) 'LOCAL_CLEAN_PATCH_FAIL'
 $refNew=[IO.File]::ReadAllBytes($refCandidate)
 ParsePs $refCandidate
 Need ($refNew.Length -gt $oldReference.Length -and
       $refNew.Length -lt ($oldReference.Length+8000)) 'LOCAL_CLEAN_CHANGE_OUTSIDE_EXPECTED'
 $candidateWhite=Join-Path $work 'candidate-white.ps1'
 & $python -B (Join-Path $work 'patch_white.py') --original $white --candidate $candidateWhite
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $candidateWhite -PathType Leaf)) 'WHITE_ONECLICK_PATCH_REJECTED'
 ParsePs $candidateWhite
 $uiNew=[IO.File]::ReadAllBytes($candidateWhite)
 $refHash=Blob $refNew
 # Embed exact patched byte-verified reference hash into the fail-closed
 # one-shot retry helper. Do not disable this original source-pin check.
 $helperOriginal=Get-Content -LiteralPath (Join-Path $work 'retry_template.ps1') -Raw -Encoding UTF8
 $knownTemplate='f1e9739ccfb8ac520a4484d00ffccc5471264763'
 Need ($helperOriginal.IndexOf($knownTemplate) -ge 0 -and
       $helperOriginal.IndexOf($knownTemplate,$helperOriginal.IndexOf($knownTemplate)+1) -lt 0) 'RETRY_SOURCE_PIN_ANCHOR'
 $helperNew=$helperOriginal.Replace($knownTemplate,$refHash)
 Need ($helperNew -cne $helperOriginal) 'RETRY_SOURCE_PIN_NOT_UPDATED'
 $helperCandidate=Join-Path $work 'candidate-helper.ps1'
 [IO.File]::WriteAllText($helperCandidate,$helperNew,[Text.UTF8Encoding]::new($false))
 ParsePs $helperCandidate
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helperCandidate -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'RETRY_HELPER_SELFTEST'
 # The local collector dot-sources CleanCompatibility by PSScriptRoot.
 # Offline-test an ephemeral copy beside it (no Excel/orders).
 $tempReference=Join-Path (Split-Path -Parent $reference) ('.no11-clean-test-'+[guid]::NewGuid().ToString('N')+'.ps1')
 try{
  [IO.File]::WriteAllBytes($tempReference,$refNew)
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tempReference -OfflineSelfTest | Out-Null
  Need ($LASTEXITCODE -eq 0) 'LOCAL_CLEAN_COLLECTOR_SELFTEST'
 }finally{
  Remove-Item -LiteralPath $tempReference -Force -ErrorAction SilentlyContinue
 }
 AssertStopped
 Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($reference))) -ceq
       ([Convert]::ToBase64String($oldReference)) -and
       ([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
       ([Convert]::ToBase64String($oldUi))) 'CONCURRENT_LOCAL_CHANGE'
 $backup=Join-Path $store ('local-clean-retry-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Capture-No11SessionReferenceReadOnly.before.ps1'),$oldReference)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Start-No11OneClick.WHITE.before.ps1'),$oldUi)
 $newRef=Join-Path (Split-Path -Parent $reference) ('.no11-patched-ref-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $newUi=Join-Path $one ('.no11-patched-ui-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $refBak=Join-Path (Split-Path -Parent $reference) ('.no11-prior-ref-'+[guid]::NewGuid().ToString('N')+'.bak')
 $uiBak=Join-Path $one ('.no11-prior-ui-'+[guid]::NewGuid().ToString('N')+'.bak')
 try{
  [IO.File]::WriteAllBytes($newRef,$refNew)
  [IO.File]::Replace($newRef,$reference,$refBak)
  [IO.File]::WriteAllBytes($newUi,$uiNew)
  [IO.File]::Replace($newUi,$white,$uiBak)
  $helperBytes=[IO.File]::ReadAllBytes($helperCandidate)
  $f=[IO.File]::Open($retry,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($helperBytes,0,$helperBytes.Length);$f.Flush($true)}
  finally{$f.Dispose()}
  Need ((BlobFile $reference) -ceq $refHash -and
        (BlobFile $retry) -ceq (Blob $helperBytes) -and
        ([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
        ([Convert]::ToBase64String($uiNew))) 'POST_INSTALL_VERIFICATION_FAILED'
  ParsePs $white
 }catch{
  [IO.File]::WriteAllBytes($reference,$oldReference)
  [IO.File]::WriteAllBytes($white,$oldUi)
  if(Test-Path -LiteralPath $retry -PathType Leaf){
   Remove-Item -LiteralPath $retry -Force -ErrorAction SilentlyContinue
  }
  throw
 }
 Write-Host 'NO11_LOCAL_CLEAN_ONECLICK_RETRY_INSTALL=PASS'
 Write-Host ('PINNED_LOCAL_REFERENCE_BLOB='+$refHash)
 Write-Host 'CLEAN_REFERENCE_READ_AND_JSON=UNCHANGED'
 Write-Host 'CONFIGURED_THIRD_BROKER_BOOK=UNCHANGED'
 Write-Host 'EXCEL_ROT_PID_VERIFICATION=ADDED'
 Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
 Write-Host 'WHITE_ONECLICK_LAYOUT_CHANGED=False'
 Write-Host 'BROKER_ORDER_OR_STATE_FILES_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
 if($OpenOneClick){
  $proc=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$white+'"')) -WorkingDirectory $one -PassThru
  Write-Host ('WHITE_ONECLICK_OPEN_REQUESTED_PID='+$proc.Id)
  Write-Host 'ORDER_APPROVAL_AUTOMATIC=False'
 }
}finally{
 if(Test-Path -LiteralPath $work -PathType Container){
  Remove-Item -LiteralPath $work -Force -Recurse -ErrorAction SilentlyContinue
 }
}
