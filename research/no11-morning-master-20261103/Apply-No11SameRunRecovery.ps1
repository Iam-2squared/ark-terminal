# ARK No.1.1: surgical SAME-RUN recovery install for the locally approved
# WHITE OneClick. Never replaces theme/layout or Frozen strategy files.
# Downloads pinned code internally; no manual file downloads.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_SAME_RUN_INSTALL_'+$reason)}
}
function BlobHash([byte[]]$raw){
 $s=([Text.UTF8Encoding]::new($false,$true)).GetString($raw)
 $crlf=([string][char]13)+([string][char]10)
 $normalized=[Text.Encoding]::UTF8.GetBytes($s.Replace($crlf,[string][char]10))
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$normalized.Length)+[char]0)
 $all=New-Object byte[] ($header.Length+$normalized.Length)
 [array]::Copy($header,0,$all,0,$header.Length)
 [array]::Copy($normalized,0,$all,$header.Length,$normalized.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($all))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function ParsePS([string]$file){
 $tok=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($file,[ref]$tok,[ref]$errors)
 Need ($errors.Count -eq 0) 'POWERSHELL_PARSE'
}
function Sha256([byte[]]$raw){
 $sha=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($raw))).Replace('-','')}
 finally{$sha.Dispose()}
}
function TextOf([byte[]]$raw){
 $bom=($raw.Length -ge 3 -and $raw[0] -eq 239 -and $raw[1] -eq 187 -and $raw[2] -eq 191)
 $offset=if($bom){3}else{0}
 return ([Text.UTF8Encoding]::new($false,$true)).GetString($raw,$offset,$raw.Length-$offset)
}
function BytesLike([byte[]]$original,[string]$lfText){
 $bom=($original.Length -ge 3 -and $original[0] -eq 239 -and $original[1] -eq 187 -and $original[2] -eq 191)
 $crlf=([string][char]13)+([string][char]10)
 $nl=if((TextOf $original).Contains($crlf)){$crlf}else{[string][char]10}
 $bytes=([Text.UTF8Encoding]::new($false)).GetBytes($lfText.Replace([string][char]10,$nl))
 if(-not $bom){return ,$bytes}
 $merged=New-Object byte[] ($bytes.Length+3)
 [array]::Copy($original,0,$merged,0,3)
 [array]::Copy($bytes,0,$merged,3,$bytes.Length)
 return ,$merged
}
function OnlySlice([string]$body,[string]$first,[string]$next){
 $start=$body.IndexOf($first,[StringComparison]::Ordinal)
 Need ($start -ge 0 -and $body.IndexOf($first,$start+$first.Length,[StringComparison]::Ordinal) -lt 0) 'SLICE_START_AMBIGUOUS'
 $end=$body.IndexOf($next,$start+$first.Length,[StringComparison]::Ordinal)
 Need ($end -gt $start) 'SLICE_END_MISSING'
 return $body.Substring($start,$end-$start)
}
function AssertStopped {
 $active=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Resume-No11SameSession|Close-No11OwnedC50Temporary|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($active.Count -eq 0) 'CLOSE_ONECLICK_AND_LIVE_PROCESSES'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 # Verify on actual Windows PowerShell 5.1 that File.Replace uses a real
 # same-volume backup destination (a prior installer used $null and failed).
 $sandbox=Join-Path $env:TEMP ('no11-atomic-probe-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($sandbox)
 try{
  $original=Join-Path $sandbox 'original.txt'
  $candidate=Join-Path $sandbox 'candidate.txt'
  $backup=Join-Path $sandbox 'original.before.txt'
  [IO.File]::WriteAllText($original,'WHITE_UI_BEFORE')
  [IO.File]::WriteAllText($candidate,'PATCHED_CANDIDATE')
  [IO.File]::Replace($candidate,$original,$backup)
  Need ([IO.File]::ReadAllText($original) -ceq 'PATCHED_CANDIDATE' -and
        [IO.File]::ReadAllText($backup) -ceq 'WHITE_UI_BEFORE') 'ATOMIC_REPLACE_SELFTEST'
 }finally{
  if(Test-Path -LiteralPath $sandbox -PathType Container){
   Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
  }
 }
 Write-Host 'NO11_SAME_RUN_ATOMIC_REPLACE_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_SAME_RUN_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_THEME_MODIFIED=False'
 Write-Host 'ORIGINAL_TRADING_STRATEGY_MODIFIED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$ui=Join-Path $store 'oneclick\Start-No11OneClick.ps1'
$helperFolder=Join-Path $store 'oneclick'
$bindingPath=Join-Path $store 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $ui -PathType Leaf) -and
      (Test-Path -LiteralPath $bindingPath -PathType Leaf)) 'ONECLICK_NOT_INSTALLED'
$binding=Get-Content -LiteralPath $bindingPath -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false) 'BINDING_UNSAFE'
$engine=[string]$binding.engine
$python=[string]$binding.python
Need ([IO.Path]::IsPathRooted($engine) -and
      (Test-Path -LiteralPath $engine -PathType Container) -and
      [IO.Path]::IsPathRooted($python) -and
      (Test-Path -LiteralPath $python -PathType Leaf)) 'INSTALLED_RUNTIME_MISSING'
$runtime=Join-Path $engine 'tools\no11_received_run_recovery.py'
$controller=Join-Path $engine 'tools\no11_received_session_controller.py'
Need ((Test-Path -LiteralPath $runtime -PathType Leaf) -and
      (Test-Path -LiteralPath $controller -PathType Leaf)) 'RECOVERY_ENGINE_MISSING'
AssertStopped
$headRef='f5562e3fd58f9ebf6487ab11a4a31ab36a09d5ad'
$baseRef='fb41945877229393b944ac3ce171c9571eaf4134'
$repo='Iam-2squared/ark-terminal'
$prefix='research/no11-morning-master-20261103/'
$enginePath='research/no12-prebuy-causal-runtime-20261011/tools/no11_received_run_recovery.py'
$controllerPath='research/no12-prebuy-causal-runtime-20261011/tools/no11_received_session_controller.py'
$pins=[ordered]@{
 'Start-No11OneClick.ps1'='bbb898627f77a62c1d4d0541f5675f067191ab31'
 'Resume-No11SameSession.ps1'='1bb926c746bddcfb5f3d74018c06ee330d9fea28'
 'Close-No11OwnedC50Temporary.ps1'='6cd43faeb745c7a976d763423f30b0e4f2ac0f18'
 'no11_finalize_owned_collector_cleanup.py'='4bad609d0f499cb29f4a8d194fe242550bf36634'
 'no11_same_session_rearm.py'='29d057c63c425015de00fbf972ba010297bb5e7b'
 'no11_manual_reconnect_review.py'='2afc1d60d24c937e1a6dc67d8436c34f40fb509c'
 'new-no11_received_run_recovery.py'='47f87ae69faa9c9168c991b2b583828c38533e91'
 'old-no11_received_run_recovery.py'='8195a1f6970ccca71f1f382403d884447a113003'
 'new-no11_received_session_controller.py'='329dbb216025b31c629f6e5fcc64d628edf29e05'
 'old-no11_received_session_controller.py'='5a2fe9f6eb785f66412cc4cd09015eb37966c58c'
 'old-Start-No11OneClick.ps1'='e4cb96d6b7192b25ce0298cb91632e3f8db611a7'
}
$temp=Join-Path $env:TEMP ('ark-same-run-installer-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 foreach($name in $pins.Keys){
  $useBase=$name.StartsWith('old-')
  $sourceName=$name
  if($useBase){$sourceName=$sourceName.Substring(4)}
  if($name -in @('new-no11_received_run_recovery.py','old-no11_received_run_recovery.py')){
   $path=$enginePath
  }elseif($name -in @('new-no11_received_session_controller.py','old-no11_received_session_controller.py')){
   $path=$controllerPath
  }else{$path=$prefix+$sourceName}
  $ref=if($useBase){$baseRef}else{$headRef}
  $url='https://raw.githubusercontent.com/'+$repo+'/'+$ref+'/'+$path
  $dest=Join-Path $temp $name
  Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop
  $raw=[IO.File]::ReadAllBytes($dest)
  Need ((BlobHash $raw) -ceq $pins[$name]) 'GITHUB_BLOB_CHANGED'
 }
 foreach($name in @('Start-No11OneClick.ps1','Resume-No11SameSession.ps1','Close-No11OwnedC50Temporary.ps1')){
  ParsePS (Join-Path $temp $name)
 }
 foreach($name in @('Resume-No11SameSession.ps1','Close-No11OwnedC50Temporary.ps1')){
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $temp $name) -OfflineSelfTest | Out-Null
  Need ($LASTEXITCODE -eq 0) 'HELPER_SELFTEST'
 }
 foreach($name in @('no11_same_session_rearm.py','no11_finalize_owned_collector_cleanup.py','no11_manual_reconnect_review.py')){
  & $python -B -m py_compile (Join-Path $temp $name)
  Need ($LASTEXITCODE -eq 0) 'PYTHON_COMPILE'
 }
 $crlf=([string][char]13)+([string][char]10)
 $LF=[string][char]10
 $oldUiOriginal=[IO.File]::ReadAllBytes($ui)
 $oldEngineOriginal=[IO.File]::ReadAllBytes($runtime)
 $oldControllerOriginal=[IO.File]::ReadAllBytes($controller)
 $uiPin=Sha256 $oldUiOriginal
 $enginePin=Sha256 $oldEngineOriginal
 $controllerPin=Sha256 $oldControllerOriginal
 $localUi=(TextOf $oldUiOriginal).Replace($crlf,$LF)
 $baseUi=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'old-Start-No11OneClick.ps1')))).Replace($crlf,$LF)
 $newUi=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'Start-No11OneClick.ps1')))).Replace($crlf,$LF)
 $oldBlock=OnlySlice $baseUi '$review.Add_Click({' '$logsButton.Add_Click({'
 $newBlock=OnlySlice $newUi '$review.Add_Click({' '$logsButton.Add_Click({'
 Need ($newBlock.Contains('ARK_NO11_ONECLICK_SAME_RUN_RESUME_BUTTON_V1') -and
       $newBlock.Contains('IConfirmSameDayBrokerOrdersAndPositions') -and
       $oldBlock.Contains('Review-No11RecoveryReadOnly.ps1')) 'PINNED_UI_PATCH_CONTRACT'
 Need (-not $localUi.Contains('ARK_NO11_ONECLICK_SAME_RUN_RESUME_BUTTON_V1')) 'ALREADY_INSTALLED_REVIEW'
 Need ($localUi.Contains($oldBlock) -and
       ([regex]::Matches($localUi,[regex]::Escape($oldBlock))).Count -eq 1) 'LOCAL_WHITE_UI_REVIEW_CHANGED'
 $newLocalUi=$localUi.Replace($oldBlock,$newBlock)
 Need ($newLocalUi.Replace($newBlock,'') -ceq $localUi.Replace($oldBlock,'')) 'WHITE_UI_OUTSIDE_REVIEW_CHANGED'
 $uiBytes=BytesLike $oldUiOriginal $newLocalUi
 $oldEngine=(TextOf $oldEngineOriginal).Replace($crlf,$LF)
 $baseEngine=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'old-no11_received_run_recovery.py')))).Replace($crlf,$LF)
 $newEngine=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'new-no11_received_run_recovery.py')))).Replace($crlf,$LF)
 $a="ATTEMPT = 'ARK_NO11_RECEIVED_ATTEMPT_V1'"
 $newConstant=$a+$LF+"POSTMORTEM = 'ARK_NO11_C50_POSTMORTEM_CLEANUP_V1'"
 Need ($baseEngine.Contains($a) -and $newEngine.Contains($newConstant) -and
       $oldEngine.Contains($a) -and
       -not $oldEngine.Contains("POSTMORTEM = 'ARK_NO11_C50_POSTMORTEM_CLEANUP_V1'")) 'RECOVERY_RUNTIME_ANCHOR_CHANGED'
 $oldAck=OnlySlice $baseEngine "            need(checksum == a['closedSha256']" "            if a.get('captureFolder')"
 $newAck=OnlySlice $newEngine "            need(checksum == a['closedSha256']" "            if a.get('captureFolder')"
 Need ($newAck.Contains('ARK_NO11_POSTMORTEM_CLEANUP_RECEIPT_V1') -and
       $oldEngine.Contains($oldAck) -and
       ([regex]::Matches($oldEngine,[regex]::Escape($oldAck))).Count -eq 1) 'RECOVERY_RUNTIME_LOCAL_DIFFERENT'
 $patchedEngine=$oldEngine.Replace($a,$newConstant).Replace($oldAck,$newAck)
 Need ($patchedEngine.Contains('POSTMORTEM_CLEANUP_NOT_VERIFIED') -and
       $patchedEngine.Contains('COLLECTOR_CLEANUP_UNCONFIRMED')) 'RECOVERY_RUNTIME_UNSAFE'
 $engineBytes=BytesLike $oldEngineOriginal $patchedEngine
 # Patch operational collector-marker resolution only; never replace the
 # locally customized or frozen order/strategy controller as a whole.
 $localController=(TextOf $oldControllerOriginal).Replace($crlf,$LF)
 $baseController=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'old-no11_received_session_controller.py')))).Replace($crlf,$LF)
 $newController=(TextOf ([IO.File]::ReadAllBytes((Join-Path $temp 'new-no11_received_session_controller.py')))).Replace($crlf,$LF)
 $oldImport='from no11_received_run_recovery import RunRecovery, CaptureRelay, read, need, atomic'
 $newImport='from no11_received_run_recovery import RunRecovery, CaptureRelay, read, need, atomic, unseal, ATTEMPT, POSTMORTEM'
 Need ($baseController.Contains($oldImport) -and $newController.Contains($newImport) -and
       $localController.Contains($oldImport) -and -not $localController.Contains('def marked_cleanup_proven(')) 'CONTROLLER_IMPORT_CHANGED'
 $markerFunction=OnlySlice $newController 'def marked_cleanup_proven(' 'def execute('
 Need ($markerFunction.Contains('recovery.history(run)') -and
       $markerFunction.Contains("COLLECTOR_CLEANUP_NOT_CONFIRMED") -and
       $markerFunction.Contains('return len(claims) == 1')) 'CONTROLLER_PROOF_FUNCTION_INVALID'
 $oldGate="    bootstrap.need(not (root / 'bootstrap-recovery-required.json').exists(),"+$LF+
          "                   'PREVIOUS_CLEANUP_REQUIRES_REVIEW')"+$LF+
          "    recovery = RunRecovery(config)"
 $newGate="    recovery = RunRecovery(config)"+$LF+
          "    bootstrap.need(marked_cleanup_proven(root, resume_run, config['sessionDate'], recovery),"+$LF+
          "                   'PREVIOUS_CLEANUP_REQUIRES_REVIEW')"
 Need ($baseController.Contains($oldGate) -and $newController.Contains($newGate) -and
       $localController.Contains($oldGate)) 'CONTROLLER_MARKER_GATE_DIFFERENT'
 $patchedController=$localController.Replace($oldImport,$newImport)
 $patchedController=$patchedController.Replace('def execute(',$markerFunction+'def execute(')
 $patchedController=$patchedController.Replace($oldGate,$newGate)
 Need ($patchedController.Contains("marked_cleanup_proven(root, resume_run, config['sessionDate'], recovery)") -and
       $patchedController.Contains('COLLECTOR_CLEANUP_NOT_CONFIRMED')) 'CONTROLLER_PATCH_INVALID'
 $controllerBytes=BytesLike $oldControllerOriginal $patchedController
 $candidateUi=Join-Path $helperFolder ('Start-No11OneClick.recovery-candidate-'+[guid]::NewGuid().ToString('N')+'.ps1')
 $candidateEngine=Join-Path (Split-Path $runtime -Parent) ('no11_received_run_recovery.recovery-candidate-'+[guid]::NewGuid().ToString('N')+'.py')
 $candidateController=Join-Path (Split-Path $controller -Parent) ('no11_received_session_controller.recovery-candidate-'+[guid]::NewGuid().ToString('N')+'.py')
 [IO.File]::WriteAllBytes($candidateUi,$uiBytes)
 [IO.File]::WriteAllBytes($candidateEngine,$engineBytes)
 [IO.File]::WriteAllBytes($candidateController,$controllerBytes)
 ParsePS $candidateUi
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $candidateUi -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'ONECLICK_OFFLINE_SELFTEST'
 & $python -B -m py_compile $candidateEngine
 Need ($LASTEXITCODE -eq 0) 'ENGINE_PYTHON_COMPILE'
 & $python -B -m py_compile $candidateController
 Need ($LASTEXITCODE -eq 0) 'CONTROLLER_PYTHON_COMPILE'
 AssertStopped
 Need ((Sha256 ([IO.File]::ReadAllBytes($ui))) -ceq $uiPin -and
       (Sha256 ([IO.File]::ReadAllBytes($runtime))) -ceq $enginePin -and
       (Sha256 ([IO.File]::ReadAllBytes($controller))) -ceq $controllerPin) 'INSTALLED_FILE_CHANGED_DURING_REVIEW'
 $backup=Join-Path $store ('same-run-recovery-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'WhiteOneClick.before.ps1'),$oldUiOriginal)
 [IO.File]::WriteAllBytes((Join-Path $backup 'no11_received_run_recovery.before.py'),$oldEngineOriginal)
 [IO.File]::WriteAllBytes((Join-Path $backup 'no11_received_session_controller.before.py'),$oldControllerOriginal)
 $placed=@()
 $engineReplaced=$false
 $controllerReplaced=$false
 $uiReplaced=$false
 try{
  foreach($name in @('Resume-No11SameSession.ps1','Close-No11OwnedC50Temporary.ps1',
                      'no11_finalize_owned_collector_cleanup.py','no11_same_session_rearm.py',
                      'no11_manual_reconnect_review.py')){
   $dest=Join-Path $helperFolder $name
   Need (-not (Test-Path -LiteralPath $dest -PathType Leaf)) 'EXISTING_HELPER_REQUIRES_REVIEW'
   [IO.File]::WriteAllBytes($dest,[IO.File]::ReadAllBytes((Join-Path $temp $name)))
   $placed+=,$dest
  }
  $engineReplaceBackup=Join-Path (Split-Path $runtime -Parent) ('no11_received_run_recovery.before-same-run-'+[guid]::NewGuid().ToString('N')+'.py')
  [IO.File]::Replace($candidateEngine,$runtime,$engineReplaceBackup)
  $engineReplaced=$true
  $controllerReplaceBackup=Join-Path (Split-Path $controller -Parent) ('no11_received_session_controller.before-same-run-'+[guid]::NewGuid().ToString('N')+'.py')
  [IO.File]::Replace($candidateController,$controller,$controllerReplaceBackup)
  $controllerReplaced=$true
  $uiReplaceBackup=Join-Path $backup 'WhiteOneClick.atomic-before.ps1'
  [IO.File]::Replace($candidateUi,$ui,$uiReplaceBackup)
  $uiReplaced=$true
  Need ((Sha256 ([IO.File]::ReadAllBytes($ui))) -ceq (Sha256 $uiBytes) -and
        (Sha256 ([IO.File]::ReadAllBytes($runtime))) -ceq (Sha256 $engineBytes) -and
        (Sha256 ([IO.File]::ReadAllBytes($controller))) -ceq (Sha256 $controllerBytes)) 'POST_INSTALL_HASH'
  Write-Host 'NO11_SAME_RUN_RECOVERY_INSTALL=PASS'
  Write-Host 'REVIEW_BUTTON=READONLY_OR_MANUAL_CONFIRMED_SAME_RUN_RESUME'
  Write-Host 'ORIGINAL_RUN_AND_LEDGER_REUSED=True'
  Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
  Write-Host 'WHITE_ONECLICK_LAYOUT_CHANGED=False'
  Write-Host 'FROZEN_STRATEGY_MODIFIED=False'
  Write-Host 'EXCEL_TOUCHED=False'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'BROKER_ORDER_RESENT=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  Write-Host ('BACKUP_ROOT='+$backup)
 }catch{
  if($uiReplaced){[IO.File]::WriteAllBytes($ui,$oldUiOriginal)}
  if($controllerReplaced){[IO.File]::WriteAllBytes($controller,$oldControllerOriginal)}
  if($engineReplaced){[IO.File]::WriteAllBytes($runtime,$oldEngineOriginal)}
  foreach($dest in $placed){Remove-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue}
  throw
 }
}finally{
 if(Test-Path -LiteralPath $temp -PathType Container){
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
 }
}
