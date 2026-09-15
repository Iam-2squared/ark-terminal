param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json"
)
$ErrorActionPreference = "Stop"
$excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
$wb = $excel.Workbooks | Where-Object { $_.Name -eq $WorkbookName }
if ($null -eq $wb) { throw "$WorkbookName is not open" }
$acct = $wb.Worksheets.Item($AccountSheet)
$excel.CalculateFull(); Start-Sleep -Milliseconds 500

# Fresh READ ONLY account snapshot. No order function is invoked here.
$positions=@()
for($r=3;$r -le 200;$r++){
 $symbol=$acct.Cells.Item($r,38).Text; $name=$acct.Cells.Item($r,39).Text; $account=$acct.Cells.Item($r,40).Text; $qty=$acct.Cells.Item($r,41).Value2
 if($symbol -and $symbol -ne "--------" -and $name -and $name -ne "--------" -and $null -ne $qty){
  $positions += [PSCustomObject]@{symbol=$symbol;name=$name;account=$account;quantity=$qty}
 }
}
$orders=@()
for($r=3;$r -le 300;$r++){
 $n=$acct.Cells.Item($r,14).Text
 if($n -and $n -ne "--------"){$orders += [PSCustomObject]@{orderNumber=$n;status=$acct.Cells.Item($r,15).Text;symbol=$acct.Cells.Item($r,16).Text;quantity=$acct.Cells.Item($r,22).Value2;filledQty=$acct.Cells.Item($r,23).Value2}}
}
$buyingPower=$acct.Cells.Item(3,12).Value2; if($null -eq $buyingPower){$buyingPower=0}
$snapshot=[PSCustomObject]@{schemaId="ARK_ACCOUNT_READONLY_SNAPSHOT_V2";capturedAt=(Get-Date).ToString("o");source="MARKETSPEED_II_RSS";mode="READ_ONLY";positions=$positions;orders=$orders;executions=@();buyingPower=$buyingPower;safety=@{executionAllowed=$false;brokerWriteAllowed=$false;excelOrderWriteAllowed=$false;rssOrderFunctionAllowed=$false;liveTradingAllowed=$false;paperTradingAllowed=$false;automaticPromotionAllowed=$false;productionUpdateAllowed=$false;transmitted=$false}}
$dir=Split-Path -Parent $SnapshotPath; New-Item -ItemType Directory -Force $dir | Out-Null
$snapshot | ConvertTo-Json -Depth 10 | Set-Content $SnapshotPath -Encoding UTF8

$sheet=$null; foreach($s in $wb.Worksheets){if($s.Name -eq $OrderSheet){$sheet=$s;break}}
if($null -eq $sheet){$sheet=$wb.Worksheets.Add();$sheet.Name=$OrderSheet}
# Inspection-only interface: never assigns .Formula and never calls RSS orders.
$sheet.Range("A1").Value2="ARK CASH-ONLY ORDER INTERFACE"
$sheet.Range("A3").Value2="MODE";$sheet.Range("B3").Value2="LOCKED / NO TRANSMISSION"
$sheet.Range("A4").Value2="PRODUCT";$sheet.Range("B4").Value2="CASH ONLY"
$sheet.Range("A5").Value2="MARGIN";$sheet.Range("B5").Value2="DISABLED"
$sheet.Range("A6").Value2="SHORT SELLING";$sheet.Range("B6").Value2="DISABLED"
$sheet.Range("A11").Value2="TRIGGER";$sheet.Range("B11").Value2=0
$sheet.Range("A12").Value2="BUYING POWER";$sheet.Range("B12").Value2=[string]$buyingPower
$sheet.Range("A13").Value2="RSS FUNCTION DRAFT";$sheet.Range("B13").NumberFormat="@"
$sheet.Range("A15").Value2="EXECUTION ALLOWED";$sheet.Range("B15").Value2="FALSE"
$sheet.Range("A16").Value2="TRANSMITTED";$sheet.Range("B16").Value2="FALSE"
$sheet.Range("A17").Value2="EXCEL ORDER WRITE";$sheet.Range("B17").Value2="FALSE"
$sheet.Range("A18").Value2="STATUS";$sheet.Range("B18").Value2="LOCKED - FRESH SNAPSHOT READY"
$sheet.Columns("A:B").AutoFit();$wb.Save()
Write-Host "ARK_CASH_LOCKED_READY"
Write-Host "Snapshot    :" $SnapshotPath
Write-Host "Positions   :" $positions.Count
Write-Host "Orders      :" $orders.Count
Write-Host "BuyingPower :" $buyingPower
Write-Host "Trigger     :" $sheet.Range("B11").Value2
Write-Host "Formula?    :" $sheet.Range("B13").HasFormula
Write-Host "Execution   :" $sheet.Range("B15").Text
Write-Host "Transmitted :" $sheet.Range("B16").Text
