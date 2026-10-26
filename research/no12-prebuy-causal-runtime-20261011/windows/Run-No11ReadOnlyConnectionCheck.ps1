# Finite account/market read-only check after Windows native I/O fixes.
# Never enables orders, starts the trading service, or changes existing books.
param(
 [string]$AccountWorkbookPath,
 [string]$DailyRun,
 [string]$OutputRoot,
 [switch]$ConfirmOrderOff,
 [switch]$OfflineSelfTest
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
function LoggedStep([string]$scriptFile,[string[]]$arguments,[string]$folder,[string]$name){
 $stdout=Join-Path $folder ($name+'.stdout.log')
 $stderr=Join-Path $folder ($name+'.stderr.log')
 $all=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$scriptFile)+$arguments
 $commandLine=(@($all|ForEach-Object {QuoteArgument ([string]$_)})) -join ' '
 Write-Host ('NO11_CONNECTION_STAGE='+$name)
 # Redirect at process creation rather than merging native stderr into a
 # PowerShell Stop pipeline. Preserve the complete error, not only line one.
 $p=Start-Process -FilePath 'powershell.exe' -ArgumentList $commandLine -WorkingDirectory $repo `
  -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 try{$code=$p.ExitCode}finally{$p.Dispose()}
 if($null -eq $code){throw 'NO11_CONNECTION_EXIT_STATUS_UNAVAILABLE'}
 $lines=@(Get-Content -LiteralPath $stdout -ErrorAction Stop)
 $errorLines=@(Get-Content -LiteralPath $stderr -ErrorAction Stop)
 $messages=@($lines|Where-Object {$_ -match '^(NO11_|ORDER_TRANSMISSION=)'})
 $messages|ForEach-Object {Write-Host $_}
 return [ordered]@{exitCode=[int]$code;messages=$messages;stderr=$errorLines}
}
function ReadObject([string]$file){
 if(-not (Test-Path -LiteralPath $file -PathType Leaf)){return $null}
 return Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json
}
function Property($obj,[string]$name){
 if($null -eq $obj -or $name -notin $obj.PSObject.Properties.Name){return $null}
 return $obj.$name
}
function PrivateDirectory([string]$value){
 if(-not [IO.Path]::IsPathRooted($value)){throw 'NO11_CONNECTION_PRIVATE_PATH_REQUIRED'}
 $full=[IO.Path]::GetFullPath($value)
 if($full.Equals($repo,[StringComparison]::OrdinalIgnoreCase) -or
    $full.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)){
  throw 'NO11_CONNECTION_OUTPUT_IN_REPO'
 }
 $cursor=$full
 while(-not [string]::IsNullOrWhiteSpace($cursor)){
  if(Test-Path -LiteralPath $cursor){
   if(((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
    throw 'NO11_CONNECTION_PRIVATE_REPARSE'
   }
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
  $program="Write-Output 'NO11_SYNTHETIC=ONLY'`n[Console]::Error.WriteLine('ERROR_LINE_ONE')`n[Console]::Error.WriteLine('ERROR_LINE_TWO')`nexit 7"
  [IO.File]::WriteAllText($child,$program,[Text.UTF8Encoding]::new($true))
  $r=LoggedStep $child @() $tmp 'mock'
  if($r.exitCode -ne 7 -or $r.messages -notcontains 'NO11_SYNTHETIC=ONLY' -or
     $r.stderr -notcontains 'ERROR_LINE_ONE' -or $r.stderr -notcontains 'ERROR_LINE_TWO'){
   throw 'NO11_CONNECTION_LOGGING_SELFTEST_FAILED'
  }
  if($null -ne (Property ([pscustomobject]@{status='OBSERVED'}) 'sequence')){throw 'NO11_CONNECTION_OPTIONAL_FIELD_SELFTEST_FAILED'}
  Write-Host 'NO11_CONNECTION_LOGGING_OFFLINE_SELFTEST=PASS'
  Write-Host 'ORDER_TRANSMISSION=False'
 }finally{Remove-Item -LiteralPath $tmp -Recurse -Force}
 exit 0
}
if(-not $ConfirmOrderOff){throw 'NO11_CONNECTION_CONFIRM_EXCEL_ORDER_OFF_REQUIRED'}
if($PSVersionTable.PSVersion.Major -ne 5){throw 'NO11_CONNECTION_WINDOWS_POWERSHELL_5_REQUIRED'}
$local=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
if([string]::IsNullOrWhiteSpace($AccountWorkbookPath)){
 $AccountWorkbookPath=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ark_No11_MSII_RSS.xlsx'
}
if([string]::IsNullOrWhiteSpace($DailyRun)){
 $DailyRun=Join-Path $local 'daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d'
}
if([string]::IsNullOrWhiteSpace($OutputRoot)){$OutputRoot=Join-Path $local 'connection-confirmation'}
$root=PrivateDirectory $OutputRoot
$out=PrivateDirectory (Join-Path $root ([guid]::NewGuid().ToString('N')))
$report=[ordered]@{
 schemaId='ARK_NO11_CONNECTION_CHECK_RESULT_V1';
 sessionDate=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-dd');
 orderTransmission=$false;productionReady=$false;
 orderPermissionSource='USER_CONFIRMED_OFF_NOT_PROGRAMMATICALLY_VERIFIED';
 shadowTested=$false;recoveryTested=$false;liveOrdersTested=$false;
 accountCheck='NOT_RUN';marketCheck='NOT_RUN';sourceIndex=@()
}
try{
 $active=@(Get-CimInstance Win32_Process|Where-Object {
  $_.ProcessId -ne $PID -and $_.CommandLine -match
   '(?i)(?:Capture|Probe|Run|Prepare|Observe|Invoke)-No11\S*\.ps1|no11_\S*(?:service|controller)\.py'
 })
 if($active.Count -gt 0){throw 'NO11_CONNECTION_EXISTING_PROCESS_LEFT_RUNNING'}
 if(-not [IO.Path]::IsPathRooted($AccountWorkbookPath) -or
    -not (Test-Path -LiteralPath $AccountWorkbookPath -PathType Leaf)){
  throw 'NO11_CONNECTION_ACCOUNT_BOOK_FILE_REQUIRED'
 }
 $accountFile=Join-Path $out 'account-private.json'
 $report.accountCheck='STARTED'
 $report.accountStep=LoggedStep (Join-Path $PSScriptRoot 'Observe-No11AccountReadOnly.ps1') @(
  '-WorkbookPath',$AccountWorkbookPath,'-OutputFile',$accountFile,
  '-StopFile',(Join-Path $out 'account.stop'),'-Samples','3','-PollSeconds','2'
 ) $out 'account'
 $a=ReadObject $accountFile;$closed=ReadObject ($accountFile+'.closed.json')
 $report.accountLastStatus=Property $a 'status'
 $report.accountSavedSequence=Property $a 'sequence'
 $report.accountCloseFailed=Property $closed 'failed'
 $report.accountReadReason=Property $a 'reason'
 $report.brokerObservationStatus=Property (Property $a 'brokerObservation') 'status'
 $report.accountCheck='INCOMPLETE_REVIEW_REQUIRED'
 if($report.accountStep.exitCode -eq 0 -and $report.accountLastStatus -ceq 'OBSERVED' -and
    $report.accountSavedSequence -eq 3 -and $null -ne $closed -and $report.accountCloseFailed -eq $false){
  $report.accountCheck='THREE_SAVED_LAST_OBSERVED_CLEAN_EXIT'
 }
 # Account read failure does not fabricate market success or prevent a separate
 # read-only market diagnostic. No trading process is started in either case.
 $now=[datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
 if($now.ToString('HH:mm:ss') -lt '09:00:00' -or $now.ToString('HH:mm:ss') -gt '15:20:00'){
  $report.marketCheck='OUTSIDE_COLLECTOR_START_WINDOW'
 }else{
  $report.marketCheck='STARTED'
  $report.marketStep=LoggedStep (Join-Path $PSScriptRoot 'Run-No11Chart50ReadOnlyE2E.ps1') @(
   '-RunDir',$DailyRun,'-Samples','4','-Skip348Quote'
  ) $out 'market'
  $report.marketCheck='INCOMPLETE_REVIEW_REQUIRED'
  if($report.marketStep.exitCode -eq 0 -and $report.marketStep.messages -contains
    'NO11_C50_E2E_READONLY=COMPLETE_NOT_SELECTOR_NOT_TRADING'){
   $report.marketCheck='CAPTURE_AND_IMPORT_COMPLETED_REVIEW_COUNTS'
  }
 }
}catch{
 $report.blocker=$_.Exception.Message
}finally{
 # Index only already known source packages; no repeated whole-PC search,
 # extraction, model substitution, fitting, or invented reviewed evidence.
 try{
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $packages=@(
   (Join-Path $env:USERPROFILE 'Downloads\Ark_No11_FrozenP1_Inference_20261023_PRIVATE.zip'),
   (Join-Path $env:USERPROFILE 'Downloads\Ark_Capital_V5_Anchor_Slot3_R1_20261005_PRIVATE.zip')
  )
  $originals='C:\ArkPrivate\MA4_Originals'
  if(Test-Path -LiteralPath $originals -PathType Container){
   $packages+=@(Get-ChildItem -LiteralPath $originals -Directory|ForEach-Object {
    Join-Path $_.FullName 'Ark_MA4_Required_Originals_PRIVATE.zip'
   }|Where-Object {Test-Path -LiteralPath $_ -PathType Leaf})
  }
  foreach($file in $packages){
   if(-not (Test-Path -LiteralPath $file -PathType Leaf)){continue}
   $zip=$null
   try{
    $zip=[IO.Compression.ZipFile]::OpenRead($file)
    $hits=@($zip.Entries|Where-Object {$_.FullName -match '(?i)h235|h2_h3_h5|mret|arrival|manifest|freeze|capital|\.zip$'})
    $report.sourceIndex+=@([ordered]@{path=$file;matched=$hits.Count;truncated=($hits.Count -gt 120);
     entries=@($hits|Select-Object -First 120|ForEach-Object {$_.FullName})})
   }catch{$report.sourceIndex+=@([ordered]@{path=$file;status='INDEX_UNAVAILABLE'})}
   finally{if($null -ne $zip){$zip.Dispose()}}
  }
 }catch{$report.sourceIndexError='KNOWN_SOURCE_INDEX_UNAVAILABLE'}
 $share=Join-Path $out 'No11_Connection_Result.json'
 [IO.File]::WriteAllText($share,($report|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($true))
 Write-Host ('ACCOUNT_CHECK='+$report.accountCheck)
 Write-Host ('MARKET_CHECK='+$report.marketCheck)
 Write-Host ('SHARE_REPORT='+$share)
 Write-Host 'ORDER_TRANSMISSION=False'
 try{Start-Process explorer.exe -ArgumentList ('/select,"'+$share+'"')}catch{}
}
if($report.accountCheck -cne 'THREE_SAVED_LAST_OBSERVED_CLEAN_EXIT' -or
   $report.marketCheck -cne 'CAPTURE_AND_IMPORT_COMPLETED_REVIEW_COUNTS'){exit 2}
exit 0
