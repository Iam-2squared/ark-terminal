# No.1.1 next input step: RssChart 1M/5M from the already RSS-enabled
# Excel instance containing the user's original account workbook.
# ONLY an unsaved temporary workbook is created/edited/closed. No order.
param([switch]$OfflineSelfTest,[int]$WaitSeconds=15,[int]$OneMinuteBars=300,[int]$FiveMinuteBars=100)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if($OneMinuteBars -lt 20 -or $OneMinuteBars -gt 3000 -or
   $FiveMinuteBars -lt 20 -or $FiveMinuteBars -gt 3000 -or
   $WaitSeconds -lt 3 -or $WaitSeconds -gt 60){
 throw 'NO11_CHART_PROBE_ARGUMENTS_INVALID'
}
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
$symbol='7203.T'
if($OfflineSelfTest){
 $a=('=RssChart($A$2:$J$2,"{0}","1M",{1})' -f $symbol,$OneMinuteBars)
 $b=('=RssChart($A$2:$J$2,"{0}","5M",{1})' -f $symbol,$FiveMinuteBars)
 if($headers.Count -ne 10 -or $a -cne ('=RssChart($A$2:$J$2,"7203.T","1M",{0})' -f $OneMinuteBars) -or
   $b -cne ('=RssChart($A$2:$J$2,"7203.T","5M",{0})' -f $FiveMinuteBars)){
  throw 'NO11_CHART_FORMULA_SELFTEST_FAILED'
 }
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
  Where-Object {$_.MainWindowTitle -like 'Ark_No11_MSII_RSS*' -and
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
 foreach($test in @(
  @{period='1M';count=$OneMinuteBars},
  @{period='5M';count=$FiveMinuteBars}
 )){
  # Same temporary sheet; no account/market workbook cell is written.
  $sheet.Range('A1').Formula=('=RssChart($A$2:$J$2,"7203.T","{0}",{1})' -f $test.period,$test.count)
  Start-Sleep -Seconds $WaitSeconds
  $values=$sheet.Range(('A3:J{0}' -f (2+$test.count))).Value2
  $numeric=0;$nonEmpty=0
  if($values -is [array] -and $values.Rank -eq 2){
   $r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
   for($r=$r0;$r -lt ($r0+$test.count);$r++){
    $v=$values.GetValue($r,$c0+8)
    if($null -ne $v -and [string]$v -ne ''){$nonEmpty++}
    if($v -is [ValueType] -and [double]$v -gt 0){$numeric++}
   }
  }
  Write-Host ('NO11_CHART_{0}_NUMERIC_CLOSE_ROWS={1}' -f $test.period,$numeric)
  Write-Host ('NO11_CHART_{0}_NONEMPTY_CLOSE_ROWS={1}' -f $test.period,$nonEmpty)
  if($numeric -eq 0){throw ('NO11_CHART_'+$test.period+'_NO_NUMERIC_ROWS')}
 }
 Write-Host 'NO11_CHART_SOURCE=OBSERVED_READ_ONLY'
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
