# One public sample ticker; seconds-level RssMarket READ ONLY physical probe.
# Uses one UNSAVED temporary workbook, never user's account workbook or order UDF.
param([switch]$OfflineSelfTest,[int]$Samples=5,[int]$IntervalSeconds=2,[int]$WarmupSeconds=5)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$symbol='7203.T'
$fields=@('現在日付','現在値','現在値詳細時刻','最良売気配値','最良買気配値')
function Convert-No12MarketDate([object]$value) {
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)}
 if($value -is [ValueType]){
   $v=[double]$value
   if($v -lt 30000 -or $v -gt 80000){return $null}
   return [datetime]::FromOADate($v).ToString('yyyy/MM/dd',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$value
 if($s -match '^\d{4}[/\-]\d\d[/\-]\d\d$'){return $s.Replace('-','/')}
 return $null
}
function Convert-No12MarketSeconds([object]$value) {
 if($null -eq $value){return $null}
 if($value -is [datetime]){return $value.ToString('HH:mm:ss',[Globalization.CultureInfo]::InvariantCulture)}
 if($value -is [ValueType]){
   $v=[double]$value
   if($v -lt 0 -or $v -ge 1){return $null}
   return [datetime]::FromOADate($v).ToString('HH:mm:ss',[Globalization.CultureInfo]::InvariantCulture)
 }
 $s=[string]$value
 if($s -match '^\d\d:\d\d:\d\d$'){return $s}
 return $null
}
function Convert-No12OptionalQuote([object]$value) {
 if($null -eq $value){return $null}
 if($value -is [ValueType] -and [double]$value -gt 0){return [double]$value}
 return $null
}
if($Samples -lt 3 -or $Samples -gt 30 -or $IntervalSeconds -lt 1 -or
   $IntervalSeconds -gt 10 -or $WarmupSeconds -lt 2 -or $WarmupSeconds -gt 30){
 throw 'NO12_SECONDS_PROBE_ARGUMENT_OUT_OF_RANGE'
}
if($OfflineSelfTest){
 $formula=('=RssMarket("{0}","{1}")' -f $symbol,'現在値詳細時刻')
 if($formula -cne '=RssMarket("7203.T","現在値詳細時刻")' -or $fields.Count -ne 5){
   throw 'NO12_SECONDS_RSS_FORMULA_INVALID'
 }
 $sample=[datetime]::new(2026,10,13,9,30,15)
 if((Convert-No12MarketDate $sample.ToOADate()) -cne '2026/10/13' -or
    (Convert-No12MarketSeconds ($sample.ToOADate()-[math]::Floor($sample.ToOADate()))) -cne '09:30:15'){
   throw 'NO12_SECONDS_OADATE_SELFTEST_FAILED'
 }
 Write-Host 'NO12_SECONDS_RSS_FORMULA_SELFTEST_PASS=True'
 Write-Host 'NO12_SECONDS_BROKER_ACCESS=False'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 exit 0
}
$excel=$null;$book=$null;$sheet=$null;$created=$false;$candidateFile=$null
try{
 $connected=$false
 $tcp=New-Object System.Net.Sockets.TcpClient
 try{$tcp.Connect('127.0.0.1',8767);$connected=$tcp.Connected}
 catch [System.Net.Sockets.SocketException]{$connected=$false}
 finally{$tcp.Close()}
 if($connected){throw 'NO11_ACCOUNT_UI_MUST_BE_STOPPED_FIRST'}
 try{$excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')}
 catch{$excel=$null}
 if($null -ne $excel){
   if([int]$excel.Workbooks.Count -ne 0){throw 'EXCEL_HAS_EXISTING_WORKBOOK_CLOSE_FIRST'}
 }else{
   $excel=New-Object -ComObject Excel.Application
   $created=$true
 }
 $excel.Visible=$true
 $book=$excel.Workbooks.Add()
 $sheet=$book.Worksheets.Item(1)
 $sheet.Name='ARK_NO12_SECONDS_READONLY'
 for($i=0;$i -lt $fields.Count;$i++){
   $sheet.Cells.Item(1,$i+1).Formula=('=RssMarket("{0}","{1}")' -f $symbol,$fields[$i])
 }
 Start-Sleep -Seconds $WarmupSeconds
 $rows=New-Object System.Collections.ArrayList
 for($n=0;$n -lt $Samples;$n++){
   $dateRaw=$sheet.Cells.Item(1,1).Value2
   $price=$sheet.Cells.Item(1,2).Value2
   $clockRaw=$sheet.Cells.Item(1,3).Value2
   $askRaw=$sheet.Cells.Item(1,4).Value2
   $bidRaw=$sheet.Cells.Item(1,5).Value2
   $date=Convert-No12MarketDate $dateRaw
   $clock=Convert-No12MarketSeconds $clockRaw
   $ask=Convert-No12OptionalQuote $askRaw
   $bid=Convert-No12OptionalQuote $bidRaw
   $sampledAt=(Get-Date).ToUniversalTime().ToString('o')
   if($null -ne $date -and $null -ne $clock -and
      $price -is [ValueType] -and [double]$price -gt 0){
     [void]$rows.Add([ordered]@{
       sampledAt=$sampledAt
       marketDate=$date
       marketClock=$clock
       lastPrice=[double]$price
       bestAsk=$ask
       bestBid=$bid
     })
   }
   if($n -lt $Samples-1){Start-Sleep -Seconds $IntervalSeconds}
 }
 if($rows.Count -lt 3){throw 'NO12_SECONDS_SOURCE_ROWS_INSUFFICIENT'}
 $privateRoot=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12'
 [void](New-Item -ItemType Directory -Force -Path $privateRoot -ErrorAction Stop)
 $candidateFile=Join-Path $privateRoot ('seconds-candidate-'+[Guid]::NewGuid().ToString('N')+'.json')
 $snapshot=[ordered]@{
   schemaId='ARK_NO12_MSII_RSS_MARKET_SECONDS_OBSERVATION_V1'
   sourceFunction='RssMarket'
   evidenceMode='OBSERVED_READ_ONLY'
   symbol=$symbol
   capturedAt=(Get-Date).ToUniversalTime().ToString('o')
   samples=@($rows.ToArray())
   orderPermissionEnabled=$false
   privateAccountDataIncluded=$false
 }
 [IO.File]::WriteAllText($candidateFile,(ConvertTo-Json -InputObject $snapshot -Depth 6 -Compress),
   [Text.UTF8Encoding]::new($false))
 $node=(Get-Command node -CommandType Application -ErrorAction Stop).Source
 $publisher=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\no12_private_rss_seconds_publish.mjs'
 $published=@(& $node $publisher --private-root $privateRoot --candidate $candidateFile)
 if($LASTEXITCODE -ne 0){throw 'NO12_SECONDS_PRIVATE_RECEIPT_NOT_READY'}
 $status=@($published | Where-Object { $_ -cmatch '^NO12_SECONDS_RSS_STATUS=(PC_OBSERVED_EXCHANGE_SECONDS_ADVANCE_NOT_BROKER_CERTIFIED|PC_OBSERVED_SAMPLES_WITHOUT_EXCHANGE_TIME_ADVANCE)$' })
 $count=@($published | Where-Object { $_ -cmatch '^NO12_SECONDS_SAMPLE_COUNT=\d+$' })
 $age=@($published | Where-Object { $_ -cmatch '^NO12_SECONDS_MAX_OBSERVED_AGE_MS=\d+$' })
 if($status.Count -ne 1 -or $count.Count -ne 1 -or $age.Count -ne 1){
   throw 'NO12_SECONDS_PRIVATE_RECEIPT_UNVERIFIED'
 }
 Write-Host 'NO12_SECONDS_PRIVATE_READ_ONLY_RECEIPT=True'
 Write-Host $status[0]
 Write-Host $count[0]
 Write-Host $age[0]
 Write-Host 'ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
}catch{
 Write-Host 'NO12_SECONDS_RSS_PROBE_BLOCKED=True'
 Write-Host 'NO12_PRODUCTION_READY=False'
 Write-Host 'ORDER_TRANSMISSION=False'
 throw 'NO12_SECONDS_PROBE_STOPPED_SAFELY'
}finally{
 if($null -ne $candidateFile -and (Test-Path -LiteralPath $candidateFile -PathType Leaf)){
   Remove-Item -LiteralPath $candidateFile -Force -ErrorAction SilentlyContinue
 }
 if($null -ne $book){try{$book.Close($false)}catch{}}
 if($null -ne $sheet){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet)}catch{}}
 if($null -ne $book){try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}catch{}}
 if($null -ne $excel){
   if($created){try{$excel.Quit()}catch{}}
   try{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}catch{}
 }
 [GC]::Collect()
 [GC]::WaitForPendingFinalizers()
}
