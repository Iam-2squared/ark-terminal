# RSS quote-only probe of the original No.1.1 observed daily PASS pool.
# One TEMPORARY UNSAVED workbook, original two Ark workbooks untouched.
# No account values read, no orders, no selector score or fabricated minute Va.
param(
 [switch]$OfflineSelfTest,
 [string]$RunDir,
 [ValidateRange(5,60)][int]$WarmupSeconds=20
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
$daily=Join-Path (Split-Path $PSScriptRoot -Parent) 'tools\no11_export_observed_pass_watch_mask.mjs'
$rootRepo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$fields=@(
 (-join [char[]]@(0x73fe,0x5728,0x65e5,0x4ed8)),
 (-join [char[]]@(0x73fe,0x5728,0x5024)),
 (-join [char[]]@(0x73fe,0x5728,0x5024,0x8a73,0x7d30,0x6642,0x523b))
)
function QuoteFormula([string]$symbol,[string]$field) {
 if($symbol -cnotmatch '^[0-9A-Z]{4}\.T$' -or $field -cnotin $fields) {
  throw 'NO11_QWATCH_INVALID_FORMULA_INPUT'
 }
 return ('=RssMarket("{0}","{1}")' -f $symbol,$field)
}
function NowJst {
 return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))
}
function DateToken([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('yyyy-MM-dd',$ci)}
 if($value -is [ValueType]){
  $v=[double]$value
  if([double]::IsNaN($v)-or [double]::IsInfinity($v)-or $v -lt 30000 -or $v -gt 80000){return $null}
  return [datetime]::FromOADate($v).ToString('yyyy-MM-dd',$ci)
 }
 $s=([string]$value).Replace('/','-');$dt=[datetime]::MinValue
 if([datetime]::TryParseExact($s,'yyyy-MM-dd',$ci,[Globalization.DateTimeStyles]::None,[ref]$dt)){
  return $dt.ToString('yyyy-MM-dd',$ci)
 }
 return $null
}
function ClockToken([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('HH:mm:ss',$ci)}
 if($value -is [ValueType]){
  $v=[double]$value
  if([double]::IsNaN($v)-or [double]::IsInfinity($v)){return $null}
  if($v -ge 30000 -and $v -le 80000){$v=$v-[math]::Floor($v)}
  if($v -lt 0 -or $v -ge 1){return $null}
  return [datetime]::FromOADate($v).ToString('HH:mm:ss',$ci)
 }
 $s=[string]$value
 if($s -match '^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$'){return $s}
 return $null
}
function NumberToken([object]$value){
 if($value -isnot [ValueType]){return $null}
 $n=[double]$value
 if([double]::IsNaN($n)-or [double]::IsInfinity($n)-or $n -le 0){return $null}
 return $n.ToString('R',$ci)
}
function SaveImmutable([string]$directory,[object]$payload){
 [void][IO.Directory]::CreateDirectory($directory)
 $data=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $payload -Depth 8 -Compress)+[char]10)
 $h=[Security.Cryptography.SHA256]::Create()
 try{$hash=([BitConverter]::ToString($h.ComputeHash($data))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
 $final=Join-Path $directory ('no11-quote-observed-'+$hash.Substring(0,16)+'.json')
 $stream=[IO.File]::Open($final,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($data,0,$data.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 return $final
}
if($OfflineSelfTest){
 $f=QuoteFormula '7203.T' $fields[2]
 if($f -cne '=RssMarket("7203.T","'+$fields[2]+'")'){throw 'NO11_QWATCH_OFFLINE_FORMULA_MISMATCH'}
 $bad=$false;try{[void](QuoteFormula '7203.T");BAD(' $fields[1])}catch{$bad=$true}
 if(-not $bad){throw 'NO11_QWATCH_OFFLINE_INJECTION_FAILED'}
 $day=DateToken ([datetime]'2026-10-23');$clock=ClockToken ([double](9*3600+30*60+5)/86400)
 if($day -cne '2026-10-23' -or $clock -cne '09:30:05' -or (NumberToken '101') -ne $null){
  throw 'NO11_QWATCH_OFFLINE_PARSER_FAILED'
 }
 Write-Host 'NO11_QWATCH_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_LIVE_DATA_ACCESSED=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if([string]::IsNullOrWhiteSpace($RunDir)){
 $RunDir=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d'
}
if(-not [IO.Path]::IsPathRooted($RunDir)){throw 'NO11_QWATCH_PRIVATE_RUN_REQUIRED'}
if(-not (Test-Path -LiteralPath $RunDir -PathType Container)){throw 'NO11_QWATCH_RUN_MISSING'}
if((Get-Item -LiteralPath $RunDir).Attributes -band [IO.FileAttributes]::ReparsePoint){
 throw 'NO11_QWATCH_REPARSE_RUN_FORBIDDEN'
}
$now=NowJst
if($now.TimeOfDay -lt [timespan]::Parse('09:00:00') -or
   $now.TimeOfDay -gt [timespan]::Parse('15:30:00')){
 throw 'NO11_QWATCH_MARKET_SESSION_ONLY'
}
$planExpression='import {lastCompletedSession,jstNow} from "./research/no12-prebuy-causal-runtime-20261011/runtime/no11_rss_daily_trend_census.mjs";import {isJpxCashTradingDay} from "./research/no12-prebuy-causal-runtime-20261011/runtime/jpx_cash_calendar_2026_2027.mjs";const now=jstNow();if(!isJpxCashTradingDay(now.slice(0,10)))throw Error("NO11_QWATCH_NOT_CASH_TRADING_DAY");console.log(lastCompletedSession(now));'
Push-Location $rootRepo
try{$expectedPrior=[string](& node --input-type=module -e $planExpression)}
finally{Pop-Location}
if($LASTEXITCODE -ne 0){throw 'NO11_QWATCH_CALENDAR_FAILED'}
$maskOutput=@(& node $daily --run $RunDir)
if($LASTEXITCODE -ne 0){throw 'NO11_QWATCH_OBSERVED_PASS_EXPORT_FAILED'}
$maskLine=@($maskOutput | Where-Object {$_ -like 'NO11_DAILY_PASS_WATCH_FILE=*'})
if($maskLine.Count -ne 1){throw 'NO11_QWATCH_MASK_PATH_MISSING'}
$maskPath=([string]$maskLine[0]).Substring('NO11_DAILY_PASS_WATCH_FILE='.Length)
$mask=Get-Content -Raw -LiteralPath $maskPath -Encoding UTF8 | ConvertFrom-Json
if($mask.schemaId -cne 'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1' -or
   $mask.asOfSession -cne $expectedPrior -or
   $mask.shadowOnly -ne $true -or $mask.orderTransmission -ne $false -or
   $mask.productionReady -ne $false -or
   $mask.strictNoUnknownFallback -ne $true){throw 'NO11_QWATCH_STALE_OR_UNCERTIFIED_MASK'}
$symbols=@($mask.observedPassSymbols)
if($symbols.Count -lt 1 -or $symbols.Count -gt 500 -or
   @($symbols | Select-Object -Unique).Count -ne $symbols.Count){
 throw 'NO11_QWATCH_RSS_QUOTE_CAP_EXCEEDED'
}
foreach($symbol in $symbols){
 if($symbol -cnotmatch '^[0-9A-Z]{4}\.T$'){throw 'NO11_QWATCH_SYMBOL_INVALID'}
}
$excel=$null;$book=$null;$sheet=$null;$stage='PRECHECK';$failed=$false
try {
 $tcp=New-Object Net.Sockets.TcpClient;$active=$false
 try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}
 catch [Net.Sockets.SocketException]{}finally{$tcp.Close()}
 if($active){throw 'NO11_QWATCH_ACCOUNT_UI_MUST_BE_STOPPED'}
 $stage='EXCEL_WINDOW'
 $processes=@(Get-Process EXCEL -ErrorAction Stop | Where-Object {
  $_.MainWindowTitle -like 'Ark_No11_*' -and $_.MainWindowHandle -ne [IntPtr]::Zero
 })
 if($processes.Count -ne 1){throw 'NO11_QWATCH_EXCEL_IDENTITY_NOT_UNIQUE'}
 if(-not ('No11QuoteWatchWindow' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11QuoteWatchWindow {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:windows=@()
 $callback=[No11QuoteWatchWindow+Callback]{
  param($h,$p)
  $text=New-Object Text.StringBuilder 128
  [void][No11QuoteWatchWindow]::GetClassName($h,$text,128)
  if($text.ToString() -ceq 'EXCEL7'){$script:windows+=@($h)}
  return $true
 }
 [void][No11QuoteWatchWindow]::EnumChildWindows(
   $processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 if($script:windows.Count -ne 1){throw 'NO11_QWATCH_EXCEL7_NOT_UNIQUE'}
 $iid=[guid]'00020400-0000-0000-C000-000000000046';$obj=$null
 $hr=[No11QuoteWatchWindow]::AccessibleObjectFromWindow(
   $script:windows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 if($hr -ne 0 -or $null -eq $obj){throw 'NO11_QWATCH_COM_ATTACH_FAILED'}
 $stage='EXCEL_ATTACHED'
 $excel=$obj.Application
 if($excel.Workbooks.Count -ne 2){throw 'NO11_QWATCH_TWO_ORIGINAL_BOOKS_REQUIRED'}
 $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 if($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY' -or
    $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){
  throw 'NO11_QWATCH_ORIGINAL_WORKBOOK_IDENTITY_INVALID'
 }
 $stage='RSS_CAPACITY'
 # Count unique quoted symbols, not formula cells, to avoid three-field overcount.
 # Unknown/dynamic formula codes each reserve one conservative extra slot.
 # Account cell VALUES are never read.
 $existingSymbols=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
 $opaque=0
 foreach($wb in @($account,$market)){
  foreach($ws in $wb.Worksheets){
   $used=$ws.UsedRange
   if([long]$used.CountLarge -gt 100000){throw 'NO11_QWATCH_CAPACITY_SCAN_TOO_LARGE'}
   $cells=$null
   try{$cells=$used.SpecialCells(-4123)}
   catch [Runtime.InteropServices.COMException]{
    if($_.Exception.HResult -ne -2146827284){throw}
   }
   if($null -ne $cells){
    foreach($cell in $cells.Cells){
     $formula=[string]$cell.Formula
     if($formula -match '(?i)RssMarket\s*\('){
      if($formula -match '(?i)RssMarket\s*\(\s*"([0-9A-Z]{4}\.T)"\s*,'){
       [void]$existingSymbols.Add($Matches[1])
      }else{$opaque++}
     }
    }
   }
  }
 }
 $existing=0
 foreach($sym in $existingSymbols){if($sym -notin $symbols){$existing++}}
 $existing+=$opaque
 if($existing+$symbols.Count -gt 500){throw 'NO11_QWATCH_EXISTING_MARKET_LIMIT'}
 $stage='TEMP_WORKBOOK'
 $book=$excel.Workbooks.Add()
 $sheet=$book.Worksheets.Item(1)
 $sheet.Name='ARK_NO11_PASS_QUOTES'
 $sheet.Cells.Item(1,1).Value2='PUBLIC_SYMBOL'
 for($j=0;$j -lt $fields.Count;$j++){$sheet.Cells.Item(1,$j+2).Value2=('FIELD_'+$j)}
 # Populate 348x4 worksheet entries with ONE bulk COM assignment, not
 # 1,000+ individual COM writes. This also reduces RSS-startup lag/overhead.
 $grid=[Array]::CreateInstance([object],$symbols.Count,4)
 for($i=0;$i -lt $symbols.Count;$i++){
  $symbol=$symbols[$i]
  $grid.SetValue($symbol,$i,0)
  for($j=0;$j -lt $fields.Count;$j++){
   $grid.SetValue((QuoteFormula $symbol $fields[$j]),$i,$j+1)
  }
 }
 $sheet.Range(('A2:D{0}' -f ($symbols.Count+1))).Formula=$grid
 $stage='RSS_WARMUP'
 Start-Sleep -Seconds $WarmupSeconds
 $stage='CAPTURE_QUOTES'
 $start=NowJst
 $values=$sheet.Range(('A2:D{0}' -f ($symbols.Count+1))).Value2
 $end=NowJst
 if($values -isnot [array] -or $values.Rank -ne 2){throw 'NO11_QWATCH_EXCEL_VALUES_INVALID'}
 $records=New-Object System.Collections.ArrayList
 $validQuotes=0;$freshQuotes=0
 $i0=$values.GetLowerBound(0);$j0=$values.GetLowerBound(1)
 for($i=0;$i -lt $symbols.Count;$i++){
  $row=$i0+$i;$symbol=$symbols[$i]
  $readSymbol=[string]$values.GetValue($row,$j0)
  if($readSymbol -cne $symbol){throw 'NO11_QWATCH_EXCEL_ROW_IDENTITY_CHANGED'}
  $day=DateToken $values.GetValue($row,$j0+1)
  $price=NumberToken $values.GetValue($row,$j0+2)
  $clock=ClockToken $values.GetValue($row,$j0+3)
  $age=$null;$fresh=$false
  if($null -ne $day -and $null -ne $clock -and $null -ne $price){
   $validQuotes++
   $source=[datetimeoffset]::MinValue
   $stamp=$day+'T'+$clock+'+09:00'
   if([datetimeoffset]::TryParseExact($stamp,'yyyy-MM-ddTHH:mm:sszzz',
      $ci,[Globalization.DateTimeStyles]::None,[ref]$source)){
    $age=[Math]::Round(($end-$source).TotalSeconds,3)
    if($age -ge 0 -and $age -le 30 -and $day -ceq $end.ToString('yyyy-MM-dd',$ci)){
     $fresh=$true;$freshQuotes++
    }
   }
  }
  [void]$records.Add([ordered]@{
   symbol=$symbol;marketDate=$day;lastPrice=$price;marketClock=$clock;
   ageAtReadEndSeconds=$age;observedFresh30s=$fresh
  })
 }
 $stage='PERSIST_READONLY'
 $payload=[ordered]@{
  schemaId='ARK_NO11_RSS_OBSERVED_PASS_QUOTES_V1';
  asOfSession=$mask.asOfSession;planId=$mask.planId;
  sourceManifestSha256=$mask.sourceManifestSha256;
  observedStartJst=$start.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci);
  observedEndJst=$end.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci);
  requestedSymbols=$symbols.Count;quoteValid=$validQuotes;
  quoteFresh30Seconds=$freshQuotes;
  quoteMissingOrMalformed=$symbols.Count-$validQuotes;
  rssMarketExistingFormulaUpperBound=$existing;
  quoteRows=@($records.ToArray());
  scanReadAtomic=false;brokerDeliveryTimestampCertified=false;
  cumulativeTurnoverVaCertified=false;marketBreadthCertified=false;
  originalSelectorNativeConnected=false;
  dailyPriceBasisCertified=false;marketRightsCertified=false;
  shadowOnly=$true;productionReady=$false;orderTransmission=$false
 }
 $report=SaveImmutable (Join-Path $RunDir 'quote-observations') $payload
 Write-Host ('NO11_QWATCH_OBSERVED={0}|VALID={1}|FRESH30S={2}' -f $symbols.Count,$validQuotes,$freshQuotes)
 Write-Host ('NO11_QWATCH_PRIVATE_REPORT='+$report)
 Write-Host 'NO11_SELECTOR_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $failed=$true;$reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_QWATCH_COM_OR_IO_FAILURE'}
 Write-Host ('NO11_QWATCH=BLOCKED|'+$reason)
 Write-Host ('NO11_QWATCH_STAGE='+$stage)
 Write-Host ('NO11_QWATCH_HRESULT='+$_.Exception.HResult)
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 if($null -ne $sheet){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
if($failed){exit 2}
exit 0
