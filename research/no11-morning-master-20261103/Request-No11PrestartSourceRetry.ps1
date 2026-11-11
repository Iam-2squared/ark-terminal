# Explicit retry of a proven pre-registration source-export failure.
# Stages an isolated corrected bootstrap; never installs over the live runtime.
param(
 [switch]$Start,
 [switch]$IConfirmNoOrdersFillsOrPositions,
 [switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$reason){
 if(-not $ok){throw ('NO11_PRESTART_RETRY_'+$reason)}
}
function Clock {return [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))}
function Quote([string]$value){
 Need (-not [string]::IsNullOrWhiteSpace($value) -and
       -not $value.Contains('"') -and -not $value.Contains([char]13) -and
       -not $value.Contains([char]10)) 'ARGUMENT_UNSAFE'
 return '"'+$value+'"'
}
function WriteNewJson([string]$file,$value){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 40 -Compress)+[char]10)
 $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function SafeCoreReason([string]$row){
 try{
  $value=$row|ConvertFrom-Json -ErrorAction Stop
  if($null -ne $value){
   $property=$value.PSObject.Properties['reason']
   if($null -ne $property -and $property.Value -is [string] -and
      $property.Value -cmatch '^NO11_[A-Z0-9_]+$'){return [string]$property.Value}
  }
 }catch{}
 return ''
}
function InvokeCore([string]$python,[string]$tool,[string[]]$parts){
 $rows=@(& $python -B -X utf8 $tool @parts)
 $code=$LASTEXITCODE
 if($code -ne 0){
  foreach($row in $rows){
   $reason=SafeCoreReason ([string]$row)
   if($reason){throw $reason}
   if([string]$row -cmatch '^NO11_[A-Z0-9_=|]+$'){Write-Host $row}
  }
  throw 'NO11_PRESTART_RETRY_CORE_REJECTED'
 }
 Need ($rows.Count -eq 1) 'CORE_OUTPUT_NOT_UNIQUE'
 return ($rows[0]|ConvertFrom-Json)
}
function ProcessSnapshot {
 $all=@(Get-CimInstance Win32_Process -ErrorAction Stop)
 Need ($all.Count -gt 0) 'PROCESS_ENUMERATION_EMPTY'
 return @($all|Where-Object{
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw|node)([.]exe)?$'
 })
}
function ProcessProof([string]$day){
 # Win32_Process.CommandLine may briefly be null for a new/exiting process.
 # Resample the entire process set without waiving unknown live processes.
 $candidates=@();$unreadable=@()
 for($attempt=0;$attempt -lt 4;$attempt++){
  $candidates=@(ProcessSnapshot)
  $unreadable=@($candidates|Where-Object{[string]::IsNullOrWhiteSpace([string]$_.CommandLine)})
  if($unreadable.Count -eq 0){break}
  if($attempt -lt 3){Start-Sleep -Milliseconds 180}
 }
 Need ($unreadable.Count -eq 0) 'PROCESS_COMMAND_LINE_UNAVAILABLE'
 $pattern='Run-No11ReceivedSession|no11_received_|no11_broker_|no11_prestart_source_retry|prestart-retry[\\/]|prestart-controller|prestart-operator|Observe-No11AccountReadOnly|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder|Run-No11Preopen|Start-No11Preopen|PreopenStandby|launcher_automatic_bridge|no11_nightly|Run-No11.*Nightly|no11_daily_cycle|Run-No11.*Daily|Start-No11Afternoon|Retry-No11|Resume-No11SameSession|Request-No11PrestartSourceRetry'
 $workers=@($candidates|Where-Object{[string]$_.CommandLine -match $pattern})
 $gui=@($candidates|Where-Object{[string]$_.CommandLine -match 'Start-No11OneClick[.]ps1'})
 Need ($workers.Count -eq 0) 'ARK_WORKERS_STILL_RUNNING'
 Need ($gui.Count -eq 0) 'CLOSE_WHITE_ONECLICK_FIRST'
 return [ordered]@{
  schemaId='ARK_NO11_PRESTART_RETRY_PROCESS_V1';sessionDate=$day
  observedAtJst=(Clock).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  enumerationSucceeded=$true;matchingWorkers=0;unreadableWorkers=0
  oneClickProcesses=0;checkerPid=$PID;orderTransmission=$false
 }
}
function IsNumericZero($value){
 return ($null -ne $value -and $value -is [ValueType] -and
         $value -isnot [bool] -and [double]$value -eq 0)
}
function TestGeneral($cell){
 $normal=$cell.NumberFormat;$local=$cell.NumberFormatLocal
 if($normal -isnot [string] -or $local -isnot [string]){return $false}
 $japanese=-join [char[]]@(0x0047,0x002F,0x6A19,0x6E96)
 return (($normal -ceq 'General' -and ($local -ceq 'General' -or $local -ceq $japanese)) -or
         ($normal -ceq $japanese -and $local -ceq $japanese))
}
function WriteNativeReasons([string[]]$paths){
 foreach($path in $paths){
  if(Test-Path -LiteralPath $path -PathType Leaf){
   try{
    foreach($line in @(Get-Content -LiteralPath $path -Tail 60 -ErrorAction Stop)){
     if([string]$line -cmatch '^NO11_[A-Z0-9_=|]+$'){Write-Host $line}
    }
   }catch{}
  }
 }
}
function TransportProof($plan,$settings){
 $transport=$plan.transport
 Need ($transport.guardCell -ceq 'BD1' -and $transport.triggerCell -ceq 'BD2' -and
       $transport.sessionCell -ceq 'BD3' -and $transport.formulaCell -ceq 'BD4' -and
       $transport.worksheetName -ceq 'ARK_ORDER_IDS_READONLY' -and
       $transport.guardValue -ceq 'ARK_NO11_SEND_ONCE') 'CONTROL_LAYOUT_CHANGED'
 $excel=$null
 try{
  $processes=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
  Need ($processes.Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
  $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  if(-not ('No11PrestartRetryPid' -as [type])){
   Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class No11PrestartRetryPid {
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window,out uint pid);
}
'@ -ErrorAction Stop
  }
  [uint32]$windowPid=0
  [void][No11PrestartRetryPid]::GetWindowThreadProcessId([IntPtr]([long]$excel.Hwnd),[ref]$windowPid)
  $started=$processes[0].StartTime.ToUniversalTime()
  $expected=[DateTimeOffset]::Parse([string]$transport.expectedExcelStartedAt,[Globalization.CultureInfo]::InvariantCulture)
  Need ($windowPid -eq [uint32]$processes[0].Id -and
        $windowPid -eq [uint32]$transport.expectedExcelPid -and
        [long]$excel.Hwnd -eq [long]$transport.expectedExcelHwnd -and
        $started.Ticks -eq $expected.UtcDateTime.Ticks) 'EXCEL_SESSION_CHANGED'
  Need ($excel.Ready -eq $true -and [int]$excel.CalculationState -eq 0 -and
        [int]$excel.Calculation -eq -4105) 'EXCEL_NOT_READY'
  $roles=@(
   @{Path=[string]$settings.accountWorkbookPath;Sheet='ARK_ACCOUNT_READONLY'},
   @{Path=[string]$settings.marketWorkbookPath;Sheet='ARK_MARKET_READONLY'},
   @{Path=[string]$settings.orderIdWorkbookPath;Sheet='ARK_ORDER_IDS_READONLY'}
  )
  Need ($excel.Workbooks.Count -eq 3) 'ORIGINAL_THREE_BOOKS_REQUIRED'
  $seen=@{};$orderBook=$null
  foreach($book in $excel.Workbooks){
   $full=[IO.Path]::GetFullPath([string]$book.FullName)
   $matches=@($roles|Where-Object{$full.Equals([IO.Path]::GetFullPath($_.Path),[StringComparison]::OrdinalIgnoreCase)})
   Need ($matches.Count -eq 1 -and -not $seen.ContainsKey($matches[0].Sheet) -and
         $book.Worksheets.Count -eq 1 -and
         [string]$book.Worksheets.Item(1).Name -ceq $matches[0].Sheet) 'REGISTERED_BOOK_IDENTITY'
   $seen[$matches[0].Sheet]=$true
   if($matches[0].Sheet -ceq 'ARK_ORDER_IDS_READONLY'){$orderBook=$book}
  }
  Need ($seen.Count -eq 3 -and $null -ne $orderBook -and -not $orderBook.ReadOnly) 'ORDER_BOOK_UNAVAILABLE'
  Need ([IO.Path]::GetFullPath([string]$orderBook.FullName).Equals(
        [IO.Path]::GetFullPath([string]$transport.workbookPath),[StringComparison]::OrdinalIgnoreCase)) 'TRANSPORT_BOOK_CHANGED'
  $configured=@($transport.expectedOpenWorkbooks|ForEach-Object{[IO.Path]::GetFullPath([string]$_).ToLowerInvariant()}|Sort-Object)
  $registered=@($roles|ForEach-Object{[IO.Path]::GetFullPath($_.Path).ToLowerInvariant()}|Sort-Object)
  Need ($configured.Count -eq 3 -and (($configured -join '|') -ceq ($registered -join '|'))) 'TRANSPORT_BOOK_SET_CHANGED'
  foreach($addonPath in $transport.expectedAddInPaths){
   $addons=@($excel.AddIns|Where-Object{[IO.Path]::GetFullPath([string]$_.FullName).Equals([IO.Path]::GetFullPath([string]$addonPath),[StringComparison]::OrdinalIgnoreCase)})
   Need ($addons.Count -eq 1 -and $addons[0].Installed -eq $true) 'RSS_ADDIN_NOT_CONNECTED'
  }
  $sheet=$orderBook.Worksheets.Item('ARK_ORDER_IDS_READONLY')
  Need (-not $sheet.ProtectContents) 'ORDER_SHEET_PROTECTED'
  $guard=$sheet.Range('BD1');$trigger=$sheet.Range('BD2');$session=$sheet.Range('BD3');$formula=$sheet.Range('BD4')
  Need (-not $guard.HasFormula -and [string]$guard.Value2 -ceq 'ARK_NO11_SEND_ONCE' -and
        -not $session.HasFormula -and [string]$session.Value2 -ceq [string]$transport.rssSessionKey) 'EXISTING_CONTROL_SESSION_CHANGED'
  Need (-not $trigger.HasFormula -and -not $trigger.MergeCells -and (IsNumericZero $trigger.Value2)) 'ORDER_TRIGGER_NOT_IDLE'
  Need (-not $formula.HasFormula -and -not $formula.HasArray -and -not $formula.MergeCells -and
        [string]::IsNullOrEmpty([string]$formula.Value2)) 'PRIOR_ORDER_FORMULA_PRESENT'
  Need (TestGeneral $formula) 'DEDICATED_ORDER_FORMAT_CHANGED'
  return [ordered]@{
   schemaId='ARK_NO11_PRESTART_RETRY_TRANSPORT_V1';sessionDate=[string]$plan.sessionDate
   observedAtJst=(Clock).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
   excelPid=[int]$windowPid;excelStartedAtUtc=$started.ToString('o');excelHwnd=[long]$excel.Hwnd
   rssSessionKey=[string]$transport.rssSessionKey;registeredThreeBooksVerified=$true
   controlCellsVerified=$true;triggerZero=$true;orderTransmission=$false
  }
 }finally{
  if($null -ne $excel -and [Runtime.InteropServices.Marshal]::IsComObject($excel)){
   [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
  }
 }
}
if($OfflineSelfTest){
 Need (-not $Start -and -not $IConfirmNoOrdersFillsOrPositions) 'SELFTEST_FLAGS'
 Need ((Quote 'C:\Space Dir\test.ps1') -ceq '"C:\Space Dir\test.ps1"') 'QUOTE_TEST'
 foreach($bad in @('',"x`ny",'x"y')){
  $blocked=$false;try{[void](Quote $bad)}catch{$blocked=$true}
  Need $blocked 'QUOTE_REJECTION_TEST'
 }
 Need ((IsNumericZero 0) -and (IsNumericZero ([double]0)) -and
       -not (IsNumericZero $null) -and -not (IsNumericZero $false) -and
       -not (IsNumericZero '0') -and -not (IsNumericZero 1)) 'ZERO_TYPE_TEST'
 $ja=-join [char[]]@(0x0047,0x002F,0x6A19,0x6E96)
 foreach($pair in @(@('General','General'),@('General',$ja),@($ja,$ja))){
  Need (TestGeneral ([pscustomobject]@{NumberFormat=$pair[0];NumberFormatLocal=$pair[1]})) 'GENERAL_VALID_TEST'
 }
 foreach($pair in @(@($ja,'General'),@('@','@'),@('0.00','0.00'),@($null,'General'),@('General',$true))){
  Need (-not (TestGeneral ([pscustomobject]@{NumberFormat=$pair[0];NumberFormatLocal=$pair[1]}))) 'GENERAL_INVALID_TEST'
 }
 Need ((SafeCoreReason '{"status":"BLOCKED","reason":"NO11_PRESTART_RETRY_EXAMPLE"}') -ceq
       'NO11_PRESTART_RETRY_EXAMPLE') 'CORE_JSON_REASON_TEST'
 foreach($row in @('{"reason":"C:\\private\\account"}','{"status":"BLOCKED"}','not json','{"reason":42}')){
  Need ([string]::IsNullOrEmpty((SafeCoreReason $row))) 'CORE_JSON_REDACTION_TEST'
 }
 $temporary=Join-Path ([IO.Path]::GetTempPath()) ('ark-prestart-test-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($temporary)
 try{
  $file=Join-Path $temporary 'claim.json'
  WriteNewJson $file @{orderTransmission=$false;test='durable'}
  $before=[IO.File]::ReadAllBytes($file)
  $blocked=$false;try{WriteNewJson $file @{orderTransmission=$true}}catch{$blocked=$true}
  Need ($blocked -and [Convert]::ToBase64String($before) -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($file))) 'NO_OVERWRITE_TEST'
 }finally{[IO.Directory]::Delete($temporary,$true)}
 # Mock the actual ProcessProof path: no CIM, Excel or broker is touched.
 $script:proofMode='gone';$script:proofReads=0
 $script:proofGood=[pscustomobject]@{ProcessId=($PID+100000);Name='powershell.exe';CommandLine='powershell.exe benign'}
 $script:proofUnknown=[pscustomobject]@{ProcessId=($PID+100001);Name='node.exe';CommandLine=$null}
 $script:proofResolved=[pscustomobject]@{ProcessId=($PID+100001);Name='node.exe';CommandLine='node.exe benign.js'}
 $script:proofWorker=[pscustomobject]@{ProcessId=($PID+100002);Name='python.exe';CommandLine='python.exe no11_received_session_controller.py'}
 function ProcessSnapshot {
  $script:proofReads++
  if($script:proofMode -eq 'persistent'){return @($script:proofGood,$script:proofUnknown)}
  if($script:proofMode -eq 'worker'){return @($script:proofGood,$script:proofWorker)}
  if($script:proofReads -eq 1){return @($script:proofGood,$script:proofUnknown)}
  if($script:proofMode -eq 'resolved'){return @($script:proofGood,$script:proofResolved)}
  return @($script:proofGood)
 }
 foreach($mode in @('gone','resolved')){
  $script:proofMode=$mode;$script:proofReads=0
  $proof=ProcessProof '2026-11-11'
  Need ($script:proofReads -eq 2 -and $proof.unreadableWorkers -eq 0 -and $proof.matchingWorkers -eq 0) 'TRANSIENT_PROCESS_RECHECK_TEST'
 }
 $script:proofMode='persistent';$script:proofReads=0
 $blocked=$false
 try{[void](ProcessProof '2026-11-11')}catch{$blocked=($_.Exception.Message -ceq 'NO11_PRESTART_RETRY_PROCESS_COMMAND_LINE_UNAVAILABLE')}
 Need ($blocked -and $script:proofReads -eq 4) 'PERSISTENT_UNREADABLE_REJECTION_TEST'
 $script:proofMode='worker';$script:proofReads=0
 $blocked=$false
 try{[void](ProcessProof '2026-11-11')}catch{$blocked=($_.Exception.Message -ceq 'NO11_PRESTART_RETRY_ARK_WORKERS_STILL_RUNNING')}
 Need $blocked 'ARK_WORKER_REJECTION_TEST'
 Write-Host 'NO11_PRESTART_RETRY_PROCESS_RACE_TEST=PASS'
 Write-Host 'NO11_PRESTART_RETRY_WINDOWS_SELFTEST=PASS'
 Write-Host 'EXCEL_ACCESSED=False'
 Write-Host 'TRADE_REQUESTED=False'
 exit 0
}
$guard=$null;$retryLock=$null;$startedProcess=$null
try{
 $store=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher'
 $binding=Get-Content -LiteralPath (Join-Path $store 'automatic-inputs.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $python=[string]$binding.python
 Need ([IO.Path]::IsPathRooted($python) -and (Test-Path -LiteralPath $python -PathType Leaf)) 'PYTHON_MISSING'
 $tool=Join-Path $PSScriptRoot 'no11_prestart_source_retry.py'
 Need (Test-Path -LiteralPath $tool -PathType Leaf) 'CORE_MISSING'
 $plan=InvokeCore $python $tool @('audit','--store',$store)
 if(-not $Start){
  Write-Host 'NO11_PRESTART_RETRY=AUDIT_READY_NOT_STARTED'
  Write-Host ('SESSION='+[string]$plan.sessionDate)
  Write-Host 'TRADE_REQUESTED=False'
  exit 0
 }
 Need $IConfirmNoOrdersFillsOrPositions.IsPresent 'OPERATOR_BROKER_CONFIRMATION_REQUIRED'
 $now=Clock;$day=$now.ToString('yyyy-MM-dd')
 Need ($now.DayOfWeek -notin @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday) -and
       $day -ceq [string]$plan.sessionDate -and
       $now.ToString('HH:mm:ss') -ge '09:00:00' -and $now.ToString('HH:mm:ss') -lt '15:20:00') 'CURRENT_ENTRY_WINDOW_REQUIRED'
 $guard=[IO.File]::Open((Join-Path $store 'unified-refresh-install.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $retryLock=[IO.File]::Open((Join-Path $store ('PRESTART-RETRY-'+$day+'.lock')),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 [void](ProcessProof $day)
 $settings=Get-Content -LiteralPath (Join-Path $store 'settings.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $retryRoot=Join-Path $store 'prestart-retry'
 [void][IO.Directory]::CreateDirectory($retryRoot)
 $package=Join-Path $retryRoot ($day+'-'+[guid]::NewGuid().ToString('N'))
 $manifest=InvokeCore $python $tool @('stage','--store',$store,'--package-dir',$package)
 $plan=$manifest.plan
 $observation=Join-Path $package 'broker-observation.json'
 $stop=Join-Path $package 'broker-observer.stop'
 & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ([string]$plan.observerFile) -WorkbookPath ([string]$plan.accountWorkbookPath) -OrderIdWorkbookPath ([string]$plan.orderIdWorkbookPath) -OutputFile $observation -StopFile $stop -Samples 1 | Out-Null
 Need ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $observation -PathType Leaf)) 'FRESH_BROKER_OBSERVATION_FAILED'
 $transportFile=Join-Path $package 'transport-proof.json'
 WriteNewJson $transportFile (TransportProof $plan $settings)
 $processFile=Join-Path $package 'process-proof.json'
 WriteNewJson $processFile (ProcessProof $day)
 $claimed=InvokeCore $python $tool @('claim','--manifest',[string]$manifest.manifestFile,'--observation',$observation,'--process-proof',$processFile,'--transport-proof',$transportFile,'--operator-approved')
 Need (-not [string]::IsNullOrWhiteSpace([string]$claimed.claimFile)) 'CLAIM_NOT_PERSISTED'
 $log=Join-Path $package 'native-trade.log';$err=Join-Path $package 'native-trade.err'
 $launchParts=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
  (Quote ([string]$manifest.operatorScript)),'-ConfigFile',(Quote ([string]$plan.bootstrapFile)),
  '-AccountWorkbookPath',(Quote ([string]$plan.accountWorkbookPath)),
  '-OrderIdWorkbookPath',(Quote ([string]$plan.orderIdWorkbookPath)),
  '-PythonExecutable',(Quote $python),'-IApproveFullArkLiveOrdersForThisSession')
 $startedProcess=Start-Process -FilePath 'powershell.exe' -ArgumentList ($launchParts -join ' ') -WorkingDirectory $package -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
 Need ($null -ne $startedProcess -and $startedProcess.Id -gt 0) 'NATIVE_START_UNCONFIRMED'
 WriteNewJson (Join-Path $package 'launch-observation.json') @{
  schemaId='ARK_NO11_PRESTART_RETRY_LAUNCH_OBSERVATION_V1';sessionDate=$day
  processId=$startedProcess.Id;requestedAtJst=(Clock).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
  claimFile=[string]$claimed.claimFile;originalMarkersPreserved=$true;isExecutionConfirmation=$false
 }
 Start-Sleep -Seconds 2
 $startedProcess.Refresh()
 if($startedProcess.HasExited){
  Write-Host ('NO11_PRESTART_RETRY_NATIVE_EXIT_CODE='+$startedProcess.ExitCode)
  WriteNativeReasons @($log,$err)
  throw 'NO11_PRESTART_RETRY_NATIVE_PROCESS_EXITED'
 }
 Write-Host 'NO11_PRESTART_RETRY=NATIVE_REQUESTED_ONCE'
 Write-Host ('NATIVE_PID='+$startedProcess.Id)
 Write-Host ('NATIVE_LOG='+$log)
 Write-Host ('NATIVE_ERROR_LOG='+$err)
 Write-Host 'ORIGINAL_RUNTIME_AND_MARKERS_PRESERVED=True'
 Write-Host 'REQUEST_IS_NOT_ORDER_OR_FILL_CONFIRMATION=True'
 $ui=Join-Path ([string]$plan.engine) 'windows\Start-No11LiveUiReadOnly.ps1'
 if(Test-Path -LiteralPath $ui -PathType Leaf){
  try{
   & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ui -ConfigFile ([string]$plan.bootstrapFile) | Out-Null
   Write-Host ('READ_ONLY_APP_EXIT_CODE='+$LASTEXITCODE)
  }catch{Write-Host 'READ_ONLY_APP=CHECK_NATIVE_LOG'}
 }
 exit 0
}catch{
 if($null -ne $startedProcess){Write-Host ('NATIVE_ALREADY_REQUESTED_PID='+$startedProcess.Id)}
 $reason=$_.Exception.Message
 if($reason -cnotmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_PRESTART_RETRY_LOCAL_OR_COM_CHECK_FAILED'}
 Write-Host ('NO11_PRESTART_RETRY=BLOCKED|'+$reason)
 Write-Host 'RETRY_CLAIM_IF_PRESENT_MUST_BE_PRESERVED=True'
 exit 2
}finally{
 if($null -ne $retryLock){$retryLock.Dispose()}
 if($null -ne $guard){$guard.Dispose()}
}
