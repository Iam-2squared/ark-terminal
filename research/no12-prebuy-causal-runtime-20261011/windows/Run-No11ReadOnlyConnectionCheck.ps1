# Finite account/market read-only check; no source ZIP indexing or trading.
param(
 [string]$AccountWorkbookPath,[string]$DailyRun,[string]$OutputRoot,
 [switch]$ConfirmOrderOff,[switch]$MarketOnly,[switch]$OfflineSelfTest
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
function QuoteArgument([string]$value){
 if($value.Contains('"') -or $value.Contains("`r") -or $value.Contains("`n") -or $value.EndsWith('\')){
  throw 'NO11_CONNECTION_UNSAFE_ARGUMENT'
 }
 return '"'+$value+'"'
}
function WriteResult([string]$file,$value){
 $tmp=$file+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
 try{
  [IO.File]::WriteAllText($tmp,($value|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($true))
  if([IO.File]::Exists($file)){
   [IO.File]::Replace($tmp,$file,[System.Management.Automation.Language.NullString]::Value)
  }else{[IO.File]::Move($tmp,$file)}
 }finally{if([IO.File]::Exists($tmp)){[IO.File]::Delete($tmp)}}
}
function LogLines([string]$file){
 if(-not (Test-Path -LiteralPath $file -PathType Leaf)){return}
 if((Get-Item -LiteralPath $file).Length -gt 2000000){throw 'NO11_CONNECTION_LOG_LIMIT'}
 Get-Content -LiteralPath $file -ErrorAction Stop
}
function LoggedProcess([string]$exe,[string[]]$arguments,[string]$folder,[string]$name,
 [int]$timeoutSeconds=360,[string]$stopFile=''){
 if($timeoutSeconds -lt 1 -or $timeoutSeconds -gt 900){throw 'NO11_CONNECTION_TIMEOUT_INVALID'}
 $stdout=Join-Path $folder ($name+'.stdout.log');$stderr=Join-Path $folder ($name+'.stderr.log')
 $progress=Join-Path $folder ($name+'.progress.json')
 $commandLine=(@($arguments|ForEach-Object {QuoteArgument ([string]$_)})) -join ' '
 Write-Host ('NO11_CONNECTION_STAGE='+$name)
 $p=$null;$watch=[Diagnostics.Stopwatch]::StartNew();$seen=0;$nextHeartbeat=0
 $timedOut=$false;$exited=$false;$code=$null
 try{
  # Wait only for the child we own, not its complete descendant process tree.
  # Polling also provides a deadline and visible progress. Never kill Excel.
  $p=Start-Process -FilePath $exe -ArgumentList $commandLine -WorkingDirectory $repo `
   -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $processHandle=$p.Handle
  while(-not ($exited=$p.WaitForExit(200))){
   if($watch.Elapsed.TotalSeconds -ge $nextHeartbeat){
    $lines=@(LogLines $stdout)
    for($i=$seen;$i -lt $lines.Count;$i++){
     if($lines[$i] -match '^(NO11_|ORDER_TRANSMISSION=)'){Write-Host $lines[$i]}
    }
    $seen=$lines.Count
    WriteResult $progress ([ordered]@{stage=$name;processId=$p.Id;elapsedSeconds=[int]$watch.Elapsed.TotalSeconds;
     timeoutSeconds=$timeoutSeconds;status='RUNNING';orderTransmission=$false})
    Write-Host ('NO11_CONNECTION_PROGRESS='+$name+'|ELAPSED_SECONDS='+[int]$watch.Elapsed.TotalSeconds)
    $nextHeartbeat=$watch.Elapsed.TotalSeconds+5
   }
   if($watch.Elapsed.TotalSeconds -ge $timeoutSeconds){
    $timedOut=$true
    if(-not [string]::IsNullOrWhiteSpace($stopFile)){
     [IO.File]::WriteAllText($stopFile,'STOP',[Text.UTF8Encoding]::new($false))
    }
    Write-Host ('NO11_CONNECTION_TIMEOUT='+$name+'|STOP_REQUESTED_NO_FORCE_TERMINATION')
    $exited=$p.WaitForExit(10000)
    break
   }
  }
  if($exited){$code=$p.ExitCode;if($null -eq $code){throw 'NO11_CONNECTION_EXIT_STATUS_UNAVAILABLE'}}
  $lines=@(LogLines $stdout);$errors=@(LogLines $stderr)
  for($i=$seen;$i -lt $lines.Count;$i++){
   if($lines[$i] -match '^(NO11_|ORDER_TRANSMISSION=)'){Write-Host $lines[$i]}
  }
  $status='EXITED';if($timedOut){$status='TIMEOUT'}
  WriteResult $progress ([ordered]@{stage=$name;processId=$p.Id;status=$status;
   exitCode=$code;timedOut=$timedOut;childMayStillBeRunning=(-not $exited);orderTransmission=$false})
  return [ordered]@{exitCode=$code;timedOut=$timedOut;childMayStillBeRunning=(-not $exited);
   messages=@($lines|Where-Object {$_ -match '^(NO11_|ORDER_TRANSMISSION=)'});stderr=$errors}
 }finally{
  $watch.Stop()
  if($null -ne $p){
   if(-not $exited){
    if(-not [string]::IsNullOrWhiteSpace($stopFile)){
     try{[IO.File]::WriteAllText($stopFile,'STOP',[Text.UTF8Encoding]::new($false))}catch{}
    }
    WriteResult (Join-Path $folder 'cleanup-required.json') ([ordered]@{
     stage=$name;processId=$p.Id;cleanupConfirmed=$false;orderTransmission=$false})
   }
   $p.Dispose()
  }
 }
}
function LoggedStep([string]$scriptFile,[string[]]$arguments,[string]$folder,[string]$name,
 [int]$timeoutSeconds=360,[string]$stopFile=''){
 $all=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$scriptFile)+$arguments
 return LoggedProcess 'powershell.exe' $all $folder $name $timeoutSeconds $stopFile
}
function ReadObject([string]$file){
 if(-not (Test-Path -LiteralPath $file -PathType Leaf)){return $null}
 if((Get-Item -LiteralPath $file).Length -gt 20000000){throw 'NO11_CONNECTION_JSON_LIMIT'}
 return Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
}
function Property($obj,[string]$name){
 if($null -eq $obj -or $name -notin $obj.PSObject.Properties.Name){return $null}
 return $obj.$name
}
function PrivateDirectory([string]$value){
 if(-not [IO.Path]::IsPathRooted($value)){throw 'NO11_CONNECTION_PRIVATE_PATH_REQUIRED'}
 $full=[IO.Path]::GetFullPath($value)
 if($full.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){
  throw 'NO11_CONNECTION_OUTPUT_IN_REPO'
 }
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   if(((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'NO11_CONNECTION_PRIVATE_REPARSE'}
  }
  $parent=Split-Path -Parent $cursor;if($parent -ceq $cursor){break};$cursor=$parent
 }
 [void][IO.Directory]::CreateDirectory($full)
 return $full
}
if($OfflineSelfTest){
 $tmp=Join-Path ([IO.Path]::GetTempPath()) ('no11 connection mock '+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($tmp)
 try{
  $child=Join-Path $tmp 'child.ps1'
  [IO.File]::WriteAllText($child,"Write-Output 'NO11_SYNTHETIC=ONLY'`n[Console]::Error.WriteLine('ERROR_LINE_ONE')`n[Console]::Error.WriteLine('ERROR_LINE_TWO')`nexit 7",[Text.UTF8Encoding]::new($true))
  $r=LoggedStep $child @() $tmp 'mock' 20
  if($r.exitCode -ne 7 -or $r.timedOut -or $r.messages -notcontains 'NO11_SYNTHETIC=ONLY' -or
     $r.stderr -notcontains 'ERROR_LINE_ONE' -or $r.stderr -notcontains 'ERROR_LINE_TWO'){
   throw 'NO11_CONNECTION_LOGGING_SELFTEST_FAILED'
  }
  if($null -ne (Property ([pscustomobject]@{status='OBSERVED'}) 'sequence')){throw 'NO11_CONNECTION_OPTIONAL_FIELD_SELFTEST_FAILED'}
  $slow=Join-Path $tmp 'slow.ps1';$stop=Join-Path $tmp 'slow.stop'
  [IO.File]::WriteAllText($slow,'param($StopFile);$w=[Diagnostics.Stopwatch]::StartNew();while(-not (Test-Path -LiteralPath $StopFile) -and $w.Elapsed.TotalSeconds -lt 8){Start-Sleep -Milliseconds 50};exit 0',[Text.UTF8Encoding]::new($true))
  $s=LoggedStep $slow @('-StopFile',$stop) $tmp 'slow' 1 $stop
  if(-not $s.timedOut -or $s.childMayStillBeRunning -or -not (Test-Path -LiteralPath $stop)){
   throw 'NO11_CONNECTION_TIMEOUT_SELFTEST_FAILED'
  }
  $receipt=Join-Path $tmp 'receipt.json'
  foreach($n in 1..3){WriteResult $receipt @{sequence=$n}}
  if((ReadObject $receipt).sequence -ne 3){throw 'NO11_CONNECTION_CHECKPOINT_SELFTEST_FAILED'}
  Write-Host 'NO11_CONNECTION_LOGGING_OFFLINE_SELFTEST=PASS'
  Write-Host 'NO11_CONNECTION_TIMEOUT_OFFLINE_SELFTEST=PASS'
  Write-Host 'ORDER_TRANSMISSION=False'
 }finally{Remove-Item -LiteralPath $tmp -Recurse -Force}
 exit 0
}
if(-not $ConfirmOrderOff){throw 'NO11_CONNECTION_CONFIRM_EXCEL_ORDER_OFF_REQUIRED'}
if($PSVersionTable.PSVersion.Major -ne 5){throw 'NO11_CONNECTION_WINDOWS_POWERSHELL_5_REQUIRED'}
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
if([string]::IsNullOrWhiteSpace($AccountWorkbookPath)){$AccountWorkbookPath=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'}
if([string]::IsNullOrWhiteSpace($DailyRun)){$DailyRun=Join-Path $local 'daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d'}
if([string]::IsNullOrWhiteSpace($OutputRoot)){$OutputRoot=Join-Path $local 'connection-confirmation'}
$root=PrivateDirectory $OutputRoot
if(@(Get-ChildItem -LiteralPath $root -Filter 'cleanup-required.json' -File -Recurse -Depth 1).Count -gt 0){throw 'NO11_CONNECTION_PREVIOUS_CLEANUP_REQUIRES_REVIEW'}
$out=PrivateDirectory (Join-Path $root ([guid]::NewGuid().ToString('N')))
$share=Join-Path $out 'No11_Connection_Result.json'
$report=[ordered]@{
 schemaId='ARK_NO11_CONNECTION_CHECK_RESULT_V1';sessionDate=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd');
 orderTransmission=$false;productionReady=$false;orderPermissionSource='USER_CONFIRMED_OFF_NOT_PROGRAMMATICALLY_VERIFIED';
 shadowTested=$false;recoveryTested=$false;liveOrdersTested=$false;
 status='IN_PROGRESS';accountCheck='NOT_RUN';marketCheck='NOT_RUN';sourceIndex=@();sourceIndexSkipped=$true
}
WriteResult $share $report
Write-Host ('SHARE_REPORT='+$share)
try{
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and $_.CommandLine -match
   '(?i)(?:Capture|Probe|Run|Prepare|Observe|Invoke)-No11\S*\.ps1|no11_\S*(?:service|controller)\.py'
 })
 if($active.Count -gt 0){throw 'NO11_CONNECTION_EXISTING_PROCESS_LEFT_RUNNING'}
 if($MarketOnly){$report.accountCheck='SKIPPED_MARKET_ONLY_NOT_RETESTED'}else{
  if(-not [IO.Path]::IsPathRooted($AccountWorkbookPath) -or -not (Test-Path -LiteralPath $AccountWorkbookPath -PathType Leaf)){
   throw 'NO11_CONNECTION_ACCOUNT_BOOK_FILE_REQUIRED'
  }
  $accountFile=Join-Path $out 'account-private.json';$accountStop=Join-Path $out 'account.stop'
  $report.accountCheck='STARTED';WriteResult $share $report
  $report.accountStep=LoggedStep (Join-Path $PSScriptRoot 'Observe-No11AccountReadOnly.ps1') @(
   '-WorkbookPath',$AccountWorkbookPath,'-OutputFile',$accountFile,
   '-StopFile',$accountStop,'-Samples','3','-PollSeconds','2'
  ) $out 'account' 120 $accountStop
  if($report.accountStep.timedOut){throw 'NO11_CONNECTION_ACCOUNT_TIMEOUT_REVIEW_REQUIRED'}
  $a=ReadObject $accountFile;$closed=ReadObject ($accountFile+'.closed.json')
  $report.accountLastStatus=Property $a 'status';$report.accountSavedSequence=Property $a 'sequence'
  $report.accountCloseFailed=Property $closed 'failed';$report.accountReadReason=Property $a 'reason'
  $report.brokerObservationStatus=Property (Property $a 'brokerObservation') 'status'
  $report.accountCheck='INCOMPLETE_REVIEW_REQUIRED'
  if($report.accountStep.exitCode -eq 0 -and $report.accountLastStatus -ceq 'OBSERVED' -and
     $report.accountSavedSequence -eq 3 -and $null -ne $closed -and $report.accountCloseFailed -eq $false){
   $report.accountCheck='THREE_SAVED_LAST_OBSERVED_CLEAN_EXIT'
  }
  WriteResult $share $report
 }
 $now=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9));$clock=$now.ToString('HH:mm:ss')
 if($clock -lt '09:00:00' -or $clock -gt '15:20:00' -or ($clock -ge '11:30:00' -and $clock -lt '12:30:00')){
  $report.marketCheck='OUTSIDE_ACTIVE_CAPTURE_START_WINDOW'
 }else{
  $ready=Join-Path $out 'market.ready.json';$stop=Join-Path $out 'market.stop'
  $report.marketCheck='STARTED';WriteResult $share $report
  $report.marketStep=LoggedStep (Join-Path $PSScriptRoot 'Run-No11Chart50ReadOnlyE2E.ps1') @(
   '-RunDir',$DailyRun,'-Samples','4','-Skip348Quote','-ReadyFile',$ready,'-StopFile',$stop
  ) $out 'market' 360 $stop
  $report.marketCheck='INCOMPLETE_REVIEW_REQUIRED';WriteResult $share $report
  if($report.marketStep.timedOut){throw 'NO11_CONNECTION_MARKET_TIMEOUT_REVIEW_REQUIRED'}
  $closed=ReadObject ($ready+'.closed.json')
  $report.temporaryWorkbookClosed=Property $closed 'temporaryWorkbookClosed'
  if($report.marketStep.exitCode -ne 0 -or $report.temporaryWorkbookClosed -ne $true){
   throw 'NO11_CONNECTION_MARKET_OR_CLEANUP_INCOMPLETE'
  }
  $folderLines=@($report.marketStep.messages|Where-Object {$_ -like 'NO11_C50_PRIVATE_FOLDER=*'})
  if($folderLines.Count -ne 1){throw 'NO11_CONNECTION_CAPTURE_PATH_REQUIRED'}
  $capture=([string]$folderLines[0]).Substring('NO11_C50_PRIVATE_FOLDER='.Length)
  $diagnostic=Join-Path $out 'market-diagnostic.json'
  $tool=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\no11_saved_chart_diagnostics.mjs'
  $report.diagnosticStep=LoggedProcess 'node' @($tool,'--folder',$capture,'--output',$diagnostic) $out 'diagnostic' 30
  if($report.diagnosticStep.timedOut -or $report.diagnosticStep.exitCode -ne 0){throw 'NO11_CONNECTION_DIAGNOSTIC_INCOMPLETE'}
  $report.marketDiagnostic=ReadObject $diagnostic
  if($report.marketDiagnostic.approximateMinuteVaRows -gt 0 -and $report.marketDiagnostic.newBarKeysObserved){
   $report.marketCheck='NEW_BARS_AND_USABLE_PROXY_ROWS_NOT_FULL_PIPELINE'
  }else{$report.marketCheck='NO_USABLE_PROXY_OR_NO_NEW_BARS_REVIEW_REQUIRED'}
 }
 $report.status='FINISHED_REVIEW_RESULTS'
}catch{
 $report.status='BLOCKED';$report.blocker=$_.Exception.Message
}finally{
 # Publish before any UI. Do not inspect source packages on this critical path.
 WriteResult $share $report
 Write-Host ('ACCOUNT_CHECK='+$report.accountCheck)
 Write-Host ('MARKET_CHECK='+$report.marketCheck)
 Write-Host ('SHARE_REPORT='+$share)
 Write-Host 'ORDER_TRANSMISSION=False'
 try{Start-Process explorer.exe -ArgumentList ('/select,"'+$share+'"')}catch{}
}
if($report.status -ne 'FINISHED_REVIEW_RESULTS' -or
   ($report.accountCheck -cne 'THREE_SAVED_LAST_OBSERVED_CLEAN_EXIT' -and -not $MarketOnly) -or
   $report.marketCheck -cne 'NEW_BARS_AND_USABLE_PROXY_ROWS_NOT_FULL_PIPELINE'){exit 2}
exit 0
