# No.1.2 separate, unsaved Excel RssChart 5M local diagnostic only.
# Never run concurrently with No.1.1 UI2 30sec account reader.
# Creates ONE TEMPORARY unsaved workbook, then closes it with SaveChanges=$false.
# No personal account workbook, no order RSS function, no safety reset.
param([switch]$OfflineSelfTest,[int]$WaitSeconds=12)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$symbol='7203.T' # PUBLIC fixed sample ONLY; never user's external/managed symbol.
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
$formula=('=RssChart($A$2:$J$2,"{0}","5M",20)' -f $symbol)
if($OfflineSelfTest){
 if($headers.Count -ne 10 -or
    $formula -cne '=RssChart($A$2:$J$2,"7203.T","5M",20)'){
   throw 'NO12_RSS_MARKET_FORMULA_OFFLINE_INVALID'
 }
 Write-Host 'NO12_RSS_CHART_FORMULA_SELFTEST_PASS=True'
 Write-Host 'NO12_MARKET_PROBE_BROKER_ACCESS=False'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
if($WaitSeconds -lt 2 -or $WaitSeconds -gt 60){throw 'NO12_WAIT_SECONDS_OUT_OF_RANGE'}
$excel=$null
$book=$null
$sheet=$null
$created=$false
try{
 # Do not perturb No.1.1's single-workbook account poll. The user must stop
 # that UI and close its workbook before a separate market probe can run.
 $connected=$false
 $tcp=New-Object System.Net.Sockets.TcpClient
 try{$tcp.Connect('127.0.0.1',8767);$connected=$tcp.Connected}
 catch [System.Net.Sockets.SocketException]{$connected=$false}
 finally{$tcp.Close()}
 if($connected){throw 'NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST'}
 try{$excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')}
 catch{$excel=$null}
 if($null -ne $excel){
   if([int]$excel.Workbooks.Count -ne 0){
      throw 'EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST'
   }
 }else{
   $excel=New-Object -ComObject Excel.Application
   $created=$true
 }
 $excel.Visible=$true
 $book=$excel.Workbooks.Add()
 $sheet=$book.Worksheets.Item(1)
 $sheet.Name='ARK_NO12_MARKET_READONLY'
 for($i=0;$i -lt $headers.Count;$i++){
    $sheet.Cells.Item(2,$i+1).Value2=$headers[$i]
 }
 # The ONLY RSS UDF inserted in the ephemeral workbook is market chart READ.
 $sheet.Range('A1').Formula=$formula
 Start-Sleep -Seconds $WaitSeconds
 $values=$sheet.Range('A3:J22').Value2
 $nonEmpty=0
 $numericOHLC=0
 if($values -is [array] -and $values.Rank -eq 2){
    $r0=$values.GetLowerBound(0)
    $c0=$values.GetLowerBound(1)
    for($r=$r0;$r -lt ($r0+20);$r++){
       $date=$values.GetValue($r,$c0+3)
       $clock=$values.GetValue($r,$c0+4)
       $close=$values.GetValue($r,$c0+8)
       if($null -ne $date -or $null -ne $clock -or $null -ne $close){
          $nonEmpty++
          if($close -is [ValueType] -and
             [double]$close -gt 0){$numericOHLC++}
       }
    }
 }
 Write-Host 'NO12_RSS_MARKET_READ_ONLY_PROBE=True'
 Write-Host ('NO12_RSS_CHART_ROWS_PRESENT={0}' -f $nonEmpty)
 Write-Host ('NO12_RSS_CHART_NUMERIC_CLOSE_ROWS={0}' -f $numericOHLC)
 Write-Host ('NO12_RSS_CHART_RESULT={0}' -f $(if($numericOHLC -gt 0){'OBSERVED_OFFLINE_SOURCE_ONLY'}else{'SOURCE_NOT_VERIFIED'}))
 Write-Host 'ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False'
 Write-Host 'NO12_NATIVE_SELECTOR_OR_STATE9_CONNECTED=False'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 # Broker symbol, account, private paths, cell data and any COM exception are not printed.
 Write-Host 'NO12_RSS_MARKET_PROBE_BLOCKED=True'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 throw 'NO12_MARKET_PROBE_STOPPED_SAFELY'
}finally{
 if($null -ne $book){
   try{$book.Close($false)}catch{}
 }
 if($null -ne $sheet){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){
   if($created){try{$excel.Quit()}catch{}}
   try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}
 }
 [GC]::Collect()
 [GC]::WaitForPendingFinalizers()
}
