# Ark No.1.1 continuous 1M chart and cumulative market observation, READ ONLY.
# Builds one UNSAVED temporary book. Original two Ark workbooks are never changed.
param(
 [switch]$OfflineSelfTest,[string]$RunDir,[string]$PinsFile,
 [ValidateRange(2,12)][int]$Samples=4,
 [ValidateRange(50,150)][int]$HistoryBars=120,
 [ValidateRange(5,60)][int]$WarmupSeconds=20
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$export=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\no11_export_chart50_prescreen.mjs'
$fields=@(
 (-join [char[]]@(0x73fe,0x5728,0x65e5,0x4ed8)),
 (-join [char[]]@(0x51fa,0x6765,0x9ad8)),
 (-join [char[]]@(0x58f2,0x8cb7,0x4ee3,0x91d1)),
 (-join [char[]]@(0x51fa,0x6765,0x9ad8,0x52a0,0x91cd,0x5e73,0x5747))
)
$headers=@(
 (-join [char[]]@(0x9298,0x67c4,0x540d,0x79f0)),
 (-join [char[]]@(0x5e02,0x5834,0x540d,0x79f0)),
 (-join [char[]]@(0x8db3,0x7a2e)),
 (-join [char[]]@(0x65e5,0x4ed8)),
 (-join [char[]]@(0x6642,0x523b)),
 (-join [char[]]@(0x59cb,0x5024)),
 (-join [char[]]@(0x9ad8,0x5024)),
 (-join [char[]]@(0x5b89,0x5024)),
 (-join [char[]]@(0x7d42,0x5024)),
 (-join [char[]]@(0x51fa,0x6765,0x9ad8))
)
function NowJst{return [datetimeoffset]::UtcNow.ToOffset([timespan]::FromHours(9))}
function Stamp([datetimeoffset]$t){return $t.ToString('yyyy-MM-ddTHH:mm:ss.fffzzz',$ci)}
function ChartFormula([string]$s){
 if($s -cnotmatch '^[0-9A-Z]{4}\.T$'){throw 'NO11_C50_SYMBOL_INVALID'}
 return ('=RssChart($A$2:$J$2,"{0}","1M",{1})' -f $s,$HistoryBars)
}
function MarketFormula([string]$s,[string]$f){
 if($s -cnotmatch '^[0-9A-Z]{4}\.T$' -or $f -cnotin $fields){
  throw 'NO11_C50_MARKET_FORMULA_INVALID'
 }
 return ('=RssMarket("{0}","{1}")' -f $s,$f)
}
function DateToken([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy-MM-dd',$ci)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n)-or [double]::IsInfinity($n)-or
     $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)
 }
 $s=([string]$v).Replace('/','-');$date=[datetime]::MinValue
 if([datetime]::TryParseExact($s,'yyyy-MM-dd',$ci,
     [Globalization.DateTimeStyles]::None,[ref]$date)){
   return $date.ToString('yyyy-MM-dd',$ci)
 }
 return $null
}
function TimeToken([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('HH:mm',$ci)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n)-or [double]::IsInfinity($n)-or $n -lt 0 -or $n -ge 1){
   return $null
  }
  return [datetime]::FromOADate($n).ToString('HH:mm',$ci)
 }
 $s=[string]$v
 if($s -match '^([01]\d|2[0-3]):[0-5]\d(?::00)?$'){return $s.Substring(0,5)}
 return $null
}
function Nonnegative([object]$v){
 if($v -isnot [ValueType]){return $null}
 $n=[double]$v
 if([double]::IsNaN($n)-or [double]::IsInfinity($n)-or $n -lt 0){return $null}
 return $n.ToString('R',$ci)
}
function Positive([object]$v){
 $x=Nonnegative $v
 if($null -eq $x -or [double]$x -le 0){return $null}
 return $x
}
function SaveSnapshot([string]$folder,[object]$payload){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(
  (ConvertTo-Json -InputObject $payload -Depth 8 -Compress)+[char]10)
 $h=[Security.Cryptography.SHA256]::Create()
 try{$digest=([BitConverter]::ToString($h.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}
 finally{$h.Dispose()}
 $file=Join-Path $folder ('snapshot-'+$digest+'.json')
 $f=[IO.File]::Open($file,[IO.FileMode]::CreateNew,
   [IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}
 finally{$f.Dispose()}
 return $file
}
if($OfflineSelfTest){
 if($headers.Count -ne 10 -or $fields.Count -ne 4 -or
    (ChartFormula '7203.T') -cne ('=RssChart($A$2:$J$2,"7203.T","1M",{0})' -f $HistoryBars) -or
    (MarketFormula '7203.T' $fields[2]) -cne ('=RssMarket("7203.T","'+$fields[2]+'")') -or
    (TimeToken ([double](9*3600+30*60)/86400)) -cne '09:30'){
  throw 'NO11_C50_OFFLINE_SELFTEST_FAILED'
 }
 $reject=$false
 try{[void](ChartFormula '7203.T");BAD(')}catch{$reject=$true}
 if(-not $reject){throw 'NO11_C50_INJECTION_CHECK_FAILED'}
 Write-Host 'NO11_C50_CONTINUOUS_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_C50_BROKER_ACCESS=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if([string]::IsNullOrWhiteSpace($RunDir)){
 $RunDir=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d'
}
if(-not [IO.Path]::IsPathRooted($RunDir) -or
   -not (Test-Path -LiteralPath $RunDir -PathType Container)){
 throw 'NO11_C50_PRIVATE_RUN_REQUIRED'
}
$now=NowJst;$session=$now.ToString('yyyy-MM-dd',$ci)
if($now.ToString('HH:mm:ss',$ci) -lt '09:00:00' -or
   $now.ToString('HH:mm:ss',$ci) -gt '15:20:00'){
 throw 'NO11_C50_MARKET_SESSION_ONLY'
}
$calendar='import {isJpxCashTradingDay} from "./research/no12-prebuy-causal-runtime-20261011/runtime/jpx_cash_calendar_2026_2027.mjs";console.log(isJpxCashTradingDay(process.argv[1])?"YES":"NO")'
Push-Location $repo
try{$isDay=@(& node --input-type=module -e $calendar $session)}
finally{Pop-Location}
if($LASTEXITCODE -ne 0 -or $isDay.Count -ne 1 -or $isDay[0] -cne 'YES'){
 throw 'NO11_C50_NOT_JPX_CASH_TRADING_DAY'
}
$arguments=@('--run',$RunDir,'--session',$session)
if(-not [string]::IsNullOrWhiteSpace($PinsFile)){
 $arguments+=@('--pins-file',$PinsFile)
}
$lines=@(& node $export @arguments)
if($LASTEXITCODE -ne 0){throw 'NO11_C50_PRESCREEN_FAILED'}
$match=@($lines | Where-Object {$_ -like 'NO11_CHART50_RECEIPT=*'})
if($match.Count -ne 1){throw 'NO11_C50_PRESCREEN_RECEIPT_MISSING'}
$planFile=([string]$match[0]).Substring('NO11_CHART50_RECEIPT='.Length)
$receipt=Get-Content -LiteralPath $planFile -Raw -Encoding UTF8 | ConvertFrom-Json
$plan=$receipt.chartPlan
if($receipt.schemaId -cne 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' -or
   $plan.schemaId -cne 'ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1' -or
   $plan.sessionDate -cne $session -or
   $plan.orderTransmission -ne $false -or $plan.productionReady -ne $false){
 throw 'NO11_C50_CHART_PLAN_INVALID'
}
$charts=@($plan.allRequestedChartSymbols)
$symbols=@($plan.selectorInputSymbols)
if($charts.Count -lt 1 -or $symbols.Count -lt 1 -or
   $charts.Count+$plan.occupiedByOtherChartFunctions -gt 50 -or
   @($charts | Select-Object -Unique).Count -ne $charts.Count){
 throw 'NO11_C50_CAPACITY_INVALID'
}
foreach($s in (@($charts)+@($symbols))){
 if($s -cnotmatch '^[0-9A-Z]{4}\.T$'){throw 'NO11_C50_SYMBOL_INVALID'}
}
$folder=Join-Path $RunDir ('chart50-shadow-'+$session+'-'+
 $now.ToString('HHmmss',$ci)+'-'+$PID)
[void][IO.Directory]::CreateDirectory($folder)
$excel=$null;$book=$null;$quote=$null;$sheets=@();$failed=$false;$stage='PRECHECK'
try{
 $tcp=New-Object Net.Sockets.TcpClient;$ui=$false
 try{$tcp.Connect('127.0.0.1',8767);$ui=$tcp.Connected}
 catch [Net.Sockets.SocketException]{}finally{$tcp.Close()}
 if($ui){throw 'NO11_C50_ACCOUNT_UI_MUST_BE_STOPPED'}
 $stage='ATTACH'
 $processes=@(Get-Process EXCEL -ErrorAction Stop | Where-Object {
  $_.MainWindowTitle -like 'Ark_No11_*' -and $_.MainWindowHandle -ne [IntPtr]::Zero
 })
 if($processes.Count -ne 1){throw 'NO11_C50_EXCEL_IDENTITY_NOT_UNIQUE'}
 if(-not ('No11C50Attach' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11C50Attach {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:wsWindows=@()
 $cb=[No11C50Attach+Callback]{
  param($h,$p)
  $n=New-Object Text.StringBuilder 128
  [void][No11C50Attach]::GetClassName($h,$n,128)
  if($n.ToString() -ceq 'EXCEL7'){$script:wsWindows+=@($h)}
  return $true
 }
 [void][No11C50Attach]::EnumChildWindows(
  $processes[0].MainWindowHandle,$cb,[IntPtr]::Zero)
 if($script:wsWindows.Count -ne 1){throw 'NO11_C50_EXCEL7_NOT_UNIQUE'}
 $iid=[guid]'00020400-0000-0000-C000-000000000046';$obj=$null
 $hr=[No11C50Attach]::AccessibleObjectFromWindow(
  $script:wsWindows[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 if($hr -ne 0 -or $null -eq $obj){throw 'NO11_C50_COM_ATTACH_FAILED'}
 $excel=$obj.Application
 if($excel.Workbooks.Count -ne 2){throw 'NO11_C50_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}
 $account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 if($account.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY' -or
    $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){
  throw 'NO11_C50_WORKBOOK_IDENTITY_INVALID'
 }
 $stage='CAPACITY'
 $occupied=0
 foreach($wb in @($account,$market)){
  foreach($ws in $wb.Worksheets){
   $used=$ws.UsedRange
   if([long]$used.CountLarge -gt 100000){throw 'NO11_C50_FORMULA_SCAN_TOO_LARGE'}
   $cells=$null
   try{$cells=$used.SpecialCells(-4123)}
   catch [Runtime.InteropServices.COMException]{
    if($_.Exception.HResult -ne -2146827284){throw}
   }
   if($null -ne $cells){
    foreach($cell in $cells.Cells){
     if([string]$cell.Formula -match '(?i)RssChart\s*\('){$occupied++}
    }
   }
  }
 }
 if($occupied+$charts.Count -gt 50){throw 'NO11_C50_ACTUAL_CHART_CAP_EXCEEDED'}
 $stage='TEMP_WORKBOOK'
 $book=$excel.Workbooks.Add()
 $quote=$book.Worksheets.Item(1)
 $quote.Name='ARK_NO11_CUMULATIVE'
 $grid=[array]::CreateInstance([object],$symbols.Count,5)
 for($i=0;$i -lt $symbols.Count;$i++){
  $grid.SetValue($symbols[$i],$i,0)
  for($j=0;$j -lt 4;$j++){
   $grid.SetValue((MarketFormula $symbols[$i] $fields[$j]),$i,$j+1)
  }
 }
 $quote.Range(('A2:E{0}' -f ($symbols.Count+1))).Formula=$grid
 for($i=0;$i -lt $charts.Count;$i++){
  $ws=$book.Worksheets.Add()
  $ws.Name=('Q{0:D2}' -f ($i+1))
  for($j=0;$j -lt 10;$j++){$ws.Cells.Item(2,$j+1).Value2=$headers[$j]}
  $ws.Range('A1').Formula=(ChartFormula $charts[$i])
  $sheets+=@([pscustomobject]@{symbol=$charts[$i];sheet=$ws})
 }
 $stage='WARMUP';Start-Sleep -Seconds $WarmupSeconds
 $stage='SAMPLES'
 $scan=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
 foreach($symbol in $symbols){[void]$scan.Add($symbol)}
 $totalMarkets=0;$totalBars=0;$invalid=0
 for($k=0;$k -lt $Samples;$k++){
  $t=NowJst
  $due=[datetimeoffset]::new($t.Year,$t.Month,$t.Day,$t.Hour,$t.Minute,8,
    [timespan]::FromHours(9))
  if($due -le $t){$due=$due.AddMinutes(1)}
  if($due.ToString('HH:mm:ss',$ci) -gt '15:25:00'){
   throw 'NO11_C50_TRADING_SESSION_ENDED'
  }
  $delay=[int][math]::Ceiling(($due-$t).TotalMilliseconds)
  if($delay -gt 0){Start-Sleep -Milliseconds $delay}
  $sampleStart=NowJst
  if(($sampleStart-$due).TotalSeconds -gt 15){
   throw 'NO11_C50_SNAPSHOT_OVERRUN'
  }
  $values=$quote.Range(('A2:E{0}' -f ($symbols.Count+1))).Value2
  $marketSeen=NowJst
  if($values -isnot [array] -or $values.Rank -ne 2){
   throw 'NO11_C50_MARKET_READ_INVALID'
  }
  $mi=New-Object System.Collections.ArrayList
  $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
  for($j=0;$j -lt $symbols.Count;$j++){
   $row=$r0+$j;$symbol=$symbols[$j]
   if([string]$values.GetValue($row,$c0) -cne $symbol){
    throw 'NO11_C50_MARKET_SYMBOL_CHANGED'
   }
   [void]$mi.Add([ordered]@{
    symbol=$symbol;marketDate=(DateToken $values.GetValue($row,$c0+1));
    cumulativeVolumeRaw=(Nonnegative $values.GetValue($row,$c0+2));
    cumulativeTurnoverRaw=(Nonnegative $values.GetValue($row,$c0+3));
    vendorVolumeWeightedAverage=(Positive $values.GetValue($row,$c0+4))
   })
  }
  $rrs=New-Object System.Collections.ArrayList
  foreach($item in $sheets){
   if(-not $scan.Contains([string]$item.symbol)){continue}
   $series=$item.sheet.Range(('A3:J{0}' -f ($HistoryBars+2))).Value2
   $chartSeen=NowJst
   if($series -isnot [array] -or $series.Rank -ne 2){$invalid++;continue}
   $q0=$series.GetLowerBound(0);$x0=$series.GetLowerBound(1)
   for($z=0;$z -lt $HistoryBars;$z++){
    $pos=$q0+$z;$date=DateToken $series.GetValue($pos,$x0+3)
    if($date -cne $session){continue}
    $time=TimeToken $series.GetValue($pos,$x0+4)
    if($null -eq $time){$invalid++;continue}
    $start=[datetimeoffset]::MinValue
    $value=$date+'T'+$time+':00+09:00'
    if(-not [datetimeoffset]::TryParseExact($value,
      'yyyy-MM-ddTHH:mm:sszzz',$ci,
      [Globalization.DateTimeStyles]::None,[ref]$start)){
      $invalid++;continue
    }
    if($start.AddMinutes(1) -gt $chartSeen){continue}
    $nums=@();for($p=5;$p -le 9;$p++){$nums+=@($series.GetValue($pos,$x0+$p))}
    if(@($nums | Where-Object {$_ -isnot [ValueType]}).Count -gt 0){
     $invalid++;continue
    }
    $O=[double]$nums[0];$H=[double]$nums[1];$L=[double]$nums[2]
    $C=[double]$nums[3];$V=[double]$nums[4]
    if($O -le 0 -or $C -le 0 -or $H -lt [math]::Max($O,$C) -or
       $L -le 0 -or $L -gt [math]::Min($O,$C) -or
       $V -lt 0 -or $V -ne [math]::Floor($V)){
      $invalid++;continue
    }
    [void]$rrs.Add([ordered]@{
      Date=$date;Code=$item.symbol;Time=$time;
      O=$O;H=$H;L=$L;C=$C;Vo=[long]$V;
      knownAtJst=(Stamp $chartSeen)
    })
   }
  }
  $payload=[ordered]@{
   schemaId='ARK_NO11_RSS_CHART50_1M_CAPTURE_V1';
   sessionDate=$session;chartPlanSha256=$plan.planSha256;
   selectedSymbols=@($symbols);
   source='RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY';
   marketObservedAtJst=(Stamp $marketSeen);
   observedEndJst=(Stamp (NowJst));
   chartRows=@($rrs.ToArray());
   marketObservations=@($mi.ToArray());
   shadowOnly=$true;productionReady=$false;orderTransmission=$false
  }
  $saved=SaveSnapshot $folder $payload
  $totalMarkets+=$mi.Count;$totalBars+=$rrs.Count
  Write-Host ('NO11_C50_SAMPLE={0}|MARKET={1}|CHART_ROWS={2}' -f
    ($k+1),$mi.Count,$rrs.Count)
 }
 Write-Host ('NO11_C50_CAPTURE=READ_ONLY_COMPLETE|MARKET_ROWS={0}|CHART_ROWS={1}|INVALID={2}' -f
  $totalMarkets,$totalBars,$invalid)
 Write-Host ('NO11_C50_PRIVATE_FOLDER='+$folder)
 Write-Host ('NO11_C50_PRIVATE_CHART_PLAN='+$planFile)
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $failed=$true;$reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_C50_COM_OR_IO_FAILURE'}
 Write-Host ('NO11_C50_CAPTURE=BLOCKED|'+$reason)
 Write-Host ('NO11_C50_STAGE='+$stage)
 Write-Host 'ORDER_TRANSMISSION=False'
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 foreach($item in $sheets){
  try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($item.sheet)}catch{}
 }
 if($null -ne $quote){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($quote)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
if($failed){exit 2}
exit 0
