# Fix JSON property-order sensitivity in the installed launcher, not its values.
# No Excel, RSS, Trade, approval, broker, handoff, registry or settings mutation.
param([switch]$Apply,[switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Assert-No11KeyOrder([bool]$Ok,[string]$Code){
 if(-not $Ok){throw ('NO11_SETTINGS_KEY_ORDER_'+$Code)}
}
function Get-No11BytesHash([byte[]]$Bytes){
 $h=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}
function Convert-No11SettingsKeyOrder([string]$Text){
 $old='(@($cfg.PSObject.Properties.Name) -join ''|'') -ceq ($required -join ''|'')'
 $new='(@($cfg.PSObject.Properties.Name | Sort-Object -CaseSensitive) -join ''|'') -ceq (@($required | Sort-Object -CaseSensitive) -join ''|'')'
 $a=[regex]::Matches($Text,[regex]::Escape($old)).Count
 $b=[regex]::Matches($Text,[regex]::Escape($new)).Count
 if($a -eq 0 -and $b -eq 1){return $Text}
 Assert-No11KeyOrder ($a -eq 1 -and $b -eq 0) 'EXACT_SETTINGS_COMPARATOR_NOT_FOUND'
 return $Text.Replace($old,$new)
}
function Test-No11LauncherSettings([string]$Source,[string]$SettingsPath){
 # Parse the whole candidate, but execute ONLY Need/NewSettings/Settings.
 # In particular, do not run the launcher's Mode switch, UI, or Trade code.
 $tokens=$null;$errors=$null
 $ast=[Management.Automation.Language.Parser]::ParseInput($Source,[ref]$tokens,[ref]$errors)
 Assert-No11KeyOrder ($errors.Count -eq 0) 'LAUNCHER_SYNTAX'
 $pieces=@()
 foreach($name in @('Need','NewSettings','Settings')){
  $matches=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
  Assert-No11KeyOrder ($matches.Count -eq 1) 'SETTINGS_FUNCTIONS_NOT_UNIQUE'
  $pieces+=@($matches[0].Extent.Text)
 }
 Assert-No11KeyOrder (Test-Path -LiteralPath $SettingsPath -PathType Leaf) 'SETTINGS_MISSING'
 $before=Get-No11BytesHash ([IO.File]::ReadAllBytes($SettingsPath))
 & {
  param($Definitions,$Path)
  $schema='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
  $settingsFile=$Path
  $store=Split-Path -Parent $Path
  . ([scriptblock]::Create($Definitions))
  [void](Settings)
 } ($pieces -join [Environment]::NewLine) $SettingsPath
 Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($SettingsPath))) -ceq $before) 'SETTINGS_BYTES_CHANGED'
}
function Get-No11KeyOrderLocalFile([string]$Path){
 Assert-No11KeyOrder ([IO.Path]::IsPathRooted($Path) -and (Test-Path -LiteralPath $Path -PathType Leaf)) 'LOCAL_FILE_REQUIRED'
 $p=[IO.Path]::GetFullPath($Path)
 $cursor=$p
 while(-not [string]::IsNullOrEmpty($cursor)){
  $item=Get-Item -LiteralPath $cursor -Force
  Assert-No11KeyOrder (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_PATH'
  $parent=Split-Path -Parent $cursor
  if($parent -ceq $cursor){break};$cursor=$parent
 }
 return $p
}
function Assert-No11KeyOrderQuiet {
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(?:powershell|pwsh|python|pythonw|node)(?:[.]exe)?$' -and
  [string]$_.CommandLine -match '(?:Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1|Start-No11PreopenStandby[.]ps1|Run-No11ReceivedSessionOperatorLive[.]ps1|no11_received_session_controller[.]py|no11_nightly_resume(?:_workeraware)?[.]py|Run-No11NightlyCycle[.]ps1|Prepare-No11WeeklyAfterCloseReadOnly[.]ps1|Prepare-No11NextSessionNightlyReadOnly[.]ps1|Run-No11RssDailyTrendCensusReadOnly[.]ps1|Run-No11WeeklyCandidateRefreshReadOnly[.]ps1|Capture-No11RssTrainingBatchReadOnly[.]ps1|Probe-No11Chart50ContinuousReadOnly[.]ps1|Invoke-No11MsiiOrder[.]ps1)'
 })
 Assert-No11KeyOrder ($rows.Count -eq 0) 'CLOSE_ONECLICK_OR_ACTIVE_WORKER'
}

if($OfflineSelfTest){
 Assert-No11KeyOrder (-not $Apply) 'SELFTEST_ARGUMENTS'
 $old='(@($cfg.PSObject.Properties.Name) -join ''|'') -ceq ($required -join ''|'')'
 $patched=Convert-No11SettingsKeyOrder $old
 Assert-No11KeyOrder ($patched -cne $old -and (Convert-No11SettingsKeyOrder $patched) -ceq $patched) 'SELFTEST'
 Write-Host 'NO11_SETTINGS_KEY_ORDER_SELFTEST=PASS'
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$lock=$null;$temporary=$null
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $bindingFile=Get-No11KeyOrderLocalFile (Join-Path $store 'automatic-inputs.json')
 $settingsFile=Get-No11KeyOrderLocalFile (Join-Path $store 'settings.json')
 $bindingRaw=[IO.File]::ReadAllBytes($bindingFile)
 $settingsRaw=[IO.File]::ReadAllBytes($settingsFile)
 $utf8=[Text.UTF8Encoding]::new($false,$true)
 $binding=$utf8.GetString($bindingRaw).TrimStart([char]0xFEFF) | ConvertFrom-Json
 Assert-No11KeyOrder ($binding.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $binding.orderTransmission -eq $false) 'BINDING_CONTRACT'
 $launcher=Get-No11KeyOrderLocalFile (Join-Path ([string]$binding.engine) 'windows\Start-No11UnifiedLauncher.ps1')
 if($Apply){
  Assert-No11KeyOrderQuiet
  $lockPath=Join-Path $store 'unified-refresh-install.lock'
  if(Test-Path -LiteralPath $lockPath){[void](Get-No11KeyOrderLocalFile $lockPath)}
  $lock=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 }
 $before=[IO.File]::ReadAllBytes($launcher)
 $beforeHash=Get-No11BytesHash $before
 $candidate=Convert-No11SettingsKeyOrder ($utf8.GetString($before))
 $after=$utf8.GetBytes($candidate)
 $afterHash=Get-No11BytesHash $after
 Test-No11LauncherSettings $candidate $settingsFile
 Write-Host 'NO11_SETTINGS_KEY_ORDER_ACTUAL_SETTINGS=PASS'
 $outcome='READY'
 if($beforeHash -ceq $afterHash){$outcome='ALREADY_APPLIED'}
 elseif($Apply){
  Assert-No11KeyOrderQuiet
  Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($bindingFile))) -ceq (Get-No11BytesHash $bindingRaw)) 'BINDING_CHANGED_DURING_REPAIR'
  Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($settingsFile))) -ceq (Get-No11BytesHash $settingsRaw)) 'SETTINGS_CHANGED_DURING_REPAIR'
  $temporary=$launcher+'.key-order-'+[guid]::NewGuid().ToString('N')+'.tmp'
  $stream=[IO.File]::Open($temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{$stream.Write($after,0,$after.Length);$stream.Flush($true)}finally{$stream.Dispose()}
  $backup=$launcher+'.key-order-'+$beforeHash+'.before'
  if(Test-Path -LiteralPath $backup){
   [void](Get-No11KeyOrderLocalFile $backup)
   Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($backup))) -ceq $beforeHash) 'BACKUP_CHANGED'
  }
  Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($launcher))) -ceq $beforeHash) 'LAUNCHER_CONCURRENT_EDIT'
  [IO.File]::Replace($temporary,$launcher,$backup,$false)
  $temporary=$null
  Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($launcher))) -ceq $afterHash) 'LAUNCHER_READBACK'
  Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($backup))) -ceq $beforeHash) 'BACKUP_READBACK'
  Test-No11LauncherSettings ($utf8.GetString([IO.File]::ReadAllBytes($launcher))) $settingsFile
  $outcome='PASS'
 }
 Assert-No11KeyOrder ((Get-No11BytesHash ([IO.File]::ReadAllBytes($settingsFile))) -ceq (Get-No11BytesHash $settingsRaw)) 'SETTINGS_BYTES_CHANGED'
 Write-Host ('NO11_SETTINGS_KEY_ORDER_REPAIR='+$outcome)
 Write-Host 'SETTINGS_VALUES_AND_BYTES_CHANGED=False'
 Write-Host 'DATA_RECAPTURED=False'
 Write-Host 'WHITE_ONECLICK_CHANGED=False'
}catch{
 $code=$_.Exception.Message
 if($code -cnotmatch '^NO11_[A-Z0-9_]+$'){$code='NO11_SETTINGS_KEY_ORDER_LOCAL_CHECK_OR_IO_FAILED'}
 Write-Host ('NO11_SETTINGS_KEY_ORDER_REPAIR=BLOCKED|'+$code)
 exit 2
}finally{
 if($null -ne $lock){$lock.Dispose()}
 if($null -ne $temporary -and (Test-Path -LiteralPath $temporary)){Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue}
 Write-Host 'TRADE_LAUNCHED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}
