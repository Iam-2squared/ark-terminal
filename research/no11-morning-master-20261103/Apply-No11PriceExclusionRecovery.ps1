# 2026-11-05: surgical installation of verified 41->39 automatic filtering.
# DO NOT replace the approved WHITE OneClick UI, engine or order modules.
# This script installs code only and NEVER launches Trade or broker orders.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw ('NO11_FILTER_INSTALL_'+$code)}}
function Blob([byte[]]$raw){
 $utf=[Text.UTF8Encoding]::new($false,$true)
 $s=$utf.GetString($raw)
 $s=$s.Replace(([string][char]13+[char]10),[string][char]10)
 $data=[Text.Encoding]::UTF8.GetBytes($s)
 $head=[Text.Encoding]::ASCII.GetBytes(('blob '+$data.Length)+[char]0)
 $joined=New-Object byte[] ($head.Length+$data.Length)
 [array]::Copy($head,0,$joined,0,$head.Length)
 [array]::Copy($data,0,$joined,$head.Length,$data.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($joined))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function Sha([byte[]]$bytes){
 $sha=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function ParsePowerShell([string]$file){
 $t=$null;$e=$null
 [void][Management.Automation.Language.Parser]::ParseFile($file,[ref]$t,[ref]$e)
 Need ($e.Count -eq 0) 'POWERSHELL_SYNTAX'
}
function AssertNativeStopped {
 $busy=@(Get-CimInstance Win32_Process | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder'
 })
 Need ($busy.Count -eq 0) 'LIVE_PROCESS_RUNNING'
}
if($OfflineSelfTest){
 Need (-not $Apply) 'SELFTEST_FLAGS'
 Write-Host 'NO11_FILTER_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_THEME_MODIFIED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'APPLY_EXPLICITLY_REQUIRED'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$bindingFile=Join-Path $root 'automatic-inputs.json'
$whiteUi=Join-Path $root 'oneclick\Start-No11OneClick.ps1'
$retryFile=Join-Path $root 'oneclick\Recover-No11FilteredMorning.ps1'
Need ((Test-Path -LiteralPath $bindingFile -PathType Leaf) -and
      (Test-Path -LiteralPath $whiteUi -PathType Leaf) -and
      (Test-Path -LiteralPath (Split-Path -Parent $retryFile) -PathType Container)) 'ONECLICK_INSTALL_REQUIRED'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      $binding.manualEvidenceRequired -eq $false -and
      $binding.manualPriceInputRequired -eq $false -and
      $binding.automatic -is [string] -and $binding.bridge -is [string]) 'BINDING_UNSAFE'
$automatic=[string]$binding.automatic
$bridge=[string]$binding.bridge
Need ([IO.Path]::IsPathRooted($automatic) -and
      [IO.Path]::IsPathRooted($bridge) -and
      (Test-Path -LiteralPath $automatic -PathType Leaf) -and
      (Test-Path -LiteralPath $bridge -PathType Leaf) -and
      [IO.Path]::GetFileName($automatic) -ceq 'automatic_morning.py' -and
      [IO.Path]::GetFileName($bridge) -ceq 'launcher_automatic_bridge_v4.py') 'PINNED_RUNTIME_PATHS'
Need (-not (Test-Path -LiteralPath $retryFile)) 'RECOVERY_HELPER_ALREADY_PRESENT'
AssertNativeStopped
$ref='c592a318ca913fe82f835253dbfc9f1c89ab6f75'
$prefix='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$ref+'/research/no11-morning-master-20261103/'
$pins=[ordered]@{
 'automatic_morning.py'='ac193bb0485ef08f93f1b253c88e42fa92664c5a'
 'launcher_automatic_bridge_v4.py'='bdd6d1c8524053bf611bbc56e89ceda20afa1c03'
 'Recover-No11FilteredMorning.ps1'='d844d7a45cb9bbcd247258ca16dc7797cbd4a6b4'
}
$temps=Join-Path $env:TEMP ('no11-filter-install-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temps)
$files=@{}
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 foreach($name in $pins.Keys){
  $target=Join-Path $temps $name
  Invoke-WebRequest -UseBasicParsing -Uri ($prefix+$name) -OutFile $target -ErrorAction Stop
  $raw=[IO.File]::ReadAllBytes($target)
  Need ((Blob $raw) -ceq $pins[$name]) 'SOURCE_HASH_DIFFERENT'
  $files[$name]=$target
 }
 ParsePowerShell $files['Recover-No11FilteredMorning.ps1']
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $files['Recover-No11FilteredMorning.ps1'] -OfflineSelfTest | Out-Null
 Need ($LASTEXITCODE -eq 0) 'RECOVERY_SELFTEST'
 $py=[string]$binding.python
 Need ([IO.Path]::IsPathRooted($py) -and (Test-Path -LiteralPath $py -PathType Leaf)) 'PINNED_PYTHON_NOT_FOUND'
 foreach($name in @('automatic_morning.py','launcher_automatic_bridge_v4.py')){
  $code=[IO.File]::ReadAllText($files[$name])
  $tokens=@('compile(open(', 'No11')
  & $py -B -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8-sig').read())" $files[$name]
  Need ($LASTEXITCODE -eq 0) 'NEW_PYTHON_SOURCE_SYNTAX'
 }
 $oldAuto=[IO.File]::ReadAllBytes($automatic)
 $oldBridge=[IO.File]::ReadAllBytes($bridge)
 $oldBinding=[IO.File]::ReadAllBytes($bindingFile)
 $oldWhite=Sha ([IO.File]::ReadAllBytes($whiteUi))
 Need ((Sha $oldAuto) -ceq [string]$binding.automaticSha256 -and
       (Sha $oldBridge) -ceq [string]$binding.bridgeSha256 -and
       (Blob $oldAuto) -ceq '2ee5fd79ba8f06372585d2fdb2ea84df29b2f0a4' -and
       (Blob $oldBridge) -ceq '224766266bfe953bc6dfa1abda28230fae6ff69f' ) 'OLD_BOUND_CODE_CHANGED_OR_NOT_REVIEWED'
 $newAuto=[IO.File]::ReadAllBytes($files['automatic_morning.py'])
 $newBridge=[IO.File]::ReadAllBytes($files['launcher_automatic_bridge_v4.py'])
 Need (([IO.File]::ReadAllText($files['launcher_automatic_bridge_v4.py'])).Contains(
       "AUTOMATIC_BLOB = 'ac193bb0485ef08f93f1b253c88e42fa92664c5a'") -and
       ([IO.File]::ReadAllText($files['automatic_morning.py'])).Contains('FILTER_NODE') -and
       ([IO.File]::ReadAllText($files['automatic_morning.py'])).Contains('FILTER_ADMISSION_PARTITION')) 'FILTER_PATCH_INTEGRITY'
 $binding.automaticSha256=Sha $newAuto
 $binding.bridgeSha256=Sha $newBridge
 $newBinding=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $binding -Depth 30 -Compress)+[char]10)
 AssertNativeStopped
 Need ((Sha ([IO.File]::ReadAllBytes($automatic))) -ceq (Sha $oldAuto) -and
       (Sha ([IO.File]::ReadAllBytes($bridge))) -ceq (Sha $oldBridge) -and
       (Sha ([IO.File]::ReadAllBytes($bindingFile))) -ceq (Sha $oldBinding)) 'CONCURRENT_RUNTIME_CHANGE'
 $backup=Join-Path $root ('morning-filter-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'automatic.before.py'),$oldAuto)
 [IO.File]::WriteAllBytes((Join-Path $backup 'bridge.before.py'),$oldBridge)
 [IO.File]::WriteAllBytes((Join-Path $backup 'binding.before.json'),$oldBinding)
 $written=@()
 $placed=$false
 try{
  foreach($pair in @(@($automatic,$newAuto),@($bridge,$newBridge),@($bindingFile,$newBinding))){
   $target=[string]$pair[0]
   $raw=[byte[]]$pair[1]
   $candidate=Join-Path (Split-Path -Parent $target) ('.no11-filter-'+[guid]::NewGuid().ToString('N')+'.tmp')
   $atomicBackup=Join-Path (Split-Path -Parent $target) ('.no11-filter-before-'+[guid]::NewGuid().ToString('N')+'.bak')
   [IO.File]::WriteAllBytes($candidate,$raw)
   [IO.File]::Replace($candidate,$target,$atomicBackup)
   $written+=,$target
  }
  [IO.File]::WriteAllBytes($retryFile,[IO.File]::ReadAllBytes($files['Recover-No11FilteredMorning.ps1']))
  $placed=$true
  Need ((Sha ([IO.File]::ReadAllBytes($automatic))) -ceq (Sha $newAuto) -and
        (Sha ([IO.File]::ReadAllBytes($bridge))) -ceq (Sha $newBridge) -and
        (Sha ([IO.File]::ReadAllBytes($bindingFile))) -ceq (Sha $newBinding) -and
        (Sha ([IO.File]::ReadAllBytes($whiteUi))) -ceq $oldWhite) 'POST_INSTALL_SOURCE_OR_WHITE_UI_DIFFERENT'
  Write-Host 'NO11_FILTERED_MORNING_INSTALL=PASS'
  Write-Host 'SOURCE_SCOPE=VERIFIED_39_ONLY_REJECT_3003_T_7616_T'
  Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
  Write-Host 'WHITE_ONECLICK_LAYOUT_CHANGED=False'
  Write-Host 'PREOPEN_APPROVAL_CHANGED=False'
  Write-Host 'TRADE_LAUNCHED=False'
  Write-Host 'ORDER_TRANSMISSION=False'
  Write-Host ('BACKUP_ROOT='+$backup)
 }catch{
  # Even on a partial failure, recover all originals from byte-preserved backup.
  [IO.File]::WriteAllBytes($automatic,$oldAuto)
  [IO.File]::WriteAllBytes($bridge,$oldBridge)
  [IO.File]::WriteAllBytes($bindingFile,$oldBinding)
  if($placed -and (Test-Path -LiteralPath $retryFile -PathType Leaf)){
   Remove-Item -LiteralPath $retryFile -Force
  }
  throw
 }
}finally{
 if(Test-Path -LiteralPath $temps -PathType Container){
  Remove-Item -LiteralPath $temps -Recurse -Force -ErrorAction SilentlyContinue
 }
}
