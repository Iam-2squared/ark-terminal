param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED"
)
$ErrorActionPreference = "Stop"
$excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
$wb = $excel.Workbooks | Where-Object { $_.Name -eq $WorkbookName }
if ($null -eq $wb) { throw "$WorkbookName is not open" }
$acct = $wb.Worksheets.Item($AccountSheet)
$sheet = $null
foreach ($s in $wb.Worksheets) { if ($s.Name -eq $OrderSheet) { $sheet=$s; break } }
if ($null -eq $sheet) { $sheet=$wb.Worksheets.Add(); $sheet.Name=$OrderSheet }

# This launcher is deliberately inspection-only. It never assigns .Formula and
# never calls an RSS order function. The draft cell is forced to text.
$sheet.Range("A1").Value2="ARK CASH-ONLY ORDER INTERFACE"
$sheet.Range("A3").Value2="MODE"; $sheet.Range("B3").Value2="LOCKED / NO TRANSMISSION"
$sheet.Range("A4").Value2="PRODUCT"; $sheet.Range("B4").Value2="CASH ONLY"
$sheet.Range("A5").Value2="MARGIN"; $sheet.Range("B5").Value2="DISABLED"
$sheet.Range("A6").Value2="SHORT SELLING"; $sheet.Range("B6").Value2="DISABLED"
$sheet.Range("A11").Value2="TRIGGER"; $sheet.Range("B11").Value2=0
$buyingPower = $acct.Cells.Item(3,12).Value2
if ($null -eq $buyingPower) { $buyingPower = 0 }
$sheet.Range("A12").Value2="BUYING POWER"
$sheet.Range("B12").Value2=[string]$buyingPower
$sheet.Range("A13").Value2="RSS FUNCTION DRAFT"
$sheet.Range("B13").NumberFormat="@"
$sheet.Range("A15").Value2="EXECUTION ALLOWED"; $sheet.Range("B15").Value2="FALSE"
$sheet.Range("A16").Value2="TRANSMITTED"; $sheet.Range("B16").Value2="FALSE"
$sheet.Range("A17").Value2="EXCEL ORDER WRITE"; $sheet.Range("B17").Value2="FALSE"
$sheet.Range("A18").Value2="STATUS"; $sheet.Range("B18").Value2="LOCKED - G10 ADAPTER INPUT REQUIRED"
$sheet.Columns("A:B").AutoFit()
$wb.Save()
Write-Host "ARK_CASH_LOCKED_READY"
Write-Host "BuyingPower :" $buyingPower
Write-Host "Trigger     :" $sheet.Range("B11").Value2
Write-Host "Formula?    :" $sheet.Range("B13").HasFormula
Write-Host "Execution   :" $sheet.Range("B15").Text
Write-Host "Transmitted :" $sheet.Range("B16").Text
