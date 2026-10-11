# No.1.2 separate, unsaved Excel RssChart 5M local diagnostic only.
# Never run concurrently with No.1.1 UI2 30sec account reader.
# Creates ONE TEMPORARY unsaved workbook, then closes it with SaveChanges=$false.
# No personal account workbook, no order RSS function, no safety reset.
param([switch]$OfflineSelfTest,[int]$WaitSeconds=12,[int]$HistoryBars=500)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$symbol='7203.T' # PUBLIC fixed sample ONLY; never user's external/managed symbol.
$headers=@('銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高')
$formula=('=RssChart($A$2:$J$2,"{0}","5M",{1})' -f $symbol,$HistoryBars)
if($HistoryBars -lt 20 -or $HistoryBars -gt 3000){throw 'NO12_RSS_HISTORY_BAR_REQUEST_OUT_OF_RANGE'}
function Convert-No12VendorDate([object]$value) {
 if($null -eq $value) { return $null }
 if($value -is [datetime]) { return $value.ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture) }
 if($value -is [ValueType]) {
  $n=[double]$value
  if($n -lt 30000 -or $n -gt 80000) { return $null }
  return [datetime]::FromOADate($n).ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$value
 if($s -match '^\d{4}[/\-]\d\d[/\-]\d\d$') { return $s.Replace('-','/') }
 return $null
}
function Convert-No12VendorTime([object]$value) {
 if($null -eq $value) { return $null }
 if($value -is [datetime]) { return $value.ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture) }
 if($value -is [ValueType]) {
  $n=[double]$value
  if($n -lt 0 -or $n -ge 1) { return $null }
  return [datetime]::FromOADate($n).ToString('HH:mm',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$value
 if($s -match '^\d\d:\d\d(?::00)?$') { return $s.Substring(0,5) }
 return $null
}

if($OfflineSelfTest){
 if($headers.Count -ne 10 -or
    $formula -cne ('=RssChart($A$2:$J$2,"7203.T","5M",{0})' -f $HistoryBars)){
   throw 'NO12_RSS_MARKET_FORMULA_OFFLINE_INVALID'
 }
 $sample=[datetime]::new(2026,10,13,9,30,0)
 if((Convert-No12VendorDate $sample.ToOADate()) -cne '2026/10/13' -or
    (Convert-No12VendorTime ($sample.ToOADate() - [math]::Floor($sample.ToOADate()))) -cne '09:30') {
   throw 'NO12_RSS_EXCEL_OADATE_SELFTEST_FAILED'
 }
 Write-Host ('NO12_RSS_HISTORY_BARS_REQUESTED={0}' -f $HistoryBars)
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
 $lastRow=2+$HistoryBars
 $values=$sheet.Range(('A3:J{0}' -f $lastRow)).Value2
 $nonEmpty=0
 $numericOHLC=0
 $parsedRows=New-Object System.Collections.ArrayList
 if($values -is [array] -and $values.Rank -eq 2){
    $r0=$values.GetLowerBound(0)
    $c0=$values.GetLowerBound(1)
    for($r=$r0;$r -lt ($r0+$HistoryBars);$r++){
       $date=$values.GetValue($r,$c0+3)
       $clock=$values.GetValue($r,$c0+4)
       $close=$values.GetValue($r,$c0+8)
       if($null -ne $date -or $null -ne $clock -or $null -ne $close){
          $nonEmpty++
          if($close -is [ValueType] -and [double]$close -gt 0){$numericOHLC++}
          $dateText=Convert-No12VendorDate $date
          $timeText=Convert-No12VendorTime $clock
          $open=$values.GetValue($r,$c0+5)
          $high=$values.GetValue($r,$c0+6)
          $low=$values.GetValue($r,$c0+7)
          $volume=$values.GetValue($r,$c0+9)
          if($null -ne $dateText -and $null -ne $timeText -and
             $open -is [ValueType] -and $high -is [ValueType] -and
             $low -is [ValueType] -and $close -is [ValueType] -and
             $volume -is [ValueType]){
             [void]$parsedRows.Add([ordered]@{
               '銘柄名称'=[string]$values.GetValue($r,$c0)
               '市場名称'=[string]$values.GetValue($r,$c0+1)
               '足種'='5M'
               '日付'=$dateText;'時刻'=$timeText
               '始値'=[double]$open;'高値'=[double]$high
               '安値'=[double]$low;'終値'=[double]$close
               '出来高'=[double]$volume
             })
          }
       }
    }
 }
 $candidateFile=$null
 try {
  if($parsedRows.Count -gt 0) {
    $privateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
    [void](New-Item -ItemType Directory -Force -Path $privateRoot -ErrorAction Stop)
    $candidateFile=Join-Path $privateRoot ('chart-candidate-'+[Guid]::NewGuid().ToString('N')+'.json')
    $capturedAt=(Get-Date).ToUniversalTime().ToString('o')
    $snap=[ordered]@{
      schemaId='ARK_NO12_MSII_RSS_CHART_5M_OBSERVATION_V1'
      sourceFunction='RssChart'
      period='5M'
      evidenceMode='OBSERVED_READ_ONLY'
      symbol=$symbol
      columns=$headers
      capturedAt=$capturedAt
      rows=@($parsedRows.ToArray())
      privateAccountDataIncluded=$false
    }
    $json=ConvertTo-Json -InputObject $snap -Depth 6 -Compress
    [IO.File]::WriteAllText($candidateFile,$json,[Text.UTF8Encoding]::new($false))
    $publisher=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\no12_private_chart_publish.mjs'
    $node=(Get-Command node -CommandType Application -ErrorAction Stop).Source
    & $node $publisher --private-root $privateRoot --candidate $candidateFile | Out-Null
    if($LASTEXITCODE -ne 0){throw 'NO12_MARKET_PRIVATE_RECEIPT_NOT_READY'}
    Write-Host 'NO12_RSS_CHART_PRIVATE_READ_ONLY_RECEIPT=True'
  }
 }finally{
  if($null -ne $candidateFile -and (Test-Path -LiteralPath $candidateFile -PathType Leaf)){
    Remove-Item -LiteralPath $candidateFile -Force -ErrorAction SilentlyContinue
  }
 }
 Write-Host 'NO12_RSS_MARKET_READ_ONLY_PROBE=True'
 Write-Host ('NO12_RSS_HISTORY_BARS_REQUESTED={0}' -f $HistoryBars)
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
