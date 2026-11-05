# Surgically add weekly/daily progress to the EXISTING user's WHITE OneClick.
# Never replace theme/UI with Github's DARK baseline. No engine/Excel/trading
# API/approval/ledgers/marker changes. Code-only; no market orders.
param([switch]$Apply,[switch]$OpenOneClick,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$yes,[string]$reason){
 if(-not $yes){throw ('NO11_SELECTION_INSTALL_'+$reason)}
}
function Blob([byte[]]$raw){
 $header=[Text.Encoding]::ASCII.GetBytes(('blob '+$raw.Length)+[char]0)
 $bytes=New-Object byte[] ($header.Length+$raw.Length)
 [array]::Copy($header,0,$bytes,0,$header.Length)
 [array]::Copy($raw,0,$bytes,$header.Length,$raw.Length)
 $sha=[Security.Cryptography.SHA1]::Create()
 try{return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$sha.Dispose()}
}
function BlobFile([string]$f){return Blob ([IO.File]::ReadAllBytes($f))}
function ParsePs([string]$p){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$errors)
 Need ($errors.Count -eq 0) 'POWERSHELL_PARSE_FAILED'
}
function NoActiveOneClick{
 $running=@(Get-CimInstance Win32_Process|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Invoke-No11MsiiOrder|Run-No11NightlyCycle[.]ps1|Prepare-No11WeeklyAfterCloseReadOnly'
 })
 Need ($running.Count -eq 0) 'CLOSE_WHITE_ONECLICK_OR_RUNNING_NATIVE_TASK_FIRST'
}
if($OfflineSelfTest){
 Need (-not $Apply -and -not $OpenOneClick) 'SELFTEST_FLAGS'
 Write-Host 'NO11_SELECTION_INSTALL_OFFLINE_SELFTEST=PASS'
 Write-Host 'WHITE_ONECLICK_REPLACED=False'
 Write-Host 'EXCEL_TOUCHED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
Need $Apply.IsPresent 'EXPLICIT_APPLY_REQUIRED'
$root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
$one=Join-Path $root 'oneclick'
$white=Join-Path $one 'Start-No11OneClick.ps1'
$helper=Join-Path $one 'no11_selection_status.py'
$bindingFile=Join-Path $root 'automatic-inputs.json'
Need ((Test-Path -LiteralPath $white -PathType Leaf) -and
      (Test-Path -LiteralPath $bindingFile -PathType Leaf) -and
      -not (Test-Path -LiteralPath $helper)) 'WHITE_INSTALL_MISSING_OR_SELECTION_HELPER_CONFLICT'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8|ConvertFrom-Json
Need ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and
      $binding.orderTransmission -eq $false -and
      [IO.Path]::IsPathRooted([string]$binding.python) -and
      (Test-Path -LiteralPath ([string]$binding.python) -PathType Leaf)) 'BOUND_PYTHON_INVALID'
NoActiveOneClick
$python=[string]$binding.python
$whiteBefore=[IO.File]::ReadAllBytes($white)
$work=Join-Path $env:TEMP ('no11-selection-ui-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($work)
$manifest=[ordered]@{
 'selection.py'=@('research/no11-morning-master-20261103/no11_selection_status.py','626d7a7a010967015ae26ccfd0f4d266eb05fe97')
 'patch.py'=@('research/no11-morning-master-20261103/patch_oneclick_selection_display.py','ba2d411556eeccc985d1ae04bdb5fcd23dee8367')
}
try{
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $commit='a03b7445f7aae17c05e8f088c1bc3c145c58ec58'
 $base='https://raw.githubusercontent.com/Iam-2squared/ark-terminal/'+$commit+'/'
 foreach($name in $manifest.Keys){
  $f=Join-Path $work $name
  Invoke-WebRequest -UseBasicParsing -Uri ($base+$manifest[$name][0]) -OutFile $f -ErrorAction Stop
  Need ((BlobFile $f) -ceq [string]$manifest[$name][1]) ('DOWNLOAD_BLOB_PIN_'+$name.ToUpperInvariant())
 }
 $candidate=Join-Path $work 'candidate-white.ps1'
 & $python -B (Join-Path $work 'patch.py') --original $white --candidate $candidate
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $candidate -PathType Leaf)) 'WHITE_UI_SAFE_PATCH_REJECTED'
 ParsePs $candidate
 $newWhite=[IO.File]::ReadAllBytes($candidate)
 $newHelper=[IO.File]::ReadAllBytes((Join-Path $work 'selection.py'))
 Need ($newWhite.Length -gt $whiteBefore.Length -and
       ($newWhite.Length-$whiteBefore.Length) -lt 4500) 'UI_PATCH_SIZE'
 # Before writing, exercise only the external pure helper's parser on the
 # already-pinned daily binding; it must not touch Excel or submit orders.
 & $python -B (Join-Path $work 'selection.py') --binding $bindingFile
 Need ($LASTEXITCODE -eq 0) 'SELECTION_STATUS_READER_FAILED'
 NoActiveOneClick
 Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
       ([Convert]::ToBase64String($whiteBefore)) -and
       -not (Test-Path -LiteralPath $helper)) 'WHITE_UI_CHANGED_BEFORE_INSTALL'
 $backup=Join-Path $root ('oneclick-selection-status-backup-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($backup)
 [IO.File]::WriteAllBytes((Join-Path $backup 'Start-No11OneClick.WHITE.before.ps1'),$whiteBefore)
 $replacement=Join-Path $one ('.no11-selection-white-'+[guid]::NewGuid().ToString('N')+'.tmp')
 $backupWindows=Join-Path $one ('.no11-selection-white-prior-'+[guid]::NewGuid().ToString('N')+'.bak')
 try{
  [IO.File]::WriteAllBytes($replacement,$newWhite)
  [IO.File]::Replace($replacement,$white,$backupWindows)
  $f=[IO.File]::Open($helper,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$f.Write($newHelper,0,$newHelper.Length);$f.Flush($true)}
  finally{$f.Dispose()}
  Need (([Convert]::ToBase64String([IO.File]::ReadAllBytes($white))) -ceq
        ([Convert]::ToBase64String($newWhite)) -and
        (BlobFile $helper) -ceq [string]$manifest['selection.py'][1]) 'POST_INSTALL_VERIFY'
  ParsePs $white
 }catch{
  [IO.File]::WriteAllBytes($white,$whiteBefore)
  if(Test-Path -LiteralPath $helper -PathType Leaf){
   Remove-Item -LiteralPath $helper -Force -ErrorAction SilentlyContinue
  }
  throw
 }
 Write-Host 'NO11_WEEKLY_DAILY_SELECTION_UI_INSTALL=PASS'
 Write-Host 'WEEKLY_STATUS=READ_ONLY_VERIFIED_WEEKLY_SOURCE_OR_CARRIED'
 Write-Host 'DAILY_STATUS=READ_ONLY_PINNED_TARGET_SESSION'
 Write-Host 'WHITE_ONECLICK_THEME_CHANGED=False'
 Write-Host 'EXISTING_BUTTONS_OR_CLICK_HANDLERS_CHANGED=False'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host ('BACKUP_ROOT='+$backup)
 if($OpenOneClick){
  $proc=Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$white+'"')) -WorkingDirectory $one -WindowStyle Normal -PassThru
  Write-Host ('WHITE_ONECLICK_OPEN_REQUESTED_PID='+$proc.Id)
 }
}finally{
 if(Test-Path -LiteralPath $work -PathType Container){
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
 }
}
