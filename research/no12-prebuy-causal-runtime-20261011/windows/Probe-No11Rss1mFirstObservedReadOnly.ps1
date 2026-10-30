# Ark No.1.1: local PC observation of closed 1M RSS chart (not broker known_at).
# Single public symbol, read-only RSS, unsaved temporary workbook, zero orders.
param([switch]$OfflineSelfTest,[int]$DurationSeconds=150,[int]$PollSeconds=3,
      [int]$HistoryBars=35,[int]$WarmupSeconds=8)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($DurationSeconds -lt 60 -or $DurationSeconds -gt 300 -or
   $PollSeconds -lt 2 -or $PollSeconds -gt 10 -or
   $HistoryBars -lt 20 -or $HistoryBars -gt 100 -or
   $WarmupSeconds -lt 3 -or $WarmupSeconds -gt 30){
 throw 'NO11_FIRST_SEEN_ARGUMENTS_INVALID'
}
$symbol='7203.T'
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
$formula=('=RssChart($A$2:$J$2,"7203.T","1M",{0})' -f $HistoryBars)

function Get-PcJst{
 return [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([datetimeoffset]::UtcNow,'Tokyo Standard Time')
}
function Test-SessionWindow([datetimeoffset]$t){
 $m=$t.Hour*60+$t.Minute
 if($t.DayOfWeek -eq [DayOfWeek]::Saturday -or $t.DayOfWeek -eq [DayOfWeek]::Sunday){return $false}
 return (($m -ge 545 -and $m -le 684) -or ($m -ge 755 -and $m -le 919))
}
function Test-RegularBar([datetimeoffset]$t){
 $m=$t.Hour*60+$t.Minute
 return (($m -ge 540 -and $m -lt 690) -or ($m -ge 750 -and $m -lt 925))
}
function Convert-RssDate([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n) -or $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$v
 if($s -match '^20\d\d[/\-]\d\d[/\-]\d\d$'){return $s.Replace('-','/')}
 return $null
}
function Convert-RssMinute([object]$v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)}
 if($v -is [ValueType]){
  $n=[double]$v
  if([double]::IsNaN($n) -or $n -lt 0 -or $n -ge 1){return $null}
  return [datetime]::FromOADate($n).ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$v
 if($s -match '^([01]\d|2[0-3]):[0-5]\d(?::00)?$'){return $s.Substring(0,5)}
 return $null
}
function Read-ChartRow([object]$values,[int]$r,[int]$c,[datetimeoffset]$observedAt){
 $day=Convert-RssDate $values.GetValue($r,$c+3)
 $clock=Convert-RssMinute $values.GetValue($r,$c+4)
 if($null -eq $day -or $null -eq $clock){return $null}
 $labelTime=[datetimeoffset]::MinValue
 $label=$day.Replace('/','-')+'T'+$clock+':00+09:00'
 if(-not [datetimeoffset]::TryParseExact($label,'yyyy-MM-ddTHH:mm:sszzz',
   [Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,
   [ref]$labelTime)){return $null}
 # Strict conservative interpretation: assume label=start and >=1m has passed.
 $lag=($observedAt-$labelTime.AddMinutes(1)).TotalSeconds
 if($labelTime.Date -ne $observedAt.Date -or -not (Test-RegularBar $labelTime) -or
    $lag -lt 0 -or $lag -gt 90){return $null}
 $nums=@()
 for($i=5;$i -le 8;$i++){
  $x=$values.GetValue($r,$c+$i)
  if($x -isnot [ValueType]){return $null}
  $n=[double]$x
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -le 0){return $null}
  $nums+=@($n)
 }
 $q=$values.GetValue($r,$c+9)
 if($q -isnot [ValueType]){return $null}
 $vol=[double]$q
 if([double]::IsNaN($vol) -or [double]::IsInfinity($vol) -or
    $vol -lt 0 -or $vol -gt 9007199254740991 -or
    $vol -ne [math]::Floor($vol) -or
    $nums[2] -gt [math]::Min($nums[0],$nums[3]) -or
    $nums[1] -lt [math]::Max($nums[0],$nums[3]) -or
    $nums[1] -lt $nums[2]){return $null}
 return [ordered]@{
  label=$label; firstObservedAsClosedAt=$observedAt.ToString('o')
  o=$nums[0];h=$nums[1];l=$nums[2];c=$nums[3];volume=[long]$vol
 }
}
if($OfflineSelfTest){
 if($formula -cne ('=RssChart($A$2:$J$2,"7203.T","1M",{0})' -f $HistoryBars)){
  throw 'NO11_FIRST_SEEN_FORMULA_INVALID'
 }
 $time=[datetimeoffset]::Parse('2026-10-14T09:11:05+09:00')
 if(-not (Test-SessionWindow $time)){throw 'NO11_FIRST_SEEN_WINDOW_SELFTEST_FAILED'}
 $array=[Array]::CreateInstance([object],1,10)
 $array.SetValue('2026/10/14',0,3)
 $array.SetValue('09:10',0,4)
 $array.SetValue([double]100,0,5)
 $array.SetValue([double]102,0,6)
 $array.SetValue([double]99,0,7)
 $array.SetValue([double]101,0,8)
 $array.SetValue([double]300,0,9)
 if($null -eq (Read-ChartRow $array 0 0 $time)){
  throw 'NO11_FIRST_SEEN_CLOSED_ROW_SELFTEST_FAILED'
 }
 $array.SetValue('09:11',0,4)
 if($null -ne (Read-ChartRow $array 0 0 $time)){
  throw 'NO11_FIRST_SEEN_UNCLOSED_ROW_ACCEPTED'
 }
 $array.SetValue('09:05',0,4)
 if($null -ne (Read-ChartRow $array 0 0 $time)){
  throw 'NO11_FIRST_SEEN_STALE_ROW_ACCEPTED'
 }
 Write-Host 'NO11_FIRST_SEEN_OFFLINE_SELFTEST=PASS'
 Write-Host 'NO11_LIVE_DATA_ACCESSED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null;$book=$null;$sheet=$null
try{
 $startedAt=Get-PcJst
 if(-not (Test-SessionWindow $startedAt)){throw 'NO11_ACTIVE_MARKET_WINDOW_REQUIRED'}
 $tcp=New-Object System.Net.Sockets.TcpClient
 $active=$false
 try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}
 catch [System.Net.Sockets.SocketException]{$active=$false}
 finally{$tcp.Close()}
 if($active){throw 'NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST'}
 # Same Windows Excel attachment process as proven RssChart capture.
 $processes=@(Get-Process EXCEL -ErrorAction Stop |
  Where-Object {$_.MainWindowTitle -like 'Ark_No11_*' -and
    $_.MainWindowHandle -ne [IntPtr]::Zero})
 if($processes.Count -ne 1){throw 'NO11_ACCOUNT_EXCEL_NOT_UNIQUE'}
 if(-not ('No11FirstSeenExcelV1' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11FirstSeenExcelV1 {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]
 public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")]
 public static extern int AccessibleObjectFromWindow(
   IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
 }
 $script:excel7=@()
 $callback=[No11FirstSeenExcelV1+Callback]{
  param($h,$ignored)
  $name=New-Object System.Text.StringBuilder 128
  [void][No11FirstSeenExcelV1]::GetClassName($h,$name,128)
  if($name.ToString() -ceq 'EXCEL7'){$script:excel7+=@($h)}
  return $true
 }
 [void][No11FirstSeenExcelV1]::EnumChildWindows(
   $processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 if($script:excel7.Count -ne 1){throw 'NO11_EXCEL7_NOT_UNIQUE'}
 $iid=[Guid]'00020400-0000-0000-C000-000000000046'
 $obj=$null
 $hr=[No11FirstSeenExcelV1]::AccessibleObjectFromWindow(
   $script:excel7[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 if($hr -ne 0 -or $null -eq $obj){throw 'NO11_EXCEL_COM_ATTACH_FAILED'}
 $excel=$obj.Application
 $original=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 if($null -eq $original -or
   $original.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY'){
  throw 'NO11_ACCOUNT_WORKBOOK_INVALID'
 }
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 if($null -eq $market -or
   $market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){
  throw 'NO11_MARKET_WORKBOOK_INVALID'
 }
 $book=$excel.Workbooks.Add()
 $sheet=$book.Worksheets.Item(1)
 $sheet.Name='ARK_FIRST_SEEN_1M'
 for($i=0;$i -lt $headers.Count;$i++){
  $sheet.Cells.Item(2,$i+1).Value2=$headers[$i]
 }
 $sheet.Range('A1').Formula=$formula
 Start-Sleep -Seconds $WarmupSeconds
 $timer=[Diagnostics.Stopwatch]::StartNew()
 $events=New-Object System.Collections.ArrayList
 $revisions=New-Object System.Collections.ArrayList
 $seen=@{}
 $polls=0
 while($timer.Elapsed.TotalSeconds -lt $DurationSeconds){
  if(-not (Test-SessionWindow (Get-PcJst))){break}
  $values=$sheet.Range(('A3:J{0}' -f (2+$HistoryBars))).Value2
  $observedAt=Get-PcJst
  $polls++
  if($values -is [array] -and $values.Rank -eq 2){
   $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
   for($r=$r0;$r -lt $r0+$HistoryBars;$r++){
    $b=Read-ChartRow $values $r $c0 $observedAt
    if($null -eq $b){continue}
    $sig=('{0}|{1}|{2}|{3}|{4}' -f $b.o,$b.h,$b.l,$b.c,$b.volume)
    if(-not $seen.ContainsKey($b.label)){
     $seen[$b.label]=$sig
     [void]$events.Add($b)
    }elseif($seen[$b.label] -cne $sig){
     $seen[$b.label]=$sig
     [void]$revisions.Add([ordered]@{
       label=$b.label; revisedObservedAt=$observedAt.ToString('o')
       kind='RSS_CLOSED_BAR_REVISION';o=$b.o;h=$b.h;l=$b.l;c=$b.c;volume=$b.volume
     })
    }
   }
  }
  if($timer.Elapsed.TotalSeconds -ge $DurationSeconds){break}
  Start-Sleep -Seconds $PollSeconds
 }
 $root=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
 [void][IO.Directory]::CreateDirectory($root)
 $file=Join-Path $root ('first-observed-1m-'+[Guid]::NewGuid().ToString('N')+'.json')
 $receipt=[ordered]@{
  schemaId='ARK_NO11_RSS_1M_LOCAL_CLOSED_OBSERVATION_V1'
  symbol=$symbol;sourceFunction='RssChart';period='1M'
  firstSeenDefinition='LOCAL_PC_FIRST_READ_AFTER_ASSUMED_BAR_CLOSE_NOT_BROKER_KNOWN_AT'
  assumedBarLabel='START_UNCERTIFIED'
  capturedStartedAt=$startedAt.ToString('o')
  capturedEndedAt=(Get-PcJst).ToString('o')
  pollSeconds=$PollSeconds;pollCount=$polls
  events=@($events.ToArray());revisions=@($revisions.ToArray())
  privateAccountDataIncluded=$false;brokerArrivalCertified=$false
  vendorStartLabelCertified=$false;vendorRawDecimalCertified=$false
  nativeState9LiveConnected=$false;productionReady=$false;orderTransmission=$false
 }
 $json=ConvertTo-Json -InputObject $receipt -Depth 8 -Compress
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json+[char]10)
 $stream=$null
 try{
  $stream=[IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  $stream.Write($bytes,0,$bytes.Length)
  $stream.Flush($true)
 }finally{if($null -ne $stream){$stream.Dispose()}}
 Write-Host 'NO11_FIRST_SEEN_STATUS=LOCAL_PC_OBSERVED_NOT_BROKER_CERTIFIED'
 Write-Host ('NO11_FIRST_SEEN_POLLS={0}' -f $polls)
 Write-Host ('NO11_FIRST_SEEN_EVENTS={0}' -f $events.Count)
 Write-Host ('NO11_FIRST_SEEN_REVISIONS={0}' -f $revisions.Count)
 Write-Host ('NO11_FIRST_SEEN_FILE={0}' -f $file)
 Write-Host ('NO11_FIRST_SEEN_SHA256={0}' -f (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant())
 Write-Host 'NO11_NATIVE_STATE9_LIVE_CONNECTED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_FIRST_SEEN_COM_OR_SOURCE_FAILURE'}
 Write-Host ('NO11_FIRST_SEEN_STATUS=BLOCKED REASON='+$reason)
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 if($null -ne $sheet){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
