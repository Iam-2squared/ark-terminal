# Weekly-pool restricted DAILY RSS refresh. Original Excel books are never
# modified/saved. A complete pinned weekly all-universe scan is prerequisite.
# The old full-market source collector is unchanged; no orders or model fits.
param(
 [switch]$OfflineSelfTest,
 [switch]$FirstBuyFridayLimited,
 [string]$WeeklyRun,
 [string]$PrivateRoot,
 [string]$PinsFile,
 [string]$CatchUpAsOf='',
 [switch]$ConfirmYahooFridayRss,
 # Logical progress every 100 or 50 symbols. Physical RSS calls never exceed
 # the observed 50-function Excel cap, minus three reserved safety slots.
 [ValidateSet(50,100)][int]$GroupSize=100,
 [ValidateRange(1,47)][int]$BatchSize=30,
 # Operator-selected MAX throughput; ramp 5 -> 10 -> 20 -> 40 -> up to 47.
 # Does not override Excel capacity, source validity or chart safety reserves.
 [switch]$AutoMaxThroughput,
 [ValidateRange(5,60)][int]$WaitSeconds=25,
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
function SafePhysicalBatch([int]$originalCharts,[int]$requested){
 if($originalCharts -lt 0 -or $originalCharts -gt 50 -or
    $requested -lt 1 -or $requested -gt 47){throw 'NO11_DAILY_CHART_BUDGET_ARGS_INVALID'}
 # Reserve three chart functions for unrelated, held and recovery use.
 # Each temporary workbook is closed before opening the next wave.
 $capacity=50-$originalCharts-3
 if($capacity -lt 1){throw 'NO11_DAILY_CHART_CAPACITY_EXHAUSTED'}
 return [Math]::Min($requested,$capacity)
}
function NextWaveEnd([int]$offset,[int]$remaining,[int]$groupSize,[int]$physical){
 if($offset -lt 0 -or $remaining -lt 1 -or $offset -ge $remaining -or
    $groupSize -notin @(50,100) -or $physical -lt 1 -or $physical -gt 47){
  throw 'NO11_DAILY_WAVE_ARGUMENT_INVALID'
 }
 $groupEnd=[int]([Math]::Floor($offset/$groupSize)+1)*$groupSize
 return [Math]::Min($remaining,[Math]::Min($offset+$physical,$groupEnd))
}
function NextAutoMaxBatch([int]$current,[int]$ceiling,[bool]$clean){
 if($current -lt 1 -or $ceiling -lt 1 -or $ceiling -gt 47 -or $current -gt $ceiling){
  throw 'NO11_DAILY_AUTOMAX_BATCH_ARGS_INVALID'
 }
 if(-not $clean){return [Math]::Max(1,[int][Math]::Floor($current/2))}
 return [Math]::Min($ceiling,[Math]::Max($current+5,$current*2))
}
# Excel can briefly reject COM calls during RSS recalculation. Retry only
# reads/idempotent writes. For Add/Close verify object counts after a rejected
# reply; never duplicate a workbook or sheet after an ambiguous COM response.
$script:DailyExcelComBusyCount=0
$script:DailyExcelOp='NO_EXCEL_OPERATION'
function Get-ExcelBusyHresult([System.Exception]$errorValue){
 for($e=$errorValue;$null -ne $e;$e=$e.InnerException){
  if([int]$e.HResult -in @(-2147418111,-2147417846)){return [int]$e.HResult}
 }
 return 0
}
function Wait-ExcelComBusy([string]$operation,[int]$attempt,[int]$hr){
 if($attempt -lt 1 -or $attempt -gt 5){throw 'NO11_DAILY_EXCEL_COM_RETRY_BUDGET_INVALID'}
 $script:DailyExcelComBusyCount++
 $seconds=[Math]::Min(5,$attempt)
 Write-Host ('NO11_DAILY_EXCEL_COM_RETRY={0}|ATTEMPT={1}/5|HRESULT={2}|WAIT_SECONDS={3}' -f $operation,$attempt,$hr,$seconds)
 Start-Sleep -Seconds $seconds
}
function Invoke-ExcelIdempotent([scriptblock]$action,[string]$operation){
 for($attempt=0;$attempt -le 5;$attempt++){
  try{return (& $action)}catch{
   $hr=Get-ExcelBusyHresult $_.Exception
   if($hr -eq 0 -or $attempt -ge 5){throw}
   Wait-ExcelComBusy $operation ($attempt+1) $hr
  }
 }
 throw 'NO11_DAILY_EXCEL_COM_RETRY_EXHAUSTED'
}
function New-ExcelComObjectChecked([scriptblock]$add,[scriptblock]$count,[string]$operation){
 $before=[int](Invoke-ExcelIdempotent $count ($operation+'_PRE_COUNT'))
 for($attempt=0;$attempt -le 5;$attempt++){
  $current=[int](Invoke-ExcelIdempotent $count ($operation+'_CURRENT_COUNT'))
  if($current -ne $before){throw 'NO11_DAILY_EXCEL_ADD_COUNT_CHANGED_NO_DUPLICATE'}
  try{return (& $add)}catch{
   $hr=Get-ExcelBusyHresult $_.Exception
   if($hr -eq 0 -or $attempt -ge 5){throw}
   Wait-ExcelComBusy $operation ($attempt+1) $hr
   $after=[int](Invoke-ExcelIdempotent $count ($operation+'_AFTER_REJECT'))
   if($after -ne $before){throw 'NO11_DAILY_EXCEL_ADD_OUTCOME_AMBIGUOUS_NO_DUPLICATE'}
  }
 }
 throw 'NO11_DAILY_EXCEL_ADD_RETRY_EXHAUSTED'
}
function Close-ExcelTemporaryWorkbook([object]$application,[object]$temporary){
 for($attempt=0;$attempt -le 5;$attempt++){
  try{$temporary.Close($false);return}catch{
   $hr=Get-ExcelBusyHresult $_.Exception
   if($hr -eq 0 -or $attempt -ge 5){throw}
   Wait-ExcelComBusy 'WORKBOOK_CLOSE' ($attempt+1) $hr
   $count=[int](Invoke-ExcelIdempotent { $application.Workbooks.Count } 'WORKBOOK_CLOSE_COUNT')
   if($count -eq 2){return} # Closed; COM reply alone was rejected.
   if($count -ne 3){throw 'NO11_DAILY_EXCEL_CLOSE_OUTCOME_AMBIGUOUS'}
  }
 }
 throw 'NO11_DAILY_EXCEL_CLOSE_RETRY_EXHAUSTED'
}
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

 $rpcRejected=[Runtime.InteropServices.COMException]::new('temporary busy',-2147418111)
 $rpcLater=[Runtime.InteropServices.COMException]::new('retry later',-2147417846)
 $other=[Runtime.InteropServices.COMException]::new('disconnected',-2147023174)
 if((Get-ExcelBusyHresult $rpcRejected) -ne -2147418111 -or
    (Get-ExcelBusyHresult $rpcLater) -ne -2147417846 -or
    (Get-ExcelBusyHresult $other) -ne 0){throw 'NO11_DAILY_COM_BUSY_CLASSIFICATION_SELFTEST'}
 $script:offlineComProbe=0
 $idempotent=Invoke-ExcelIdempotent {
  $script:offlineComProbe++
  if($script:offlineComProbe -eq 1){
   throw [Runtime.InteropServices.COMException]::new('synthetic Excel busy',-2147418111)
  }
  return 42
 } 'OFFLINE_TRANSIENT_BUSY'
 if($idempotent -ne 42 -or $script:offlineComProbe -ne 2){throw 'NO11_DAILY_COM_IDEMPOTENT_RETRY_SELFTEST'}
 $script:offlineAddCount=1;$script:offlineAddAttempts=0;$ambiguousBlocked=$false
 try{
  [void](New-ExcelComObjectChecked {
   $script:offlineAddAttempts++
   $script:offlineAddCount=2
   throw [Runtime.InteropServices.COMException]::new('synthetic Excel busy after add',-2147418111)
  } { $script:offlineAddCount } 'OFFLINE_ADD_AMBIGUOUS')
 }catch{
  $ambiguousBlocked=$_.Exception.Message -ceq 'NO11_DAILY_EXCEL_ADD_OUTCOME_AMBIGUOUS_NO_DUPLICATE'
 }
 if(-not $ambiguousBlocked -or $script:offlineAddAttempts -ne 1){
  throw 'NO11_DAILY_COM_NONIDEMPOTENT_ADD_SELFTEST'
 }
 Write-Host 'NO11_DAILY_EXCEL_BUSY_BOUNDED_RETRY_SELFTEST=PASS'
 Write-Host 'NO11_DAILY_EXCEL_AMBIGUOUS_ADD_FAILCLOSED_SELFTEST=PASS'
 $batch=5
 foreach($size in @(10,20,40,47)){
  $batch=NextAutoMaxBatch $batch 47 $true
  if($batch -ne $size){throw 'NO11_DAILY_AUTOMAX_RAMP_SELFTEST'}
 }
 if((NextAutoMaxBatch 47 47 $false) -ne 23 -or
    (NextAutoMaxBatch 5 47 $false) -ne 2 -or
    (NextAutoMaxBatch 12 12 $true) -ne 12 -or
    (SafePhysicalBatch 0 47) -ne 47){
  throw 'NO11_DAILY_AUTOMAX_SAFETY_SELFTEST'
 }
 Write-Host 'NO11_DAILY_AUTOMAX_RAMP_OFFLINE_SELFTEST=PASS'
 if($script:DailyExcelOp -cne 'NO_EXCEL_OPERATION'){
  throw 'NO11_DAILY_COM_OPERATION_TRACKER_SELFTEST'
 }
 if((SafePhysicalBatch 0 47) -ne 47 -or (SafePhysicalBatch 19 47) -ne 28 -or
    (SafePhysicalBatch 39 30) -ne 8 -or
    (NextWaveEnd 90 429 100 30) -ne 100 -or
    (NextWaveEnd 100 429 100 30) -ne 130 -or
    (NextWaveEnd 400 429 100 30) -ne 429){
  throw 'NO11_DAILY_GROUP_CAPACITY_SELFTEST_FAILED'
 }
 $selftestOffset=0;$selftestSizes=@()
 while($selftestOffset -lt 429){
  $finish=NextWaveEnd $selftestOffset 429 100 30
  if($finish -le $selftestOffset -or $finish-$selftestOffset -gt 30){
   throw 'NO11_DAILY_GROUP_COVERAGE_SELFTEST_FAILED'
  }
  $selftestSizes+=@($finish-$selftestOffset)
  $selftestOffset=$finish
 }
 if($selftestOffset -ne 429 -or ($selftestSizes|Measure-Object -Sum).Sum -ne 429){
  throw 'NO11_DAILY_GROUP_COVERAGE_SELFTEST_FAILED'
 }
 Write-Host 'NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS'
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
 if($FirstBuyFridayLimited){
  if($ConfirmYahooFridayRss -or $CatchUpAsOf){
   throw 'NO11_DAILY_FIRST_BUY_FRIDAY_MODES_CONFLICT'
  }
  $planArgs+=@('--first-buy-friday-limited','true')
 }
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
  $ceiling=SafePhysicalBatch $existing $BatchSize
  $physical=if($AutoMaxThroughput){[Math]::Min(5,$ceiling)}else{$ceiling}
  $fullWaves=0
  Write-Host ('NO11_DAILY_BATCH_POLICY=GROUP_{0}|PHYSICAL_MAX_{1}|ORIGINAL_CHARTS_{2}|RESERVE_3|LIMIT_50' -f $GroupSize,$ceiling,$existing)
  if($AutoMaxThroughput){
   Write-Host ('NO11_DAILY_AUTOMAX=ADAPTIVE_5_TO_{0}|EXCEL_CHART_CAP=50|RESERVED=3|CURRENT_BATCH={1}' -f $ceiling,$physical)
  }
  for($offset=0;$offset -lt $remaining.Count;){
   $waveEnd=NextWaveEnd $offset $remaining.Count $GroupSize $physical
   $batch=@($remaining[$offset..($waveEnd-1)]);$sheets=@();$stage='TEMPORARY_WORKBOOK'
   $waveComBusyBefore=$script:DailyExcelComBusyCount
   $script:DailyExcelOp='TEMP_BOOK_ADD'
   $book=New-ExcelComObjectChecked { $excel.Workbooks.Add() } { $excel.Workbooks.Count } 'WORKBOOK_ADD'
   foreach($symbol in $batch){
    $script:DailyExcelOp='TEMP_SHEET_ADD'
    $ws=New-ExcelComObjectChecked { $book.Worksheets.Add() } { $book.Worksheets.Count } 'SHEET_ADD'
    $sheetName='DAILY_'+$symbol.Replace('.','_')
    $script:DailyExcelOp='TEMP_SHEET_RENAME'
    [void](Invoke-ExcelIdempotent { $ws.Name=$sheetName } 'SHEET_NAME')
    $script:DailyExcelOp='TEMP_SHEET_HEADERS'
    for($j=0;$j -lt 10;$j++){
     [void](Invoke-ExcelIdempotent { $ws.Cells.Item(2,$j+1).Value2=$headers[$j] } 'SHEET_HEADER')
    }
    $formula=New-DailyFormula $symbol
    $script:DailyExcelOp='TEMP_SHEET_RSS_FORMULA'
    [void](Invoke-ExcelIdempotent { $ws.Range('A1').Formula=$formula } 'RSS_FORMULA')
    $sheets+=@($ws)
   }
   $stage='WAIT_FOR_RSS';$script:DailyExcelOp='WAIT_RSS';Start-Sleep -Seconds $WaitSeconds
   $emptyRetry=0
   do{
    $payloads=New-Object System.Collections.ArrayList;$usable=0;$complete=0;$stage='DAILY_CAPTURE'
   for($k=0;$k -lt $batch.Count;$k++){
    $symbol=$batch[$k];$ws=$sheets[$k];$formula=New-DailyFormula $symbol
    $script:DailyExcelOp='CAPTURE_FORMULA_VERIFY'
    if([string](Invoke-ExcelIdempotent { $ws.Range('A1').Formula } 'RSS_FORMULA_VERIFY') -cne $formula){throw 'NO11_DAILY_FORMULA_CHANGED'}
    $script:DailyExcelOp='CAPTURE_RSS_D100_READ'
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
    if($usable -gt 0 -or $emptyRetry -ge 2){break}
    $emptyRetry++
    $extraWait=[Math]::Min(60,$WaitSeconds*(1+$emptyRetry))
    Write-Host ('NO11_DAILY_EMPTY_WAVE_RETRY={0}/2|WAIT_SECONDS={1}|PERSISTED=False' -f $emptyRetry,$extraWait)
    $stage='WAIT_FOR_RSS';Start-Sleep -Seconds $extraWait
   }while($true)
   # Never checkpoint an entirely empty wave, even after retries.
   if($usable -eq 0){throw 'NO11_DAILY_ALL_EMPTY_WAVE_RETRY_AFTER_RECONNECT'}
   $script:DailyExcelOp='SAVE_VERIFIED_WAVE'
   foreach($payload in $payloads){Save-Capture (Join-Path $run 'sources') $payload}
   $script:DailyExcelOp='TEMP_BOOK_CLOSE'
   Close-ExcelTemporaryWorkbook $excel $book
   $script:DailyExcelOp='TEMP_COM_RELEASE'
   foreach($ws in $sheets){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($ws)}
   $sheets=@();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book);$book=$null
   $script:DailyExcelOp='WAVE_COMPLETE'
   # RssChart may still be calculating directly after a workbook closes.
   Start-Sleep -Seconds 2
   Write-Host ('NO11_DAILY_PROGRESS={0}/{1}|WAVE_OBSERVED={2}|WAVE_FULL76={3}' -f ($work.resumed+$waveEnd),$work.plan.symbols.Count,$usable,$complete)
   # Canary runs automatically; avoid collecting thousands of unusable snapshots.
   if($complete -eq 0){throw 'NO11_DAILY_NO_FULL_HISTORY_IN_WAVE_REVIEW_PARTIAL_REPORT'}
   $offset=$waveEnd
   # An RSS partial wave is an observed source gap, NOT a success for its
   # missing symbols. Reduce concurrency for subsequent waves; ramp back up
   # only after repeated fully observed waves.
   if($script:DailyExcelComBusyCount -gt $waveComBusyBefore){
    $fullWaves=0
    $physical=[Math]::Max(1,[int][Math]::Floor($physical/2))
    Write-Host ('NO11_DAILY_BATCH_TUNE=EXCEL_COM_BUSY_REDUCED_TO_{0}|NO_DATA_FABRICATION' -f $physical)
   }elseif($usable -lt $batch.Count){
    $fullWaves=0
    $physical=[Math]::Max(1,[int][Math]::Floor($physical/2))
    Write-Host ('NO11_DAILY_BATCH_TUNE=PARTIAL_REDUCED_TO_{0}|MISSING_NOT_G1_PASS' -f $physical)
   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($AutoMaxThroughput -or $fullWaves -ge 2){
     $physical=if($AutoMaxThroughput){
      NextAutoMaxBatch $physical $ceiling $true
     }else{
      [Math]::Min($ceiling,$physical+5)
     }
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }
   if($offset -eq $remaining.Count -or $offset % $GroupSize -eq 0){
    Write-Host ('NO11_DAILY_GROUP_COMPLETE={0}/{1}|GROUP_SIZE={2}|NEXT_WAVE_AUTO=True' -f ($work.resumed+$offset),$work.plan.symbols.Count,$GroupSize)
   }
  }
 }
}catch{
 $failed=$true
 $errorRecord=$_
 $reason=$errorRecord.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_DAILY_COM_OR_IO_FAILURE'}
 # Diagnostic only: no error message, file path, symbol or account info in logs.
 $exceptionType=($errorRecord.Exception.GetType().Name -replace '[^A-Za-z0-9]','_')
 $inner=$errorRecord.Exception.InnerException
 $innerType=if($null -eq $inner){'NONE'}else{($inner.GetType().Name -replace '[^A-Za-z0-9]','_')}
 $innerHr=if($null -eq $inner){0}else{[int]$inner.HResult}
 $line=[int]$errorRecord.InvocationInfo.ScriptLineNumber
 Write-Host ('NO11_DAILY_ERROR_OPERATION='+$script:DailyExcelOp)
 Write-Host ('NO11_DAILY_ERROR_CLASS={0}|INNER={1}|INNER_HRESULT={2}|LINE={3}' -f $exceptionType,$innerType,$innerHr,$line)
 Write-Host ('NO11_DAILY_CAPTURE=BLOCKED|'+$reason);Write-Host ('NO11_DAILY_STAGE='+$stage)
 Write-Host ('NO11_DAILY_HRESULT='+$errorRecord.Exception.HResult)
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
if($FirstBuyFridayLimited){$reportArgs+=@('--first-buy-friday-limited','true')}
if(-not [string]::IsNullOrWhiteSpace($PinsFile)){$reportArgs+=@('--pins-file',$PinsFile)}
$output=@(& node $tool @reportArgs)
$reportExit=$LASTEXITCODE
$output|ForEach-Object {Write-Host $_}
if($failed -or $reportExit -ne 0){exit 2}
if(-not [string]::IsNullOrWhiteSpace($CatchUpAsOf)){
 Write-Host 'NO11_WEEKLY_DAILY_CAPTURE=HISTORICAL_ASOF_WITH_REAL_CURRENT_RECEIPT'
}
if($FirstBuyFridayLimited){
 Write-Host 'NO11_FIRST_BUY_FRIDAY_SCOPE=LOCKED_ORIGINAL_WEEKLY_POOL_ONLY'
 Write-Host 'NO11_FIRST_BUY_FRIDAY_NOT_A_TRADING_PERMISSION=True'
}
Write-Host 'NO11_WEEKLY_DAILY_REFRESH=COMPLETE_NOT_FULL_UNIVERSE'
Write-Host 'ORDER_TRANSMISSION=False'
exit 0
