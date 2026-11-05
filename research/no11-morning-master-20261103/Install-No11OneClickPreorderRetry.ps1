# Surgical source + existing WHITE OneClick START repair.
# Actual -Apply INSTALLS CODE ONLY; it never runs Trade or sends orders.
# -OpenOneClick optionally opens the existing approved white launcher window.
param([switch]$Apply,[switch]$OpenOneClick,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$why){if(-not $ok){throw ('NO11_RETRY_INSTALL_'+$why)}}
function GitBlob([string]$path){
 $hash=@(& git hash-object --no-filters -- $path)
 Need ($LASTEXITCODE -eq 0 -and $hash.Count -eq 1 -and
       [string]$hash[0] -cmatch '^[a-f0-9]{40}$') 'GIT_HASH_UNAVAILABLE'
 return [string]$hash[0]
}
function ParsePs([string]$p){
 $t=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$errors)
 Need ($errors.Count -eq 0) 'PATCHED_POWERSHELL_PARSE_FAILED'
}
function NoLiveOrUiProcesses{
 $busy=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Recover-No11FilteredMorning[.]ps1|Start-No11AfternoonFilteredRecovery[.]ps1'
 })
 Need ($busy.Count -eq 0) 'EXISTING_UI_OR_NATIVE_LIVE_PROCESS'
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $OpenOneClick) 'SELFTEST_FLAGS'
 Write-Host 'NO11_RETRY_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_THEME_REPLACED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_INSTALL_REQUIRED'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$one=Join-Path $root 'oneclick'
$white=Join-Path $one 'Start-No11OneClick.ps1'
$helper=Join-Path $one 'Retry-No11OneClickPreorder.ps1'
$bindingFile=Join-Path $root 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $white -PathType Leaf) -and
      (Test-Path -LiteralPath $bindingFile -PathType Leaf) -and
      -not (Test-Path -LiteralPath $helper)) 'LOCAL_WHITE_INSTALL_OR_RETRY_HELPER_CONFLICT'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.engine)) 'CURRENT_BINDING_INVALID'
$reference=Join-Path ([string]$binding.engine) 'windows\Capture-No11SessionReferenceReadOnly.ps1'
Need (Test-Path -LiteralPath $reference -PathType Leaf) 'REFERENCE_COLLECTOR_MISSING'
Need ((GitBlob $reference) -ceq '26d2a79c912d4bfd2422bcb82562004794b50487') 'REFERENCE_ORIGINAL_CHANGED'
NoLiveOrUiProcesses
$python=[string]$binding.python
Need ([IO.Path]::IsPathRooted($python) -and
      (Test-Path -LiteralPath $python -PathType Leaf)) 'EXISTING_PINNED_PYTHON_MISSING'
$beforeUi=[IO.File]::ReadAllBytes($white)
$beforeCapture=[IO.File]::ReadAllBytes($reference)
$work=Join-Path $env:TEMP ('ark-oneclick-retry-install-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($work)
$patches=[ordered]@{
 'capture.ps1'=@('research/no12-prebuy-causal-runtime-20261011/windows/Capture-No11SessionReferenceReadOnly.ps1','f6b56c10dfbd25b57ee6e8ca9783204cff3a83d3')
 'helper.ps1'=@('research/no11-morning-master-20261103/Retry-No11OneClickPreorder.ps1','82cdac68d7725ae97954e0479f2542e9d3ce03c1')
 'patch.py'=@('research/no11-morning-master-20261103/patch_oneclick_preorder_retry.py','05f574fb8794ad19bc64c9953f042bab5cda439c')
}
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/eb41e193cf7c0bca8f3829bd2597c7ebe9b6b0ae/'
 foreach($name in $patches.Keys){
  $url=$base+[string]$patches[$name][0]
  $local=Join-Path $work $name
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $local -ErrorAction Stop
  Need ((GitBlob $local) -ceq [string]$patches[$name][1]) ('PIN_MISMATCH_'+$name)
 }
 ParsePs (Join-Path $work 'capture.ps1')
 ParsePs (Join-Path $work 'helper.ps1')
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $work 'capture.ps1') -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'CAPTURE_OFFLINE_SELFTEST'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $work 'helper.ps1') -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'ONECLICK_RETRY_OFFLINE_SELFTEST'
 & $python -B -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" (Join-Path $work 'patch.py')
 Need ($LASTEXITCODE -eq 0) 'PATCHER_PYTHON_PARSE'
 $patchedUi=Join-Path $work 'candidate-oneclick.ps1'
 & $python -B (Join-Path $work 'patch.py') --original $white --candidate $patchedUi
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $patchedUi -PathType Leaf)) 'LOCAL_WHITE_UI_PATCH_NOT_SAFE'
 ParsePs $patchedUi
 $bytesNewUi=[IO.File]::ReadAllBytes($patchedUi)
 $bytesNewCapture=[IO.File]::ReadAllBytes((Join-Path $work 'capture.ps1'))
 Need ((GitBlob $white) -cne (GitBlob $patchedUi) -and
       (GitBlob (Join-Path $work 'capture.ps1')) -ceq 'f6b56c10dfbd25b57ee6e8ca9783204cff3a83d3') 'PATCH_OUTPUT_IDENTITY'
 NoLiveOrUiProcesses
 Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
       ([Convert]::ToBase64String($beforeUi)) -and
       ([Convert]::ToBase64String([IO.File]::ReadAllBytes($reference))) -ceq
       ([Convert]::ToBase64String($beforeCapture))) 'SOURCES_CHANGED_DURING_INSTALL'
 $backup=Join-Path $root ('oneclick-preorder-retry-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Start-No11OneClick.WHITE.before.ps1'),$beforeUi)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Capture-No11SessionReferenceReadOnly.before.ps1'),$beforeCapture)
 $installedHelper=$false
 try{
  $newReference=Join-Path (Split-Path -Parent $reference) ('.no11-retry-reference-'+[guid]::NewGuid().ToString('N')+'.tmp')
  $referenceBak=Join-Path (Split-Path -Parent $reference) ('.no11-retry-reference-backup-'+[guid]::NewGuid().ToString('N')+'.bak')
  [IO.File]::WriteAllBytes($newReference,$bytesNewCapture)
  [IO.File]::Replace($newReference,$reference,$referenceBak)
  $newUi=Join-Path (Split-Path -Parent $white) ('.no11-retry-oneclick-'+[guid]::NewGuid().ToString('N')+'.tmp')
  $uiBak=Join-Path (Split-Path -Parent $white) ('.no11-retry-oneclick-backup-'+[guid]::NewGuid().ToString('N')+'.bak')
  [IO.File]::WriteAllBytes($newUi,$bytesNewUi)
  [IO.File]::Replace($newUi,$white,$uiBak)
  $h=[IO.File]::Open($helper,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{
   $helperBytes=[IO.File]::ReadAllBytes((Join-Path $work 'helper.ps1'))
   $h.Write($helperBytes,0,$helperBytes.Length)
   $h.Flush($true)
  }finally{$h.Dispose()}
  $installedHelper=$true
  Need ((GitBlob $reference) -ceq [string]$patches['capture.ps1'][1] -and
        (GitBlob $helper) -ceq [string]$patches['helper.ps1'][1] -and
        [IO.File]::ReadAllBytes($white).Length -eq $bytesNewUi.Length) 'POST_INSTALL_VERIFICATION_FAILED'
  ParsePs $white
 }catch{
  [IO.File]::WriteAllBytes($reference,$beforeCapture)
  [IO.File]::WriteAllBytes($white,$beforeUi)
  if(Test-Path -LiteralPath $helper -PathType Leaf){
   Remove-Item -LiteralPath $helper -Force -ErrorAction SilentlyContinue
  }
  throw
 }
 Write-Host 'NO11_ONECLICK_VERIFIED_RETRY_INSTALL=PASS'
 Write-Host 'SOURCE_REFERENCE_BOOKS=2_OR_EXACT_KNOWN_3'
 Write-Host 'SINGLE_EXCEL_COM_PROCESS_CHECK=ENABLED'
 Write-Host 'WHITE_ONECLICK_THEME_REPLACED=False'
 Write-Host 'WHITE_ONECLICK_LAYOUT_CHANGED=False'
 Write-Host 'OLD_TRADE_AND_PREOPEN_MARKERS_UNCHANGED=True'
 Write-Host 'LIVE_TRADE_STARTED_BY_INSTALL=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
 # The UI itself is safe to launch. A broker order STILL requires an
 # additional explicit YES click in the original START button.
 if($OpenOneClick){
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$white+'"'))
  $process=Start-Process -FilePath 'powershell.exe' -ArgumentList ($args -join ' ') -WorkingDirectory $one -WindowStyle Normal -PassThru
  Write-Host ('NO11_WHITE_ONECLICK_OPEN_REQUESTED_PID='+$process.Id)
  Write-Host 'AUTO_ORDER_APPROVAL=False'
 }
}finally{
 if(Test-Path -LiteralPath $work -PathType Container){
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
 }
}
