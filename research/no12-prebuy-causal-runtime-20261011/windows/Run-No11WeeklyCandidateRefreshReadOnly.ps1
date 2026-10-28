# Weekly-pool restricted DAILY RSS refresh. Original Excel books are never
# modified/saved. A complete pinned weekly all-universe scan is prerequisite.
# The old full-market source collector is unchanged; no orders or model fits.
param(
 [switch]$OfflineSelfTest,
 [string]$WeeklyRun,
 [string]$PrivateRoot,
 [string]$PinsFile,
 [string]$CatchUpAsOf='',
 [switch]$ConfirmYahooFridayRss,
 [ValidateRange(1,20)][int]$BatchSize=20,
 [ValidateRange(5,60)][int]$WaitSeconds=15,
 [ValidateRange(0,5000)][int]$MaxSymbols=0
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
# Unicode constructed at runtime so Windows PowerShell 5.1 also reads this UTF-8 file safely.
$headers=@(
 (-join [char[]]@(0x9298,0x67c4,0x540d,0x79f0)),(-join [char[]]@(0x5e02,0x5834,0x540d,0x79f0)),
 (-join [char[]]@(0x8db3,0x7a2e)),(-join [char[]]@(0x65e5,0x4ed8)),(-join [char[]]@(0x6642,0x523b)),
 (-join [char[]]@(0x59cb,0x5024)),(-join [char[]]@(0x9ad8,0x5024)),(-join [char[]]@(0x5b89,0x5024)),
 (-join [char[]]@(0x7d42,0x5024)),(-join [char[]]@(0x51fa,0x6765,0x9ad8))
)
function New-DailyFormula([string]$symbol){
 if($symbol -cnotmatch '^[0-9A-Z]{4}\.T$'){throw 'NO11_DAILY_SYMBOL_INVALID'}
 return ('=RssChart($A$2:$J$2,"{0}","D",100)' -f $symbol)
}
function Now-Jst {return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9)).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)}
function Number-Token([object]$value){
 if($value -isnot [double] -and $value -isnot [int] -and $value -isnot [long] -and $value -isnot [decimal]){return $null}
 $n=[double]$value
 if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 0){return $null}
 # Explicitly Excel Value2 round-trip, not vendor decimal-token certification.
 return $n.ToString('R',$ci)
}
function Date-Token([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('yyyy-MM-dd',$ci)}
 if($value -is [double] -or $value -is [int]){
  $n=[double]$value
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)
 }
 $s=([string]$value).Replace('/','-');$d=[datetime]::MinValue
 if([datetime]::TryParseExact($s,'yyyy-MM-dd',$ci,[Globalization.DateTimeStyles]::None,[ref]$d)){return $d.ToString('yyyy-MM-dd',$ci)}
 return $null
}
function Read-DailyRows([object]$values){
 $rows=New-Object System.Collections.ArrayList;$invalid=0
 if($values -is [array] -and $values.Rank -eq 2){
  $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
  for($r=$r0;$r -lt $r0+$values.GetLength(0);$r++){
   $dateValue=$values.GetValue($r,$c0+3)
   if($null -eq $dateValue -or [string]::IsNullOrWhiteSpace([string]$dateValue)){continue}
   $day=Date-Token $dateValue
   if($null -eq $day){$invalid++;continue}
   $p=@();for($j=5;$j -le 9;$j++){$p+=@(Number-Token $values.GetValue($r,$c0+$j))}
   if($p.Count -ne 5 -or @($p | Where-Object {$null -eq $_}).Count -gt 0){$invalid++;continue}
   [void]$rows.Add([ordered]@{session=$day;open=$p[0];high=$p[1];low=$p[2];close=$p[3];volume=$p[4]})
  }
 }
 return [pscustomobject]@{rows=@($rows.ToArray());invalidRows=$invalid}
}
function Save-Capture([string]$directory,[object]$payload){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $payload -Depth 10 -Compress)+[char]10)
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{$sha=([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
 $final=Join-Path $directory ($payload.symbol+'-'+$sha+'.json')
 $temp=Join-Path $directory ([guid]::NewGuid().ToString('N')+'.pending');$stream=$null
 try{
  $stream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true);$stream.Dispose();$stream=$null
  [IO.File]::Move($temp,$final)
 }finally{if($null -ne $stream){$stream.Dispose()}}
}
if($OfflineSelfTest){
 if((New-DailyFormula '7203.T') -cne '=RssChart($A$2:$J$2,"7203.T","D",100)'){throw 'NO11_DAILY_FORMULA_SELFTEST'}
 $blocked=$false;try{[void](New-DailyFormula '7203.T");BAD(')}catch{$blocked=$true}
 if(-not $blocked){throw 'NO11_DAILY_FORMULA_INJECTION'}
 $a=[Array]::CreateInstance([object],1,10);$a.SetValue('2026/10/23',0,3)
 foreach($j in 5..8){$a.SetValue([double]101.5,0,$j)};$a.SetValue([double]200,0,9)
 $r=Read-DailyRows $a
 if($r.rows.Count -ne 1 -or $r.rows[0].close -cne '101.5' -or $r.rows[0].session -cne '2026-10-23'){throw 'NO11_DAILY_PARSE_SELFTEST'}
 $a.SetValue('BAD',0,8);$r=Read-DailyRows $a
 if($r.invalidRows -ne 1){throw 'NO11_DAILY_INVALID_SELFTEST'}
 if($null -ne (Date-Token '2026/02/30') -or $null -ne (Number-Token ([double]::NaN))){throw 'NO11_DAILY_TOKEN_SELFTEST'}
 Write-Host 'NO11_DAILY_OFFLINE_SELFTEST=PASS';Write-Host 'ORDER_TRANSMISSION=False';exit 0
}
$tool=Join-Path (Split-Path $PSScriptRoot -Parent) 'tools\no11_weekly_g1_refresh.mjs'
if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){throw 'NO11_DAILY_TOOL_MISSING'}
[void](Get-Command node -ErrorAction Stop)
if([string]::IsNullOrWhiteSpace($WeeklyRun) -or -not [IO.Path]::IsPathRooted($WeeklyRun) -or
  -not (Test-Path -LiteralPath $WeeklyRun -PathType Container)){
 throw 'NO11_WEEKLY_FULL_SCAN_RUN_REQUIRED'
}
if([string]::IsNullOrWhiteSpace($PrivateRoot)){$PrivateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\weekly-pool-refresh'}
if(-not [string]::IsNullOrWhiteSpace($PinsFile) -and
  (-not [IO.Path]::IsPathRooted($PinsFile) -or
   -not (Test-Path -LiteralPath $PinsFile -PathType Leaf))){
 throw 'NO11_WEEKLY_PINS_FILE_INVALID'
}
function Get-Plan {
 $planArgs=@('plan','--weekly-run',$WeeklyRun,'--root',$PrivateRoot)
 if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
  if($CatchUpAsOf -cnotmatch '^20\d{2}-\d{2}-\d{2}$'){throw 'NO11_DAILY_CATCHUP_DAY_INVALID'}
  $planArgs+=@('--catch-up-asof',$CatchUpAsOf)
 }
 if($ConfirmYahooFridayRss){$planArgs+=@('--yahoo-friday-rss-confirm','true')}
 $text=(& node $tool @planArgs | Out-String)
 if($LASTEXITCODE -ne 0){throw 'NO11_WEEKLY_REFRESH_PLAN_FAILED'}
 return ($text | ConvertFrom-Json)
}
$work=Get-Plan;$run=$work.run;$lock=$null;$excel=$null;$book=$null;$sheets=@();$failed=$false;$stage='LOCK'
try{
 # File sharing lock is released by the OS after a crash; no stale PID bypass needed.
 $lock=[IO.File]::Open((Join-Path $run 'capture.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $work=Get-Plan
 if($work.run -cne $run){throw 'NO11_DAILY_TARGET_CHANGED_RESTART'}
 $remaining=@($work.remaining);if($MaxSymbols -gt 0){$remaining=@($remaining | Select-Object -First $MaxSymbols)}
 Write-Host ('NO11_DAILY_TARGET='+$work.plan.asOfSession)
 Write-Host ('NO11_DAILY_RESUME_VERIFIED='+$work.resumed+'/'+$work.plan.symbols.Count)
 if($remaining.Count -gt 0){
  $tcp=New-Object Net.Sockets.TcpClient;$active=$false
  try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}catch [Net.Sockets.SocketException]{}finally{$tcp.Close()}
  if($active){throw 'NO11_DAILY_ARK_UI_MUST_BE_STOPPED'}
  $stage='EXCEL_WINDOW'
  # Excel changes MainWindowTitle when the active workbook switches.
  # Prefer one uniquely Ark-labelled visible process, or fall back to the
  # single visible Excel process. Original workbook/sheet COM checks remain
  # mandatory before creating a temporary book.
  $visible=@(Get-Process EXCEL -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne [IntPtr]::Zero})
  $arkNamed=@($visible | Where-Object {$_.MainWindowTitle -like 'Ark_No11_*'})
  $processes=@()
  if($arkNamed.Count -eq 1){$processes=@($arkNamed)}
  elseif($arkNamed.Count -eq 0 -and $visible.Count -eq 1){$processes=@($visible)}
  Write-Host ('NO11_DAILY_EXCEL_DISCOVERY=VISIBLE_{0}|ARK_NAMED_{1}|SELECTED_{2}' -f $visible.Count,$arkNamed.Count,$processes.Count)
  if($processes.Count -ne 1){throw 'NO11_DAILY_EXCEL_IDENTITY_NOT_UNIQUE'}
  if(-not ('No11DailyWindow' -as [type])){
   Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11DailyWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
  }
  $script:dailyWindows=@();$callback=[No11DailyWindow+Callback]{param($h,$p) $n=New-Object Text.StringBuilder 128;[void][No11DailyWindow]::GetClassName($h,$n,128);if($n.ToString() -ceq 'EXCEL7'){$script:dailyWindows+=@($h)};return $true}
  [void][No11DailyWindow]::EnumChildWindows($processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
  if($script:dailyWindows.Count -ne 1){throw 'NO11_DAILY_EXCEL7_NOT_UNIQUE'}
  $iid=[guid]'00020400-0000-0000-C000-000000000046';$obj=$null
  $hr=[No11DailyWindow]::AccessibleObjectFromWindow($script:dailyWindows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
  if($hr -ne 0 -or $null -eq $obj){throw 'NO11_DAILY_COM_ATTACH_FAILED'}
  $excel=$obj.Application
  if($excel.Workbooks.Count -ne 2){throw 'NO11_DAILY_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}
  $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx');$market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
  if($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY' -or $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){throw 'NO11_DAILY_WORKBOOK_IDENTITY_INVALID'}
  $stage='CAPACITY';$existing=0
  foreach($wb in @($account,$market)){
   for($i=1;$i -le $wb.Worksheets.Count;$i++){
    $used=$wb.Worksheets.Item($i).UsedRange
    if([long]$used.CountLarge -gt 100000){throw 'NO11_DAILY_CAPACITY_SCAN_TOO_LARGE'}
    $cells=$null
    try{$cells=$used.SpecialCells(-4123)}catch [Runtime.InteropServices.COMException]{if($_.Exception.HResult -ne -2146827284){throw}}
    if($null -ne $cells){foreach($cell in $cells.Cells){if([string]$cell.Formula -match '(?i)Rss(?:Chart|Trend)[A-Za-z]*\s*\('){$existing++}}}
   }
  }
  if($existing+$BatchSize -gt 50){throw 'NO11_DAILY_CHART_CAPACITY_EXCEEDED'}
  for($offset=0;$offset -lt $remaining.Count;$offset+=$BatchSize){
   $batch=@($remaining[$offset..([Math]::Min($offset+$BatchSize-1,$remaining.Count-1))]);$sheets=@();$stage='TEMPORARY_WORKBOOK'
   $book=$excel.Workbooks.Add()
   foreach($symbol in $batch){
    $ws=$book.Worksheets.Add();$ws.Name='DAILY_'+$symbol.Replace('.','_')
    for($j=0;$j -lt 10;$j++){$ws.Cells.Item(2,$j+1).Value2=$headers[$j]}
    $ws.Range('A1').Formula=(New-DailyFormula $symbol);$sheets+=@($ws)
   }
   $stage='WAIT_FOR_RSS';Start-Sleep -Seconds $WaitSeconds
   $payloads=New-Object System.Collections.ArrayList;$usable=0;$complete=0;$stage='DAILY_CAPTURE'
   for($k=0;$k -lt $batch.Count;$k++){
    $symbol=$batch[$k];$ws=$sheets[$k];$formula=New-DailyFormula $symbol
    if([string]$ws.Range('A1').Formula -cne $formula){throw 'NO11_DAILY_FORMULA_CHANGED'}
    $start=Now-Jst;$values=$ws.Range('A3:J102').Value2;$end=Now-Jst;$parsed=Read-DailyRows $values
    $status=if($parsed.rows.Count -gt 0){'OBSERVED'}else{'UNAVAILABLE'}
    if($parsed.rows.Count -gt 0){$usable++}
    $dates=@($parsed.rows | ForEach-Object {$_.session})
    if(@($work.plan.expectedSessions | Where-Object {$_ -notin $dates}).Count -eq 0){$complete++}
    [void]$payloads.Add([ordered]@{
     schemaId='ARK_NO11_RSS_DAILY_CAPTURE_V1';planId=$work.plan.planId;symbol=$symbol;asOfSession=$work.plan.asOfSession;
     period='D';formula=$formula;status=$status;observedStartJst=$start;observedEndJst=$end;
     rows=$parsed.rows;invalidRows=$parsed.invalidRows;priceBasis='RSS_CHART_UNVERIFIED';
     decimalProvenance='EXCEL_VALUE2_ROUNDTRIP';corporateActionsCleared=$false;originalVendorDecimalCertified=$false;
     productionReady=$false;orderTransmission=$false
    })
   }
   # Do not checkpoint an all-empty wave as completed when the feed may be disconnected.
   if($usable -eq 0){throw 'NO11_DAILY_ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT'}
   foreach($payload in $payloads){Save-Capture (Join-Path $run 'sources') $payload}
   $book.Close($false);foreach($ws in $sheets){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}
   $sheets=@();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book);$book=$null
   Write-Host ('NO11_DAILY_PROGRESS={0}/{1}|WAVE_OBSERVED={2}|WAVE_FULL76={3}' -f ($work.resumed+$offset+$batch.Count),$work.plan.symbols.Count,$usable,$complete)
   # Canary runs automatically; avoid collecting thousands of unusable snapshots.
   if($complete -eq 0){throw 'NO11_DAILY_NO_FULL_HISTORY_IN_WAVE_REVIEW_PARTIAL_REPORT'}
  }
 }
}catch{
 $failed=$true;$reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_DAILY_COM_OR_IO_FAILURE'}
 Write-Host ('NO11_DAILY_CAPTURE=BLOCKED|'+$reason);Write-Host ('NO11_DAILY_STAGE='+$stage)
 Write-Host ('NO11_DAILY_HRESULT='+$_.Exception.HResult)
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 foreach($ws in $sheets){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
 if($null -ne $lock){$lock.Dispose()}
}
$reportArgs=@('report','--run',$run,'--weekly-run',$WeeklyRun)
if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
 $reportArgs+=@('--catch-up-asof',$CatchUpAsOf)
}
if($ConfirmYahooFridayRss){$reportArgs+=@('--yahoo-friday-rss-confirm','true')}
if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$reportArgs+=@('--pins-file',$PinsFile)}
$output=@(& node $tool @reportArgs)
$reportExit=$LASTEXITCODE
$output|ForEach-Object {Write-Host $_}
if($failed -or $reportExit -ne 0){exit 2}
if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
 Write-Host 'NO11_WEEKLY_DAILY_CAPTURE=HISTORICAL_ASOF_WITH_REAL_CURRENT_RECEIPT'
}
Write-Host 'NO11_WEEKLY_DAILY_REFRESH=COMPLETE_NOT_FULL_UNIVERSE'
Write-Host 'ORDER_TRANSMISSION=False'
exit 0
