# Pure value-parser smoke test for the November 2 exact 24-symbol RSS
# reference. Uses a manufactured in-process 2D array only, not an Excel
# simulation, no Excel/COM, broker, RSS, account or trading.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$ci=[Globalization.CultureInfo]::InvariantCulture
function DateValue($v){
 if($null -eq $v){return $null}
 if($v -is [datetime]){return $v.ToString('yyyy-MM-dd',$ci)}
 if($v -is [ValueType]){
  $n=[double]$v
  if($n -ge 30000 -and $n -le 80000){return [datetime]::FromOADate($n).ToString('yyyy-MM-dd',$ci)}
  return $null
 }
 $d=[datetime]::MinValue
 if([datetime]::TryParseExact(([string]$v).Replace('/','-'),'yyyy-MM-dd',$ci,[Globalization.DateTimeStyles]::None,[ref]$d)){
  return $d.ToString('yyyy-MM-dd',$ci)
 }
 return $null
}
function NumberValue($v){
 if($null -eq $v -or $v -isnot [ValueType]){return $null}
 $n=[double]$v
 if([double]::IsNaN($n) -or [double]::IsInfinity($n)){return $null}
 return $n
}
$vals=[Array]::CreateInstance([object],24,12)
for($i=0;$i -lt 24;$i++){
 $symbol=('{0:0000}.T' -f (3753+$i))
 $vals.SetValue($symbol,$i,0)
 $vals.SetValue($symbol.Substring(0,4),$i,1)
 $vals.SetValue('T',$i,2)
 $vals.SetValue([datetime]::ParseExact('2026-11-02','yyyy-MM-dd',$ci).ToOADate(),$i,3)
 $vals.SetValue([datetime]::ParseExact('2026-10-30','yyyy-MM-dd',$ci).ToOADate(),$i,4)
 $vals.SetValue(1200.0,$i,5)
 $vals.SetValue(1200.0,$i,6)
 $vals.SetValue('Market',$i,7)
 $vals.SetValue(100.0,$i,8)
 for($j=9;$j -lt 12;$j++){$vals.SetValue('',$i,$j)}
}
$rows=@()
for($i=0;$i -lt 24;$i++){
 $r=$i;$c0=0
 $rows+=@([ordered]@{
  symbol=([string]$vals.GetValue($r,$c0))
  marketCode=([string]$vals.GetValue($r,$c0+2)).Trim()
  marketDate=(DateValue $vals.GetValue($r,$c0+3))
  previousDate=(DateValue $vals.GetValue($r,$c0+4))
  previousClose=(NumberValue $vals.GetValue($r,$c0+5))
  dayBasePrice=(NumberValue $vals.GetValue($r,$c0+6))
  marketSection=([string]$vals.GetValue($r,$c0+7)).Trim()
  lotShares=(NumberValue $vals.GetValue($r,$c0+8))
 })
}
if($rows.Count -ne 24 -or $rows[0].marketDate -cne '2026-11-02' -or
   $rows[23].previousDate -cne '2026-10-30' -or $rows[9].previousClose -ne 1200){
 throw 'NO11_REFERENCE_ARRAY_VALUE_PARSER_MISMATCH'
}
Write-Host 'NO11_REFERENCE_PURE_24_VALUE_PARSER=PASS'
Write-Host 'NO11_REFERENCE_PURE_JSON_BEGIN=True'
$payload=[ordered]@{
 schemaId='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'
 sessionDate='2026-11-02'
 source='RssMarket_SELECTED_REFERENCE_READONLY'
 capturedAtJst='2026-11-02T11:00:00.000+09:00'
 completedAtJst='2026-11-02T11:00:01.000+09:00'
 chartPlanSha256=('0'*64)
 selectedSymbols=@($rows|ForEach-Object {$_.symbol})
 rows=@($rows)
 corporateActionReviewPerformed=$false
 readOnly=$true
 productionReady=$false
 orderTransmission=$false
}
$utf8=[Text.UTF8Encoding]::new($false)
$raw=$utf8.GetBytes((ConvertTo-Json -InputObject $payload -Depth 10 -Compress)+[char]10)
if($raw.Length -lt 3000 -or $raw.Length -gt 100000){
 throw 'NO11_REFERENCE_PURE_JSON_SIZE_INVALID'
}
$roundTrip=$utf8.GetString($raw)|ConvertFrom-Json
if(@($roundTrip.rows).Count -ne 24 -or $roundTrip.orderTransmission -ne $false){
 throw 'NO11_REFERENCE_PURE_JSON_ROUND_TRIP_INVALID'
}
Write-Host ('NO11_REFERENCE_PURE_JSON_24=PASS|BYTES='+$raw.Length)
Write-Host 'EXCEL_STARTED=False'
Write-Host 'ORDER_TRANSMISSION=False'
