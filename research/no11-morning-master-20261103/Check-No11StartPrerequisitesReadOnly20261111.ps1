# Consolidated current-session diagnostic. ASCII source for Windows PS 5.1.
# Reads existing files and Excel properties only. Does not install, repair,
# refresh data, initialize controls, authorize orders, start or stop a process.
param([switch]$OfflineSelfTest)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need-No11Today([bool]$ok,[string]$code){
 if(-not $ok){throw ('NO11_TODAY_'+$code)}
}
function Hash-No11Today([byte[]]$raw){
 $h=[Security.Cryptography.SHA256]::Create()
 try{return ([BitConverter]::ToString($h.ComputeHash($raw))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
}
function File-No11Today([string]$path){
 Need-No11Today ([IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType Leaf)) 'FILE_NOT_AVAILABLE'
 $full=[IO.Path]::GetFullPath($path)
 $cur=$full
 while(-not [string]::IsNullOrWhiteSpace($cur)){
  $item=Get-Item -LiteralPath $cur -Force
  Need-No11Today (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'REPARSE_SOURCE'
  $next=Split-Path -Parent $cur
  if($next -ceq $cur){break};$cur=$next
 }
 return $full
}
function Json-No11Today([string]$path){
 $file=File-No11Today $path
 Need-No11Today ((Get-Item -LiteralPath $file).Length -le 25000000) 'JSON_TOO_LARGE'
 return (Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json)
}
function Pin-No11Today([string]$path,[string]$expected){
 Need-No11Today ($expected -cmatch '^[a-f0-9]{64}$') 'SHA256_PIN_FORMAT'
 $file=File-No11Today $path
 Need-No11Today ((Hash-No11Today ([IO.File]::ReadAllBytes($file))) -ceq $expected) 'SOURCE_HASH_CHANGED'
}
function General-No11Today($cell){
 $a=$cell.NumberFormat;$b=$cell.NumberFormatLocal
 if($a -isnot [string] -or $b -isnot [string]){return $false}
 $ja=-join [char[]]@(0x47,0x2f,0x6a19,0x6e96)
 return (($a -ceq 'General' -and ($b -ceq 'General' -or $b -ceq $ja)) -or ($a -ceq $ja -and $b -ceq $ja))
}
function Controls-No11Today($guard,$trigger,$session,[string]$key){
 Need-No11Today ($key -cmatch '^[a-f0-9]{64}$') 'CURRENT_SESSION_KEY_FORMAT'
 Need-No11Today (-not $guard.HasFormula -and -not $trigger.HasFormula -and -not $session.HasFormula) 'CONTROL_HAS_FORMULA'
 $t=$trigger.Value2
 $zero=($t -is [ValueType] -and $t -isnot [bool] -and [double]$t -eq 0)
 $empty=($null -eq $t -or ($t -is [string] -and $t -ceq ''))
 Need-No11Today ($zero -or $empty) 'TRIGGER_NOT_ZERO_OR_EMPTY'
 $g=[string]$guard.Value2;$s=[string]$session.Value2
 if($g -ceq 'DISABLED' -and $s -ceq 'UNCONFIGURED_RSS_SESSION' -and $zero){return 'EXACT_INERT_TEMPLATE'}
 Need-No11Today ([string]::IsNullOrWhiteSpace($g) -or $g -ceq 'ARK_NO11_SEND_ONCE') 'UNKNOWN_GUARD'
 Need-No11Today ([string]::IsNullOrWhiteSpace($s) -or $s -ceq $key) 'DIFFERENT_OR_UNKNOWN_SESSION'
 if($g -ceq 'ARK_NO11_SEND_ONCE' -and $s -ceq $key){return 'CURRENT_EXCEL_SESSION'}
 return 'EMPTY_OR_CURRENT_PARTIAL_SESSION'
}
function Scope-No11Today($pointer,$hand,[string]$day){
 Need-No11Today ($pointer.schemaId -ceq 'ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1' -and
  $pointer.sessionDate -ceq $day -and $pointer.orderTransmission -eq $false -and
  $pointer.productionReady -eq $false -and $pointer.humanReviewClaimed -eq $false) 'TODAY_POINTER_CONTRACT'
 Need-No11Today ($hand.schemaId -ceq 'ARK_NO11_MORNING_MASTER_HANDOFF_V1' -and
  $hand.sessionDate -ceq $day -and $hand.previousSession -ceq $pointer.previousSession -and
  $hand.orderTransmission -eq $false -and $hand.productionReady -eq $false -and
  $hand.reviewStatus -ceq 'NOT_REVIEWED' -and $hand.datedMasterCreated -eq $false) 'TODAY_HANDOFF_CONTRACT'
 $previous=[datetime]::ParseExact([string]$pointer.previousSession,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
 $target=[datetime]::ParseExact($day,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
 Need-No11Today ($previous -lt $target) 'SOURCE_DAY_NOT_BEFORE_TARGET'
 $symbols=@($hand.selectedSymbols)
 Need-No11Today ($symbols.Count -ge 1 -and $symbols.Count -le 47 -and
  $symbols.Count -eq [int]$pointer.selectedCount -and
  ($symbols -join '|') -ceq (@($pointer.selectedSymbols) -join '|') -and
  @($symbols|Sort-Object -Unique).Count -eq $symbols.Count) 'HANDOFF_SYMBOL_SCOPE'
 foreach($s in $symbols){Need-No11Today ($s -is [string] -and $s -cmatch '^[0-9A-Z]{4}[.]T$') 'HANDOFF_SYMBOL_FORMAT'}
 return [int]$symbols.Count
}
function Parse-No11Today([string]$path){
 $tokens=$null;$errors=$null
 [void][Management.Automation.Language.Parser]::ParseFile((File-No11Today $path),[ref]$tokens,[ref]$errors)
 Need-No11Today ($errors.Count -eq 0) 'INSTALLED_POWERSHELL_PARSE'
}
function Test-No11TodayOffline {
 $script:TodayTests=0
 function Check([bool]$ok){Need-No11Today $ok 'SELFTEST';$script:TodayTests++}
 function MustFail([scriptblock]$body){$failed=$false;try{& $body|Out-Null}catch{$failed=$true};Check $failed}
 $key='a'*64
 $g=[pscustomobject]@{Value2='DISABLED';HasFormula=$false}
 $t=[pscustomobject]@{Value2=[double]0;HasFormula=$false}
 $s=[pscustomobject]@{Value2='UNCONFIGURED_RSS_SESSION';HasFormula=$false}
 Check ((Controls-No11Today $g $t $s $key) -ceq 'EXACT_INERT_TEMPLATE')
 $g.Value2='12345678';$s.Value2='x'*24
 MustFail {Controls-No11Today $g $t $s $key}
 $g.Value2='ARK_NO11_SEND_ONCE';$s.Value2=$key
 Check ((Controls-No11Today $g $t $s $key) -ceq 'CURRENT_EXCEL_SESSION')
 $s.Value2='b'*64;MustFail {Controls-No11Today $g $t $s $key}
 $g.Value2='';$s.Value2=''
 Check ((Controls-No11Today $g $t $s $key) -ceq 'EMPTY_OR_CURRENT_PARTIAL_SESSION')
 $t.Value2=[double]1;MustFail {Controls-No11Today $g $t $s $key}
 $t.Value2=[double]0;$g.HasFormula=$true;MustFail {Controls-No11Today $g $t $s $key};$g.HasFormula=$false
 $ja=-join [char[]]@(0x47,0x2f,0x6a19,0x6e96)
 foreach($pair in @(@('General','General'),@('General',$ja),@($ja,$ja))){Check (General-No11Today ([pscustomobject]@{NumberFormat=$pair[0];NumberFormatLocal=$pair[1]}))}
 foreach($pair in @(@('@','@'),@('0.00','0.00'),@($ja,'General'))){Check (-not (General-No11Today ([pscustomobject]@{NumberFormat=$pair[0];NumberFormatLocal=$pair[1]})))}
 $p=[pscustomobject]@{schemaId='ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1';sessionDate='2026-11-11';previousSession='2026-11-10';selectedSymbols=@('7203.T');selectedCount=1;orderTransmission=$false;productionReady=$false;humanReviewClaimed=$false}
 $h=[pscustomobject]@{schemaId='ARK_NO11_MORNING_MASTER_HANDOFF_V1';sessionDate='2026-11-11';previousSession='2026-11-10';selectedSymbols=@('7203.T');orderTransmission=$false;productionReady=$false;reviewStatus='NOT_REVIEWED';datedMasterCreated=$false}
 Check ((Scope-No11Today $p $h '2026-11-11') -eq 1)
 MustFail {Scope-No11Today $p $h '2026-11-12'}
 $h.selectedSymbols=@('6501.T');MustFail {Scope-No11Today $p $h '2026-11-11'};$h.selectedSymbols=@('7203.T')
 $h.orderTransmission=$true;MustFail {Scope-No11Today $p $h '2026-11-11'};$h.orderTransmission=$false
 Check ((Hash-No11Today (New-Object byte[] 0)) -ceq 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
 Write-Host ('NO11_TODAY_SELFTEST=PASS|CASES='+$script:TodayTests)
 Write-Host 'EXCEL_ACCESSED=False'
}
if($OfflineSelfTest){Test-No11TodayOffline;Write-Host 'ORDER_TRANSMISSION_BY_THIS_CHECK=False';exit 0}
$stage='CONFIG';$excel=$null
try{
 $now=[DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
 $day=$now.ToString('yyyy-MM-dd')
 Write-Host ('NO11_TODAY_CHECK_TIME='+$now.ToString('yyyy-MM-dd HH:mm:ss')+' JST')
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $cfg=Json-No11Today (Join-Path $store 'settings.json')
 $b=Json-No11Today (Join-Path $store 'automatic-inputs.json')
 Need-No11Today ($cfg.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
  $cfg.normalMaxPositions -eq 3 -and $cfg.sameDayApprovalRequired -eq $true -and
  $cfg.automaticOrderAuthorization -eq $false -and $cfg.orderTransmission -eq $false -and
  $b.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -and $b.orderTransmission -eq $false) 'CONFIG_CONTRACT'
 $stage='TODAY_HANDOFF'
 $ptr=Json-No11Today (Join-Path ([string]$b.dailyCycleRoot) ('prepared-days\'+$day+'.json'))
 Pin-No11Today ([string]$ptr.handoff) ([string]$ptr.handoffSha256)
 Need-No11Today ([IO.Path]::GetFileName([string]$ptr.handoff) -ceq ('morning-handoff-'+$ptr.handoffSha256+'.json')) 'HANDOFF_FILENAME_HASH'
 $hand=Json-No11Today ([string]$ptr.handoff)
 $count=Scope-No11Today $ptr $hand $day
 foreach($name in @('chartReceipt','passMask','previousStage')){Pin-No11Today ([string]$hand.spec.$name) ([string]$hand.sourcePins.$name)}
 Pin-No11Today ([string]$hand.publicSourceBasis) ([string]$hand.publicSourceBasisSha256)
 Write-Host ('NO11_TODAY_HANDOFF=PASS|SESSION='+$hand.sessionDate+'|ASOF='+$hand.previousSession+'|ENTRIES='+$count)
 $stage='BOUND_SOURCES'
 foreach($name in @('bridge','automatic','runner','scopeTool','dailyCycleTool','nightlyResumeTool','transportProbe','dataWorkbookRegistration','dataWorkbookResolver')){
  Pin-No11Today ([string]$b.$name) ([string]$b.($name+'Sha256'))
 }
 $journal=Json-No11Today (Join-Path $store 'excel-locale-template-v1.transaction.json')
 Need-No11Today ($journal.kind -ceq 'ARK_NO11_EXCEL_LOCALE_TEMPLATE_INSTALL_V1' -and $journal.phase -ceq 'COMPLETE' -and $journal.orderTransmission -eq $false) 'LOCALE_INSTALL_NOT_COMPLETE'
 $sender=Join-Path ([string]$b.engine) 'windows\Invoke-No11MsiiOrder.ps1'
 $validator=Join-Path ([string]$b.engine) 'tools\no11_msii_transport.mjs'
 foreach($path in @($sender,$validator)){
  $rows=@($journal.sources|Where-Object {([IO.Path]::GetFullPath([string]$_.path)).Equals([IO.Path]::GetFullPath($path),[StringComparison]::OrdinalIgnoreCase)})
  Need-No11Today ($rows.Count -eq 1) 'LOCALE_COMPONENT_NOT_RECORDED'
  Pin-No11Today $path (Hash-No11Today ([Convert]::FromBase64String([string]$rows[0].after)))
 }
 Need-No11Today (([IO.Path]::GetFullPath([string]$b.transportProbe)).Equals([IO.Path]::GetFullPath([string]$journal.probe),[StringComparison]::OrdinalIgnoreCase) -and $b.transportProbeSha256 -ceq $journal.probeSha256) 'LOCALE_PROBE_NOT_ACTIVE'
 foreach($p in @([string]$b.transportProbe,$sender,(Join-Path ([string]$b.engine) 'windows\Start-No11UnifiedLauncher.ps1'),(Join-Path ([string]$b.engine) 'windows\Run-No11ReceivedSessionOperatorLive.ps1'))){Parse-No11Today $p}
 Write-Host 'NO11_TODAY_CODE_PINS_AND_LOCALE_INSTALL=PASS'
 $stage='EXCEL_BOOKS'
 $processes=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need-No11Today ($processes.Count -eq 1) 'EXCEL_NOT_RUNNING_OR_AMBIGUOUS'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need-No11Today ($excel.Visible -eq $true -and $excel.Ready -eq $true -and [int]$excel.CalculationState -eq 0 -and [int]$excel.Calculation -eq -4105) 'EXCEL_NOT_READY_OR_NOT_AUTOMATIC'
 Need-No11Today ($excel.Workbooks.Count -eq 3) 'EXPECTED_THREE_ORIGINAL_BOOKS'
 $reg=Json-No11Today ([string]$b.dataWorkbookRegistration)
 Need-No11Today ($reg.schemaId -ceq 'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1' -and @($reg.books).Count -eq 3 -and $reg.orderTransmission -eq $false) 'BOOK_REGISTRY_CONTRACT'
 $roles=@(@{Role='Account';Field='accountWorkbookPath';Sheet='ARK_ACCOUNT_READONLY'},@{Role='Market';Field='marketWorkbookPath';Sheet='ARK_MARKET_READONLY'},@{Role='OrderIds';Field='orderIdWorkbookPath';Sheet='ARK_ORDER_IDS_READONLY'})
 $books=@{};$paths=@{}
 foreach($r in $roles){
  $path=File-No11Today ([string]$cfg.($r.Field));$paths[$r.Role]=$path
  $record=@($reg.books|Where-Object {$_.role -ceq $r.Role})
  Need-No11Today ($record.Count -eq 1 -and $record[0].sheet -ceq $r.Sheet -and ([IO.Path]::GetFullPath([string]$record[0].path)).Equals($path,[StringComparison]::OrdinalIgnoreCase)) 'BOOK_SETTINGS_REGISTRY_MISMATCH'
  $found=@($excel.Workbooks|Where-Object {([IO.Path]::GetFullPath([string]$_.FullName)).Equals($path,[StringComparison]::OrdinalIgnoreCase)})
  Need-No11Today ($found.Count -eq 1 -and $found[0].Worksheets.Count -eq 1 -and [string]$found[0].Worksheets.Item(1).Name -ceq $r.Sheet -and -not $found[0].Date1904) 'OPEN_BOOK_IDENTITY'
  $books[$r.Role]=$found[0]
 }
 Need-No11Today (([IO.Path]::GetFullPath([string]$hand.orderIdWorkbookPath)).Equals($paths['OrderIds'],[StringComparison]::OrdinalIgnoreCase)) 'HANDOFF_ORDER_BOOK_PATH_CHANGED'
 Write-Host 'NO11_TODAY_THREE_BOOKS_AND_HANDOFF_PATH=PASS'
 $stage='EXCEL_CONTROLS'
 if(-not ('No11TodayAuditNative' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class No11TodayAuditNative {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
}
'@ -ErrorAction Stop
 }
 [uint32]$winPid=0
 [void][No11TodayAuditNative]::GetWindowThreadProcessId([IntPtr]([long]$excel.Hwnd),[ref]$winPid)
 Need-No11Today ($winPid -gt 0 -and $winPid -eq [uint32]$processes[0].Id) 'EXCEL_PROCESS_IDENTITY'
 $started=$processes[0].StartTime.ToUniversalTime().ToString('o')
 $aHash=Hash-No11Today ([Text.Encoding]::UTF8.GetBytes($paths['Account'].ToLowerInvariant()))
 $oHash=Hash-No11Today ([Text.Encoding]::UTF8.GetBytes($paths['OrderIds'].ToLowerInvariant()))
 $identity=(@([string]$winPid,$started,$aHash,$oHash)) -join [string][char]10
 $key=Hash-No11Today ([Text.Encoding]::UTF8.GetBytes($identity))
 $order=$books['OrderIds'];$sheet=$order.Worksheets.Item('ARK_ORDER_IDS_READONLY')
 Need-No11Today (-not $order.ReadOnly -and -not $sheet.ProtectContents) 'ORDER_BOOK_OR_SHEET_NOT_WRITABLE'
 $g=$sheet.Range('BD1');$t=$sheet.Range('BD2');$s=$sheet.Range('BD3');$f=$sheet.Range('BD4')
 $control=Controls-No11Today $g $t $s $key
 Need-No11Today (-not $f.MergeCells -and -not $f.HasArray -and -not $t.MergeCells -and -not $f.HasFormula -and [string]::IsNullOrWhiteSpace([string]$f.Value2)) 'ORDER_CELL_NOT_EMPTY_OR_DEDICATED'
 Need-No11Today (General-No11Today $f) 'ORDER_CELL_FORMAT_NOT_STANDARD'
 Write-Host ('NO11_TODAY_CONTROL_STATE=PASS|'+$control)
 Write-Host 'NO11_TODAY_JAPANESE_OR_ENGLISH_GENERAL=PASS'
 $stage='RSS_ADDINS'
 $addons=@($excel.AddIns|Where-Object {$_.Installed -eq $true -and [IO.Path]::GetFileName([string]$_.FullName) -match '^MarketSpeed2_RSS_(?:(?:32|64)bit[.]xll|VBA[.]xlam)$'}|ForEach-Object {[IO.Path]::GetFullPath([string]$_.FullName)}|Sort-Object -Unique)
 Need-No11Today ($addons.Count -eq 2 -and @($addons|Where-Object {$_ -match '_VBA[.]xlam$'}).Count -eq 1 -and @($addons|Where-Object {$_ -match '_(?:32|64)bit[.]xll$'}).Count -eq 1) 'RSS_ADDINS_NOT_READY'
 Write-Host 'NO11_TODAY_RSS_ADDINS=PASS'
 $stage='EXISTING_RUN'
 $marker=Join-Path $store ('TRADE-'+$day+'.launch.json')
 Need-No11Today (-not (Test-Path -LiteralPath $marker)) 'TODAY_TRADE_REQUEST_EXISTS_REVIEW_NOT_RESTART'
 $boot=Json-No11Today ([string]$cfg.bootstrapConfigFile)
 $private=[string]$boot.privateRoot
 Need-No11Today ([IO.Path]::IsPathRooted($private)) 'BOOTSTRAP_PRIVATE_ROOT'
 Need-No11Today (-not (Test-Path -LiteralPath (Join-Path $private ('received-session-'+$day+'.active.json'))) -and -not (Test-Path -LiteralPath (Join-Path $private 'bootstrap-recovery-required.json'))) 'EXISTING_RUN_OR_RECOVERY_REQUIRES_REVIEW'
 $workers=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object {$_.ProcessId -ne $PID -and $_.Name -match '^(?:powershell|pwsh|python|pythonw|node)(?:[.]exe)?$' -and [string]$_.CommandLine -match 'Run-No11ReceivedSessionOperatorLive[.]ps1|no11_received_session_controller[.]py|Invoke-No11MsiiOrder[.]ps1|Probe-No11Chart50ContinuousReadOnly[.]ps1'})
 Need-No11Today ($workers.Count -eq 0) 'LIVE_WORKER_PRESENT_DO_NOT_RESTART'
 Write-Host 'NO11_TODAY_PRIOR_RUN_CHECK=NO_LOCAL_RUN_FOUND'
 $clock=$now.ToString('HH:mm:ss')
 $phase=if($clock -lt '09:00:00'){'PREOPEN_WAIT_FOR_NORMAL_START'}elseif($clock -le '15:20:00'){'NORMAL_START_TIME_WINDOW'}else{'OUTSIDE_START_TIME_WINDOW'}
 Write-Host ('NO11_TODAY_CLOCK='+$phase)
 Write-Host 'NO11_TODAY_PRECHECK=PASS_READ_ONLY_PREREQUISITES'
 Write-Host 'LIVE_START_AND_ORDER_EXECUTION_VERIFIED=False'
 Write-Host 'TODAY_MARKET_INPUTS_AND_BROKER_RECONCILIATION=NOT_PERFORMED_BY_THIS_CHECK'
}catch{
 $code=[string]$_.Exception.Message
 if($code -cnotmatch '^NO11_TODAY_[A-Z0-9_]+$'){$code='NO11_TODAY_READ_OR_RUNTIME_FAILED'}
 Write-Host ('NO11_TODAY_PRECHECK=BLOCKED|STAGE_'+$stage+'|'+$code)
 exit 2
}finally{
 if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}
 Write-Host 'INSTALLED_SETTINGS_AND_CODE_MODIFIED=False'
 Write-Host 'EXCEL_CELLS_MODIFIED=False'
 Write-Host 'DATA_RECAPTURED=False'
 Write-Host 'TRADE_LAUNCHED_BY_THIS_CHECK=False'
 Write-Host 'ORDER_TRANSMISSION_BY_THIS_CHECK=False'
}
