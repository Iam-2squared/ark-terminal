# Ark No.1.1 CLASSIC rich-UI standalone launcher; old No.1.1 files untouched.
# Shares the already-pinned Frozen simulation and RSS account observers.
# Only original frozen Shadow simulator can run, after its own Preflight.
# Excel account observation is read-only; no RSS order functions or model fits.
param(
 [string]$AccountWorkbookPath='',
 [string]$MarketWorkbookPath='',
 [string]$MarketSpeedShortcut='',
 [string]$EngineRoot='C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011',
 [string]$PreparedConfigFile='',
 [string]$BootstrapTemplateFile='',
 [string]$SecurityEvidenceFile='',
 [string]$EvidenceDocumentsDir='',
 [string]$PreviousCaptureDir='',
 [string]$PrivateRoot='',
 [ValidateRange(1024,65535)][int]$Port=8769,
 [switch]$SkipMarketSpeed,
 [switch]$SkipExcel,
 [switch]$NoBrowser,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ui=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\ui\ark_shadow_classic.py'))
$runner=Join-Path $EngineRoot 'windows\Run-No11ReceivedSessionReadOnly.ps1'
$prepare=Join-Path $EngineRoot 'windows\Prepare-No11ReceivedInputsReadOnly.ps1'
$observer=Join-Path $EngineRoot 'windows\Observe-No11AccountReadOnly.ps1'
$session=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd')
$desktop=[Environment]::GetFolderPath('Desktop')
if(-not $AccountWorkbookPath){$AccountWorkbookPath=Join-Path $desktop 'Ark_No11_MSII_RSS.xlsx'}
if(-not $MarketWorkbookPath){$MarketWorkbookPath=Join-Path $desktop 'Ark_No11_MARKET_RSS.xlsx'}
if(-not $PrivateRoot){$PrivateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\shadow-oneclick-classic'}
$statusFile=Join-Path $PrivateRoot 'launcher-status.json'
$settingsFile=Join-Path $PrivateRoot 'launcher-settings.json'
$steps=[ordered]@{marketSpeed='NOT_CHECKED';excel='NOT_CHECKED';account='NOT_CHECKED';shadow='NOT_CONFIGURED'}
$script:stage='ENTRY'
function Need([bool]$ok,[string]$code) {if(-not $ok){throw ('ARK_SHADOW_'+$code)}}
function NowJst {[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:sszzz')}
function CheckPath([string]$p,[string]$code,[bool]$dir=$false){
 Need ([IO.Path]::IsPathRooted($p)) ($code+'_ABSOLUTE_REQUIRED')
 $p=[IO.Path]::GetFullPath($p);$i=Get-Item -LiteralPath $p -ErrorAction Stop
 Need ($dir -eq [bool]$i.PSIsContainer) ($code+'_TYPE_INVALID')
 Need (($i.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) ($code+'_REPARSE_FORBIDDEN')
 return $p
}
function Q([string]$s){
 Need (-not [string]::IsNullOrWhiteSpace($s) -and -not $s.Contains('"') -and
  -not $s.Contains([char]10) -and -not $s.Contains([char]13)) 'UNSAFE_ARGUMENT'
 return '"'+$s+'"'
}
function ArgLine([string[]]$values){return (($values|ForEach-Object {Q ([string]$_)}) -join ' ')}
function Publish([string]$state,[string]$reason){
 if(-not (Test-Path -LiteralPath $PrivateRoot -PathType Container)){return}
 $record=[ordered]@{schemaId='ARK_SHADOW_ONECLICK_LAUNCH_STATUS_V1';status=$state;
  sessionDate=$session;updatedAtJst=NowJst;steps=$steps;message=$reason;
  productionReady=$false;orderTransmission=$false}
 $tmp=Join-Path $PrivateRoot ('ark-shadow-'+[guid]::NewGuid().ToString('N')+'.tmp')
 try{
  [IO.File]::WriteAllText($tmp,(ConvertTo-Json -InputObject $record -Depth 10 -Compress),[Text.UTF8Encoding]::new($false))
  # Windows can temporarily hold the destination while the local UI reads it.
  # Retry ONLY the atomic status-file replacement (never a workbook/order).
  $stored=$false
  for($attempt=0;$attempt -lt 8;$attempt++){
   try{
    if([IO.File]::Exists($statusFile)){[IO.File]::Replace($tmp,$statusFile,$null)}
    else{[IO.File]::Move($tmp,$statusFile)}
    $stored=$true;break
   }catch [IO.IOException]{
    if($attempt -eq 7){throw}
    Start-Sleep -Milliseconds 90
   }
  }
  Need $stored 'STATUS_WRITE_FAILED'
 }finally{if([IO.File]::Exists($tmp)){[IO.File]::Delete($tmp)}}
 Write-Host ('ARK_SHADOW_LAUNCH_STATUS='+$state)
 Write-Host 'ORDER_TRANSMISSION=False'
}
function PythonExe {
 $pinned=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 if(Test-Path -LiteralPath $pinned -PathType Leaf){return @{exe=$pinned;prefix=@()}}
 $py=Get-Command py.exe -ErrorAction SilentlyContinue
 if($py){return @{exe=$py.Source;prefix=@('-3.12')}}
 $p=Get-Command python.exe -ErrorAction SilentlyContinue
 Need ($null -ne $p) 'PYTHON_MISSING'
 return @{exe=$p.Source;prefix=@()}
}
function Spawn([string]$exe,[string[]]$values,[string]$label){
 $id=[guid]::NewGuid().ToString('N')
 $out=Join-Path $PrivateRoot ($label+'-'+$id+'.stdout.log')
 $err=Join-Path $PrivateRoot ($label+'-'+$id+'.stderr.log')
 $argLine=ArgLine $values
 return Start-Process -FilePath $exe -ArgumentList $argLine -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -ErrorAction Stop
}
function LocalUiAlive{
 try{$r=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$Port+'/api/health') -TimeoutSec 2 -ErrorAction Stop
  return ($r.status -ceq 'READ_ONLY' -and $r.sessionDate -ceq $session -and $r.orderTransmission -eq $false)}
 catch{return $false}
}
function PortBusy{
 $c=New-Object Net.Sockets.TcpClient
 try{
  $pending=$c.BeginConnect('127.0.0.1',$Port,$null,$null)
  if(-not $pending.AsyncWaitHandle.WaitOne(250)){return $false}
  $c.EndConnect($pending);return $true
 }catch{return $false}finally{$c.Close()}
}
function SettingValue([object]$record,[string]$key){
 $property=$record.PSObject.Properties[$key]
 if($null -eq $property -or $null -eq $property.Value){return ''}
 return [string]$property.Value
}
function ReadSettings {
 if(-not (Test-Path -LiteralPath $settingsFile -PathType Leaf)){return}
 $s=Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($s.schemaId -ceq 'ARK_SHADOW_ONECLICK_SETTINGS_V1' -and $s.orderTransmission -eq $false) 'SETTINGS_INVALID'
 $allowed=@('schemaId','orderTransmission','preparedConfigFile','bootstrapTemplateFile',
  'securityEvidenceFile','evidenceDocumentsDir','previousCaptureDir')
 Need (@($s.PSObject.Properties.Name|Where-Object {$_ -notin $allowed}).Count -eq 0) 'SETTINGS_UNKNOWN_FIELDS'
 if(-not $script:PreparedConfigFile){$script:PreparedConfigFile=SettingValue $s 'preparedConfigFile'}
 if(-not $script:BootstrapTemplateFile){$script:BootstrapTemplateFile=SettingValue $s 'bootstrapTemplateFile'}
 if(-not $script:SecurityEvidenceFile){$script:SecurityEvidenceFile=SettingValue $s 'securityEvidenceFile'}
 if(-not $script:EvidenceDocumentsDir){$script:EvidenceDocumentsDir=SettingValue $s 'evidenceDocumentsDir'}
 if(-not $script:PreviousCaptureDir){$script:PreviousCaptureDir=SettingValue $s 'previousCaptureDir'}
}
function CheckWorkbook([string]$p){
 $p=CheckPath $p 'WORKBOOK' $false
 Need ([IO.Path]::GetExtension($p) -ieq '.xlsx' -and (Get-Item -LiteralPath $p).Length -le 100000000) 'WORKBOOK_XLSX_REQUIRED'
 Add-Type -AssemblyName System.IO.Compression
 $s=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 $z=$null
 try{
  $z=[IO.Compression.ZipArchive]::new($s,[IO.Compression.ZipArchiveMode]::Read,$false)
  Need ($z.Entries.Count -ge 2 -and $z.Entries.Count -le 1024) 'WORKBOOK_ZIP_LAYOUT'
  foreach($entry in $z.Entries){
   Need ($entry.Length -le 12000000 -and $entry.FullName -notmatch '(?i)(vbaProject|xl/macrosheets/|\.bin$)') 'WORKBOOK_BINARY_OR_OVERSIZE'
   if($entry.FullName -notmatch '(?i)\.(xml|rels)$'){continue}
   $reader=$null
   try{
    $reader=New-Object IO.StreamReader($entry.Open())
    $body=$reader.ReadToEnd()
    if($body -match '(?i)Rss(?:StockOrder|Margin(?:Open|Close)Order|FOP(?:Multi)?(?:Open|Close)Order|FOPModifyOrder|FOPCancelOrder|ModifyOrder|CancelOrder)\b'){
     throw 'ARK_SHADOW_ORDER_FORMULA_FORBIDDEN'
    }
   }finally{if($null -ne $reader){$reader.Dispose()}}
  }
 }finally{if($null -ne $z){$z.Dispose()};$s.Dispose()}
 return $p
}
function BookState([string]$account,[string]$market){
 $p=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 if($p.Count -eq 0){return 'NO_EXCEL'}
 if($p.Count -ne 1){return 'MULTIPLE_EXCEL_PROCESSES'}
 try{
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  $paths=@();foreach($book in $excel.Workbooks){$paths+=@([IO.Path]::GetFullPath([string]$book.FullName))}
  if($paths.Count -gt 2){return 'OTHER_WORKBOOK_PRESENT'}
  if(@($paths|Where-Object {$_ -ieq $account}).Count -gt 1 -or
     @($paths|Where-Object {$_ -ieq $market}).Count -gt 1){return 'DUPLICATE_WORKBOOK'}
  if($paths.Count -eq 2){
   if(@($paths|Where-Object {$_ -ieq $account}).Count -ne 1 -or
      @($paths|Where-Object {$_ -ieq $market}).Count -ne 1){return 'OTHER_WORKBOOK_PRESENT'}
   $a=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
   $m=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
   if($a.Worksheets.Count -ne 1 -or $a.Worksheets.Item(1).Name -cne 'ARK_ACCOUNT_READONLY' -or
      $m.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){return 'ORIGINAL_SHEET_MISMATCH'}
   return 'READY'
  }
  if($paths.Count -eq 1){
   if($paths[0] -ieq $account){return 'NEED_MARKET'}
   if($paths[0] -ieq $market){return 'NEED_ACCOUNT'}
   return 'OTHER_WORKBOOK_PRESENT'
  }
  return 'NO_WORKBOOK'
 }catch{return 'EXCEL_COM_UNAVAILABLE'}
}
function EnsureBooks([string]$account,[string]$market){
 if($SkipExcel){return (BookState $account $market)}
 $openedA=$false;$openedM=$false
 for($i=0;$i -lt 80;$i++){
  $state=BookState $account $market
  if($state -ceq 'READY'){return $state}
  if($state -in @('NO_EXCEL','NO_WORKBOOK') -and -not $openedA){
   Start-Process -FilePath $account -ErrorAction Stop;$openedA=$true
  }elseif($state -ceq 'NEED_ACCOUNT' -and -not $openedA){
   Start-Process -FilePath $account -ErrorAction Stop;$openedA=$true
  }elseif($state -ceq 'NEED_MARKET' -and -not $openedM){
   Start-Process -FilePath $market -ErrorAction Stop;$openedM=$true
  }elseif($state -in @('MULTIPLE_EXCEL_PROCESSES','OTHER_WORKBOOK_PRESENT',
    'DUPLICATE_WORKBOOK','ORIGINAL_SHEET_MISMATCH')){return $state}
  Start-Sleep -Milliseconds 750
 }
 return (BookState $account $market)
}
function FindMarketSpeed {
 if($MarketSpeedShortcut){
  Need ([IO.Path]::IsPathRooted($MarketSpeedShortcut) -and
   [IO.Path]::GetExtension($MarketSpeedShortcut) -ieq '.lnk' -and
   (Test-Path -LiteralPath $MarketSpeedShortcut -PathType Leaf)) 'MARKETSPEED_SHORTCUT_INVALID'
  return $MarketSpeedShortcut
 }
 $roots=@($desktop,[Environment]::GetFolderPath('CommonDesktopDirectory'),
  [Environment]::GetFolderPath('StartMenu'),[Environment]::GetFolderPath('CommonStartMenu'))
 $hits=@()
 foreach($r in $roots|Where-Object {$_ -and (Test-Path -LiteralPath $_ -PathType Container)}){
  $hits+=@(Get-ChildItem -LiteralPath $r -Recurse -Filter '*.lnk' -File -ErrorAction SilentlyContinue |
   Where-Object {$_.BaseName -match '(?i)(Market\s*Speed\s*(II|2)|マーケットスピード\s*(II|Ⅱ|2|２))' -and
    $_.BaseName -notmatch '(?i)(Setup|Uninstall|削除|アンインストール)'})
 }
 $hits=@($hits|Sort-Object FullName -Unique)
 if($hits.Count -eq 1){return $hits[0].FullName}
 return ''
}
function Config([string]$file){
 $full=CheckPath $file 'CONFIG' $false
 Need ((Get-Item -LiteralPath $full).Length -le 100000) 'CONFIG_OVERSIZE'
 $c=Get-Content -LiteralPath $full -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($c.schemaId -ceq 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1' -and
  $c.sessionDate -ceq $session -and
  $c.productionReady -eq $false -and $c.orderTransmission -eq $false) 'SHADOW_CONFIG_NOT_VERIFIED'
 $names=@($c.PSObject.Properties.Name)
 Need ('shadowAccountConfig' -in $names -and 'h235ModelRoot' -in $names -and
  'brokerExecutionConfig' -notin $names -and 'orderIdWorkbookPath' -notin $names) 'SHADOW_SIMULATOR_ONLY'
 [void](CheckPath ([string]$c.privateRoot) 'ORIGINAL_SHADOW_PRIVATE' $true)
 return $c
}
function StartObserver([string]$account,[string]$output){
 if(-not (Test-Path -LiteralPath $observer -PathType Leaf)){$steps.account='BLOCKED';return}
 $stop=Join-Path $PrivateRoot ('observer-stop-'+[guid]::NewGuid().ToString('N')+'.flag')
 $argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$observer,
  '-WorkbookPath',$account,'-OutputFile',$output,'-StopFile',$stop,
  '-Samples','10000','-PollSeconds','6')
 try{
  $p=Spawn 'powershell.exe' $argsList 'account-observer'
  $steps.account='START_REQUESTED'
  Write-Host ('ARK_SHADOW_ACCOUNT_OBSERVER_PID='+$p.Id)
 }catch{$steps.account='BLOCKED'}
}
function Preflight([string]$file,[string]$python){
 $lines=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -ConfigFile $file -PythonExecutable $python -PreflightOnly)
 $good=@($lines|Where-Object {$_ -ceq 'NO11_BOOTSTRAP_PREFLIGHT=EXISTING_ASSETS_LOADED_NOT_LIVE_VERIFIED'}).Count -eq 1
 return ($LASTEXITCODE -eq 0 -and $good)
}
if($OfflineSelfTest){
 Need (Test-Path -LiteralPath $ui -PathType Leaf) 'UI_MISSING'
 foreach($name in @('index.html','ark-readonly-overlay.js','ark-shadow-classic-bridge.js')){
  Need (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $ui) ('classic\'+$name)) -PathType Leaf) 'ORIGINAL_CLASSIC_ASSET_MISSING'
 }
 Need (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $ui) 'ark_shadow_ui.py') -PathType Leaf) 'READONLY_BACKEND_MISSING'
 Write-Host 'ARK_SHADOW_OFFLINE_SELFTEST=PASS'
 Write-Host 'ARK_SHADOW_OLD_LAUNCHER_TOUCHED=False'
 Write-Host 'ARK_SHADOW_EXCEL_STARTED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$mutex=[Threading.Mutex]::new($false,'Local\ArkTerminal_ShadowOneClick_ReadOnly')
$held=$false
try{
 try{$held=$mutex.WaitOne(0)}
 catch [Threading.AbandonedMutexException]{throw 'ARK_SHADOW_PREVIOUS_LAUNCH_ABANDONED_REVIEW'}
 Need $held 'LAUNCH_ALREADY_IN_PROGRESS'
 # Never start a second independent account observer or Shadow controller
 # when the original new-style oneclick is already live on port 8768.
 if($Port -ne 8768){
  $other=$null
  try{$other=Invoke-RestMethod -Uri 'http://127.0.0.1:8768/api/status' -TimeoutSec 2 -ErrorAction Stop}catch{}
  if($null -ne $other -and $other.schemaId -ceq 'ARK_SHADOW_LOCAL_DASHBOARD_V1' -and
     $other.orderTransmission -eq $false){
   $accountState=''
   if($null -ne $other.launcher -and $null -ne $other.launcher.steps){
    $stepsOther=$other.launcher.steps
    $property=$stepsOther.PSObject.Properties['account']
    if($null -ne $property -and $null -ne $property.Value){$accountState=[string]$property.Value}
   }
   if($accountState -in @('START_REQUESTED','ORIGINAL_CONTROLLER_OBSERVER','AWAITING_ORIGINAL_CONTROLLER')){
    throw 'ARK_SHADOW_OTHER_ACCOUNT_OBSERVER_ALREADY_ACTIVE'
   }
  }
 }
 if(PortBusy){
  $classic=$null
  try{$classic=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$Port+'/api/classic-health') -TimeoutSec 2 -ErrorAction Stop}catch{}
  Need ($classic -and $classic.schemaId -ceq 'ARK_SHADOW_CLASSIC_UI_V1' -and $classic.orderTransmission -eq $false) 'CLASSIC_PORT_OCCUPIED_BY_OTHER_SERVICE'
  Need (LocalUiAlive) 'PORT_OCCUPIED_BY_OTHER_SERVICE'
  if(-not $NoBrowser){Start-Process ('http://127.0.0.1:'+$Port+'/')}
  Write-Host 'ARK_SHADOW_EXISTING_UI_REUSED=True'
  Write-Host 'ORDER_TRANSMISSION=False'
  exit 0
 }
 Need ([IO.Path]::IsPathRooted($PrivateRoot)) 'PRIVATE_ROOT_ABSOLUTE_REQUIRED'
 [void][IO.Directory]::CreateDirectory($PrivateRoot)
 $PrivateRoot=CheckPath $PrivateRoot 'PRIVATE_ROOT' $true
 $statusFile=Join-Path $PrivateRoot 'launcher-status.json'
 $settingsFile=Join-Path $PrivateRoot 'launcher-settings.json'
 $script:stage='READ_SETTINGS'
 ReadSettings
 Need (-not ($PreparedConfigFile -and $BootstrapTemplateFile)) 'TWO_CONFIG_MODES_FORBIDDEN'
 $script:stage='VERIFY_WORKBOOK_FILES'
 $account=CheckWorkbook $AccountWorkbookPath
 $market=CheckWorkbook $MarketWorkbookPath
 Need (-not $account.Equals($market,[StringComparison]::OrdinalIgnoreCase)) 'SAME_WORKBOOK_FORBIDDEN'
 $activeAccount=Join-Path $PrivateRoot ('account-source-'+$session+'.json')
 $configObj=$null;$requested=$false;$shadowRoot=''
 if($PreparedConfigFile){$configObj=Config $PreparedConfigFile;$requested=$true}
 elseif($BootstrapTemplateFile){$configObj=Config $BootstrapTemplateFile;$requested=$true}
 if($requested){$shadowRoot=[string]$configObj.privateRoot}
 else{
  $shadowRoot=Join-Path $PrivateRoot 'unconfigured-simulator'
  [void][IO.Directory]::CreateDirectory($shadowRoot)
 }
 $secondary=if($requested){Join-Path $shadowRoot ('account-source-'+$session+'.json')}else{$activeAccount}
 $script:stage='SELECT_LOCAL_PYTHON'
 $py=PythonExe
 $script:stage='PUBLISH_INITIAL'
 Publish 'STARTING' 'Starting original rich read-only Ark UI with Shadow adapter'
 $uiArgs=@($py.prefix)+@($ui,'--port',[string]$Port,'--session',$session,
  '--launch-status-file',$statusFile,'--account-file',$activeAccount,
  '--account-secondary-file',$secondary,'--shadow-root',$shadowRoot)
 if(-not $NoBrowser){$uiArgs+=@('--open-browser')}
 $script:stage='START_CLASSIC_UI'
 $uiP=Spawn $py.exe $uiArgs 'classic-dashboard'
 $ready=$false
 for($i=0;$i -lt 50;$i++){
  if(LocalUiAlive){$ready=$true;break}
  if($uiP.HasExited){break}
  Start-Sleep -Milliseconds 250
 }
 Need $ready 'DASHBOARD_NOT_RUNNING'
 Write-Host ('ARK_SHADOW_DASHBOARD=http://127.0.0.1:'+$Port+'/')
 Write-Host 'ARK_SHADOW_UI_MODE=ORIGINAL_CLASSIC_READ_ONLY'
 $script:stage='PUBLISH_AFTER_CLASSIC_UI'
 $steps.excel='WAITING';$steps.marketSpeed='WAITING'
 Publish 'STARTING' 'Opening MarketSpeed II and original Excel RSS books'
 $script:stage='OPEN_MARKETSPEED'
 if($SkipMarketSpeed){$steps.marketSpeed='SKIPPED'}
 elseif(@(Get-Process MarketSpeed2 -ErrorAction SilentlyContinue).Count -gt 0){$steps.marketSpeed='PROCESS_OBSERVED'}
 else{
  $shortcut=FindMarketSpeed
  if($shortcut){Start-Process -FilePath $shortcut -ErrorAction Stop;$steps.marketSpeed='START_REQUESTED'}
  else{$steps.marketSpeed='MANUAL_OPEN_REQUIRED'}
 }
 Write-Host 'ARK_SHADOW_MARKETSPEED_LOGIN=MANUAL_IF_PROMPTED'
 $script:stage='OPEN_VERIFY_EXCEL_BOOKS'
 $state=EnsureBooks $account $market
 if($state -cne 'READY'){
  $steps.excel='BLOCKED';$steps.shadow='BLOCKED'
  Publish 'BLOCKED' ('EXCEL_'+$state+'; check Excel identity and close unrelated books')
  Write-Host ('ARK_SHADOW_EXCEL_IDENTITY='+$state)
  exit 2
 }
 $script:stage='PUBLISH_EXCEL_BOOKS_READY'
 $steps.excel='READY';$steps.account='WAITING'
 Publish 'UI_READY' 'Both original RSS workbooks verified'
 if(-not $requested){
  $script:stage='START_ACCOUNT_OBSERVER'
  StartObserver $account $activeAccount
  $steps.shadow='NOT_CONFIGURED'
  Publish 'UI_READY' 'Original Shadow requires current dated master, reviewed security evidence and pinned private config'
  exit 0
 }
 $pinned=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\frozen-p1-replay\runtime-py312-sklearn180\Scripts\python.exe'
 if(-not (Test-Path -LiteralPath $pinned -PathType Leaf)){
  StartObserver $account $activeAccount
  $steps.shadow='BLOCKED';Publish 'BLOCKED' 'PINNED_PY312_RUNTIME_MISSING'
  exit 2
 }
 Need (Test-Path -LiteralPath $runner -PathType Leaf) 'ORIGINAL_SHADOW_RUNNER_MISSING'
 if($PreparedConfigFile){
  $script:stage='ORIGINAL_SHADOW_PREFLIGHT'
  $steps.shadow='PREFLIGHT'
  Publish 'PREPARING' 'Validating original Shadow frozen model, source and previous context'
  if(-not (Preflight $PreparedConfigFile $pinned)){
   StartObserver $account $activeAccount
   $steps.shadow='BLOCKED'
   Publish 'BLOCKED' 'ORIGINAL_SHADOW_PREFLIGHT_FAILED_NO_SHADOW_STARTED'
   exit 2
  }
  $cmd=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,
   '-ConfigFile',$PreparedConfigFile,'-PythonExecutable',$pinned,'-AccountWorkbookPath',$account)
  $p=Spawn 'powershell.exe' $cmd 'shadow-controller'
  $steps.account='ORIGINAL_CONTROLLER_OBSERVER';$steps.shadow='START_REQUESTED'
  Publish 'SHADOW_START_REQUESTED' 'Original P1/H235/Capital/EXIT Shadow controller started; no broker orders'
  Write-Host ('ARK_SHADOW_CONTROLLER_PID='+$p.Id)
  exit 0
 }
 Need (Test-Path -LiteralPath $prepare -PathType Leaf) 'ORIGINAL_INPUT_PREPARER_MISSING'
 # Only reuse the pre-existing 47 symbol archive; never silently recapture
 # thousands of histories or manufacture corporate-action review evidence.
 $evidence=CheckPath $SecurityEvidenceFile 'SECURITY_EVIDENCE' $false
 $docs=CheckPath $EvidenceDocumentsDir 'EVIDENCE_DOCUMENTS' $true
 $archive=CheckPath $PreviousCaptureDir 'PREVIOUS_CAPTURE' $true
 $out=Join-Path $PrivateRoot ('prepared-sources-'+$session)
 [void][IO.Directory]::CreateDirectory($out)
 $script:stage='ORIGINAL_INPUT_PREPARE'
 $command=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$prepare,
  '-ConfigFile',$BootstrapTemplateFile,'-SecurityEvidence',$evidence,
  '-EvidenceDocuments',$docs,'-PreviousCaptureDir',$archive,
  '-OutputRoot',$out,'-PythonExecutable',$pinned,'-AccountWorkbookPath',$account,'-StartShadow')
 $p=Spawn 'powershell.exe' $command 'original-input-prepare'
 $steps.account='AWAITING_ORIGINAL_CONTROLLER';$steps.shadow='PREPARING'
 Publish 'SHADOW_PREPARING' 'Original source/evidence preflight and Shadow requested; not yet live-verified'
 Write-Host ('ARK_SHADOW_PREPARATION_PID='+$p.Id)
 exit 0
}catch{
 $message=$_.Exception.Message
 if($message -notmatch '^ARK_SHADOW_[A-Z0-9_]+$'){$message='ARK_SHADOW_SOURCE_OR_RUNTIME_ERROR'}
 $steps.shadow='BLOCKED'
 Write-Host ('ARK_SHADOW_FAILURE_STAGE='+$script:stage)
 Write-Host ('ARK_SHADOW_FAILURE_KIND='+$_.Exception.GetType().Name)
 Write-Host ('ARK_SHADOW_FAILURE_HRESULT='+$_.Exception.HResult)
 try{Publish 'BLOCKED' $message}catch{}
 Write-Host ('ARK_SHADOW_LAUNCH_ERROR='+$message)
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($held){$mutex.ReleaseMutex()}
 $mutex.Dispose()
}
