# No.1.1 next input step: RssChart 1M/5M from the already RSS-enabled
# Excel instance containing the user's original account workbook.
# ONLY an unsaved temporary workbook is created/edited/closed. No order.
param([switch]$OfflineSelfTest,[int]$WaitSeconds=15,[int]$OneMinuteBars=300,[int]$FiveMinuteBars=100,[switch]$SaveEvidence)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OneMinuteBars -lt 20 -or $OneMinuteBars -gt 3000 -or
   $FiveMinuteBars -lt 20 -or $FiveMinuteBars -gt 3000 -or
   $WaitSeconds -lt 3 -or $WaitSeconds -gt 60){
 throw 'NO11_CHART_PROBE_ARGUMENTS_INVALID'
}
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
$symbol='7203.T'
function Convert-No11ChartDate([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)}
 if($value -is [ValueType]){
  $n=[double]$value
  if([double]::IsNaN($n) -or $n -lt 30000 -or $n -gt 80000){return $null}
  return [datetime]::FromOADate($n).ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)
 }
 $str=[string]$value
 if($str -match '^20\d\d/\d\d/\d\d$'){return $str}
 return $null
}
function Convert-No11ChartTime([object]$value){
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)}
 if($value -is [ValueType]){
  $n=[double]$value
  if([double]::IsNaN($n) -or $n -lt 0 -or $n -ge 1){return $null}
  return [datetime]::FromOADate($n).ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)
 }
 $str=[string]$value
 if($str -match '^([01]\d|2[0-3]):[0-5]\d(?::00)?$'){return $str.Substring(0,5)}
 return $null
}
function Test-No11ChartRow([object]$values,[int]$r,[int]$c,[string]$period,[datetimeoffset]$observed){
 $day=Convert-No11ChartDate $values.GetValue($r,$c+3)
 $clock=Convert-No11ChartTime $values.GetValue($r,$c+4)
 if($null -eq $day -or $null -eq $clock){return $null}
 $stamp=[datetimeoffset]::MinValue
 $dayTime=$day.Replace('/','-')+'T'+$clock+':00+09:00'
 if(-not [datetimeoffset]::TryParseExact($dayTime,'yyyy-MM-ddTHH:mm:sszzz',
   [Globalization.CultureInfo]::InvariantCulture,
   [Globalization.DateTimeStyles]::None,[ref]$stamp)){return $null}
 if($stamp -gt $observed){return $null}
 $clockMinutes=([int]$clock.Substring(0,2))*60+[int]$clock.Substring(3,2)
 if(-not (($clockMinutes -ge 540 -and $clockMinutes -le 690) -or
   ($clockMinutes -ge 750 -and $clockMinutes -le 930))){return $null}
 if($period -ceq '5M' -and $clockMinutes%5 -ne 0){return $null}
 $prices=@()
 for($i=5;$i -le 8;$i++){
  $v=$values.GetValue($r,$c+$i)
  if($v -isnot [ValueType]){return $null}
  $n=[double]$v
  if([double]::IsNaN($n) -or [double]::IsInfinity($n) -or $n -le 0){return $null}
  $prices+=@($n)
 }
 $volumeRaw=$values.GetValue($r,$c+9)
 if($volumeRaw -isnot [ValueType]){return $null}
 $volume=[double]$volumeRaw
 if([double]::IsNaN($volume) -or [double]::IsInfinity($volume) -or
   $volume -lt 0 -or $volume -gt 9007199254740991 -or
   $volume -ne [math]::Floor($volume)){return $null}
 if($prices[2] -gt [math]::Min($prices[0],$prices[3]) -or
   $prices[1] -lt [math]::Max($prices[0],$prices[3]) -or
   $prices[1] -lt $prices[2]){return $null}
 return [pscustomobject]@{
  key=$day+'|'+$clock
  time=$stamp
  open=$prices[0];high=$prices[1];low=$prices[2];close=$prices[3];volume=$volume
 }
}
if($OfflineSelfTest){
 $a=('=RssChart($A$2:$J$2,"{0}","1M",{1})' -f $symbol,$OneMinuteBars)
 $b=('=RssChart($A$2:$J$2,"{0}","5M",{1})' -f $symbol,$FiveMinuteBars)
 if($headers.Count -ne 10 -or $a -cne ('=RssChart($A$2:$J$2,"7203.T","1M",{0})' -f $OneMinuteBars) -or
   $b -cne ('=RssChart($A$2:$J$2,"7203.T","5M",{0})' -f $FiveMinuteBars)){
  throw 'NO11_CHART_FORMULA_SELFTEST_FAILED'
 }
 $testValues=[Array]::CreateInstance([object],1,10)
 $testValues.SetValue('2026/10/13',0,3)
 $testValues.SetValue('12:35',0,4)
 $testValues.SetValue([double]100,0,5)
 $testValues.SetValue([double]102,0,6)
 $testValues.SetValue([double]99,0,7)
 $testValues.SetValue([double]101,0,8)
 $testValues.SetValue([double]300,0,9)
 $when=[datetimeoffset]::Parse('2026-10-13T12:36:00+09:00')
 $good=Test-No11ChartRow $testValues 0 0 '1M' $when
 if($null -eq $good -or $good.close -ne 101 -or
   $good.key -cne '2026/10/13|12:35'){
  throw 'NO11_CHART_OHLCV_SELFTEST_FAILED'
 }
 $testValues.SetValue([double]90,0,6)
 if($null -ne (Test-No11ChartRow $testValues 0 0 '1M' $when)){
  throw 'NO11_CHART_OHLCV_BAD_HIGH_ACCEPTED'
 }
 $testValues.SetValue([double]102,0,6)
 $testValues.SetValue('12:36',0,4)
 if($null -ne (Test-No11ChartRow $testValues 0 0 '5M' $when)){
  throw 'NO11_CHART_5M_MISALIGNED_LABEL_ACCEPTED'
 }
 Write-Host 'NO11_CHART_OHLCV_SELFTEST=PASS'
 Write-Host 'NO11_CHART_OFFLINE_SELFTEST=PASS'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if(-not ('No11RssChartWindowV1' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class No11RssChartWindowV1 {
 public delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,Callback cb,IntPtr p);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("oleacc.dll")] public static extern int AccessibleObjectFromWindow(
  IntPtr h,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out object o);
}
'@ -ErrorAction Stop
}
$excel=$null;$book=$null;$sheet=$null
try{
 # A running No.1.1 UI may be polling the account workbook: do not interfere.
 $tcp=New-Object System.Net.Sockets.TcpClient
 $active=$false
 try{$tcp.Connect('127.0.0.1',8767);$active=$tcp.Connected}
 catch [System.Net.Sockets.SocketException]{$active=$false}
 finally{$tcp.Close()}
 if($active){throw 'NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST'}
 $processes=@(Get-Process EXCEL -ErrorAction Stop |
  # The active Excel window title changes between account and market books.
  # Exact workbook identities are verified via COM below before any write.
  Where-Object {$_.MainWindowTitle -like 'Ark_No11_*' -and
    $_.MainWindowHandle -ne [IntPtr]::Zero})
 if($processes.Count -ne 1){throw 'NO11_ACCOUNT_EXCEL_NOT_UNIQUE'}
 $script:excel7=@()
 $callback=[No11RssChartWindowV1+Callback]{
  param($h,$unused)
  $name=New-Object System.Text.StringBuilder 128
  [void][No11RssChartWindowV1]::GetClassName($h,$name,128)
  if($name.ToString() -ceq 'EXCEL7'){$script:excel7+=@($h)}
  return $true
 }
 [void][No11RssChartWindowV1]::EnumChildWindows(
  $processes[0].MainWindowHandle,$callback,[IntPtr]::Zero)
 if($script:excel7.Count -ne 1){throw 'NO11_EXCEL7_NOT_UNIQUE'}
 $iid=[Guid]'00020400-0000-0000-C000-000000000046'
 $obj=$null
 $hr=[No11RssChartWindowV1]::AccessibleObjectFromWindow(
  $script:excel7[0],[uint32]4294967280,[ref]$iid,[ref]$obj)
 if($hr -ne 0 -or $null -eq $obj){throw 'NO11_EXCEL_COM_ATTACH_FAILED'}
 $excel=$obj.Application
 $original=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx')
 if($null -eq $original -or
   $original.Worksheets.Item('ARK_ACCOUNT_READONLY').Name -cne 'ARK_ACCOUNT_READONLY'){
  throw 'NO11_ACCOUNT_WORKBOOK_IDENTITY_INVALID'
 }
 # Never modify the account or saved market workbook.
 $market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')
 if($market.Worksheets.Item('ARK_MARKET_READONLY').Name -cne 'ARK_MARKET_READONLY'){
  throw 'NO11_MARKET_WORKBOOK_IDENTITY_INVALID'
 }
 $book=$excel.Workbooks.Add()
 $sheet=$book.Worksheets.Item(1)
 $sheet.Name='ARK_CHART_DIAGNOSTIC'
 for($i=0;$i -lt $headers.Count;$i++){
  $sheet.Cells.Item(2,$i+1).Value2=$headers[$i]
 }
 $evidence=[ordered]@{
  schemaId='ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1'
  symbol=$symbol
  sourceFunction='RssChart'
  evidenceMode='OBSERVED_READ_ONLY'
  privateAccountDataIncluded=$false
  excelOrderEnabled=$false
  labelSemanticsCertified=$false
  brokerArrivalCertified=$false
  originalNativeState9Certified=$false
  productionReady=$false
  orderTransmission=$false
  periods=[ordered]@{}
 }
 foreach($test in @(
  @{period='1M';count=$OneMinuteBars},
  @{period='5M';count=$FiveMinuteBars}
 )){
  # Same temporary sheet; no account/market workbook cell is written.
  $sheet.Range('A1').Formula=('=RssChart($A$2:$J$2,"7203.T","{0}",{1})' -f $test.period,$test.count)
  Start-Sleep -Seconds $WaitSeconds
  $values=$sheet.Range(('A3:J{0}' -f (2+$test.count))).Value2
  $numeric=0;$nonEmpty=0;$valid=0;$invalid=0;$duplicate=0
  $latest=[datetimeoffset]::MinValue
  $earliest=[datetimeoffset]::MaxValue
  $observed=[datetimeoffset]::Now
  $seen=New-Object 'System.Collections.Generic.HashSet[string]'
  $bars=New-Object System.Collections.ArrayList
  if($values -is [array] -and $values.Rank -eq 2){
   $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
   for($r=$r0;$r -lt ($r0+$test.count);$r++){
    $v=$values.GetValue($r,$c0+8)
    if($null -ne $v -and [string]$v -ne ''){$nonEmpty++}
    if($v -is [ValueType] -and [double]$v -gt 0){
     $numeric++
     $bar=Test-No11ChartRow $values $r $c0 $test.period $observed
     if($null -eq $bar){$invalid++;continue}
     if(-not $seen.Add($bar.key)){$duplicate++;continue}
     $valid++
     [void]$bars.Add([ordered]@{
      label=$bar.time.ToString('yyyy-MM-ddTHH:mm:sszzz')
      open=$bar.open;high=$bar.high;low=$bar.low;close=$bar.close;volume=$bar.volume
     })
     if($bar.time -lt $earliest){$earliest=$bar.time}
     if($bar.time -gt $latest){$latest=$bar.time}
    }
   }
  }
  Write-Host ('NO11_CHART_{0}_NUMERIC_CLOSE_ROWS={1}' -f $test.period,$numeric)
  Write-Host ('NO11_CHART_{0}_NONEMPTY_CLOSE_ROWS={1}' -f $test.period,$nonEmpty)
  Write-Host ('NO11_CHART_{0}_VALID_OHLCV_ROWS={1}' -f $test.period,$valid)
  Write-Host ('NO11_CHART_{0}_INVALID_OHLCV_ROWS={1}' -f $test.period,$invalid)
  Write-Host ('NO11_CHART_{0}_DUPLICATE_BAR_TIMES={1}' -f $test.period,$duplicate)
  if($valid -gt 0){
   Write-Host ('NO11_CHART_{0}_EARLIEST_LABEL={1}' -f $test.period,$earliest.ToString('yyyy-MM-ddTHH:mm:sszzz'))
   Write-Host ('NO11_CHART_{0}_LATEST_LABEL={1}' -f $test.period,$latest.ToString('yyyy-MM-ddTHH:mm:sszzz'))
  }
  if($numeric -eq 0 -or $valid -ne $numeric -or $invalid -gt 0 -or $duplicate -gt 0){
   throw ('NO11_CHART_'+$test.period+'_OHLCV_AUDIT_BLOCKED')
  }
  $evidence.periods[$test.period]=[ordered]@{
   observedAt=$observed.ToString('o')
   requestedBars=[int]$test.count
   validRows=[int]$valid
   rows=@($bars.ToArray())
  }
 }
 if($SaveEvidence){
  # Private, immutable evidence: only public 7203.T OHLCV. Never save Excel.
  $folder=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
  [void][IO.Directory]::CreateDirectory($folder)
  $evidence['capturedAt']=[datetimeoffset]::Now.ToString('o')
  $payload=ConvertTo-Json -InputObject $evidence -Depth 8 -Compress
  $output=Join-Path $folder ('chart-evidence-'+[Guid]::NewGuid().ToString('N')+'.json')
  $stream=$null
  try{
   $stream=[IO.File]::Open($output,[IO.FileMode]::CreateNew,
     [IO.FileAccess]::Write,[IO.FileShare]::None)
   $bytes=[Text.UTF8Encoding]::new($false).GetBytes($payload+"`n")
   $stream.Write($bytes,0,$bytes.Length)
   $stream.Flush($true)
  }catch{
   if($null -ne $stream){$stream.Dispose();$stream=$null}
   if([IO.File]::Exists($output)){[IO.File]::Delete($output)}
   throw 'NO11_CHART_EVIDENCE_WRITE_FAILED'
  }finally{if($null -ne $stream){$stream.Dispose()}}
  Write-Host ('NO11_CHART_EVIDENCE_FILE='+$output)
  Write-Host ('NO11_CHART_EVIDENCE_SHA256='+(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant())
 }
 Write-Host 'NO11_CHART_SOURCE=OBSERVED_READ_ONLY'
 Write-Host 'NO11_CHART_LABEL_START_OR_END_CERTIFIED=False'
 Write-Host 'NO11_CHART_COMPLETED_BARS_CERTIFIED=False'
 Write-Host 'NO11_CHART_MISSING_BARS_CERTIFIED=False'
 Write-Host 'NO11_NATIVE_SELECTOR_CONNECTED=False'
 Write-Host 'NO11_NATIVE_STATE9_CONNECTED=False'
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 Write-Host 'NO11_CHART_PROBE=PASS'
}catch{
 $reason=$_.Exception.Message
 if($reason -notmatch '^NO11_[A-Z0-9_]+$'){$reason='NO11_CHART_COM_OR_SOURCE_FAILURE'}
 Write-Host ('NO11_CHART_PROBE=BLOCKED REASON='+$reason)
 Write-Host 'NO11_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 2
}finally{
 if($null -ne $book){try{$book.Close($false)}catch{}}
 if($null -ne $sheet){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}}
}
