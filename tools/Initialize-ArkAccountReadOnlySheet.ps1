param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$BackupDirectory = "C:\Ark\backups"
)

$ErrorActionPreference = "Stop"

$writeCapableFunctions = @(
    "RssStockOrder",
    "RssMarginOpenOrder",
    "RssMarginCloseOrder",
    "RssModifyOrder",
    "RssCancelOrder",
    "RssFOPOpenOrder",
    "RssFOPCloseOrder",
    "RssFOPMultiOpenOrder",
    "RssFOPMultiCloseOrder",
    "RssFOPModifyOrder",
    "RssFOPCancelOrder"
)

function Get-ArkExcelApplication {
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    }
    catch {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $true
        return $excel
    }
}

function Assert-NoWriteCapableRssFormula {
    param([Parameter(Mandatory=$true)]$Worksheet)
    $used = $Worksheet.UsedRange
    $rows = [Math]::Max(1, [int]$used.Rows.Count)
    $columns = [Math]::Max(1, [int]$used.Columns.Count)
    for ($row = 1; $row -le $rows; $row++) {
        for ($column = 1; $column -le $columns; $column++) {
            $cell = $Worksheet.Cells.Item($row, $column)
            if ($cell.HasFormula -eq $true) {
                $formula = [string]$cell.Formula
                foreach ($functionName in $writeCapableFunctions) {
                    if ($formula -match [Regex]::Escape($functionName)) {
                        throw ("WRITE_CAPABLE_RSS_FORMULA_FORBIDDEN:{0}:{1}" -f $cell.Address(), $functionName)
                    }
                }
            }
        }
    }
}

$resolvedWorkbookPath = [IO.Path]::GetFullPath($WorkbookPath)
if (-not (Test-Path -LiteralPath $resolvedWorkbookPath -PathType Leaf)) {
    throw ("DEDICATED_WORKBOOK_FILE_MISSING:{0}" -f $resolvedWorkbookPath)
}

$excel = Get-ArkExcelApplication
$matchingBooks = @($excel.Workbooks | Where-Object { $_.Name -eq $WorkbookName })
if ($matchingBooks.Count -gt 1) { throw "MULTIPLE_DEDICATED_WORKBOOKS_OPEN" }

$workbook = $null
if ($matchingBooks.Count -eq 1) {
    $workbook = $matchingBooks[0]
    if ($workbook.ReadOnly -eq $true) {
        # A prior read-only preview may have auto-opened the file. Close only
        # this dedicated workbook without saving, then reopen it writable.
        $workbook.Close($false)
        Start-Sleep -Milliseconds 300
        $workbook = $excel.Workbooks.Open($resolvedWorkbookPath, 0, $false)
    }
}
else {
    $workbook = $excel.Workbooks.Open($resolvedWorkbookPath, 0, $false)
}

if ($null -eq $workbook -or $workbook.ReadOnly -eq $true) {
    throw "WRITABLE_DEDICATED_WORKBOOK_REQUIRED_FOR_ONE_TIME_SETUP"
}

$existing = @($workbook.Worksheets | Where-Object { $_.Name -eq $AccountSheet })
if ($existing.Count -gt 1) { throw "MULTIPLE_ACCOUNT_SHEETS_FOUND" }
if ($existing.Count -eq 1) {
    Assert-NoWriteCapableRssFormula -Worksheet $existing[0]
    Write-Host "ARK_ACCOUNT_READ_ONLY_SHEET_ALREADY_EXISTS"
    Write-Host "Workbook   :" $WorkbookName
    Write-Host "Sheet      :" $AccountSheet
    Write-Host "SetupWrite : NONE"
    Write-Host "OrderFuncs : NONE"
    return
}

[void](New-Item -ItemType Directory -Force -Path ([IO.Path]::GetFullPath($BackupDirectory)))
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path ([IO.Path]::GetFullPath($BackupDirectory)) ("Ark_MSII_LiveSource.before-account-readonly-{0}.xlsx" -f $timestamp)
$workbook.SaveCopyAs($backupPath)

$sheet = $workbook.Worksheets.Add()
$sheet.Name = $AccountSheet

# Dedicated read-only RSS layout. Row 1 = function/status, row 2 = requested
# fields, row 3+ = returned data. No order creation/cancel/modify function is
# written anywhere in this sheet.
$sheet.Range("L2").Value2 = "現物買付可能額"
$sheet.Range("L1").Formula = '=RssCapacityList(L2:L2)'

$orderHeaders = @(
    "注文番号",
    "通常注文状況",
    "銘柄コード",
    "銘柄名称",
    "口座区分",
    "売買",
    "取引",
    "執行条件",
    "注文数量",
    "約定数量"
)
for ($index = 0; $index -lt $orderHeaders.Count; $index++) {
    $sheet.Cells.Item(2, 14 + $index).Value2 = $orderHeaders[$index]
}
$sheet.Range("N1").Formula = '=RssOrderList(N2:W2,0,1)'

$executionHeaders = @(
    "約定日",
    "銘柄コード",
    "銘柄名称",
    "口座区分",
    "市場名称",
    "取引",
    "売買",
    "約定数量",
    "約定単価"
)
for ($index = 0; $index -lt $executionHeaders.Count; $index++) {
    $sheet.Cells.Item(2, 27 + $index).Value2 = $executionHeaders[$index]
}
$sheet.Range("AA1").Formula = '=RssExecutionList(AA2:AI2,1)'

$positionHeaders = @(
    "銘柄コード",
    "銘柄名称",
    "口座区分",
    "保有数量",
    "発注数量",
    "平均取得価額",
    "時価",
    "時価評価額",
    "評価損益額",
    "評価損益率"
)
for ($index = 0; $index -lt $positionHeaders.Count; $index++) {
    $sheet.Cells.Item(2, 38 + $index).Value2 = $positionHeaders[$index]
}
$sheet.Range("AL1").Formula = '=RssPositionList(AL2:AU2)'

Assert-NoWriteCapableRssFormula -Worksheet $sheet

$sheet.Columns("L:AU").AutoFit() | Out-Null
$workbook.Save()
try { $excel.CalculateFull() } catch { }
Start-Sleep -Milliseconds 1200

Assert-NoWriteCapableRssFormula -Worksheet $sheet

Write-Host "ARK_ACCOUNT_READ_ONLY_SHEET_INITIALIZED"
Write-Host "Workbook   :" $WorkbookName
Write-Host "Sheet      :" $AccountSheet
Write-Host "Backup     :" $backupPath
Write-Host "Capacity   :" $sheet.Range("L1").Text
Write-Host "Orders     :" $sheet.Range("N1").Text
Write-Host "Executions :" $sheet.Range("AA1").Text
Write-Host "Positions  :" $sheet.Range("AL1").Text
Write-Host "OrderFuncs : NONE"
Write-Host "Execution  : FALSE"
Write-Host "Transmitted:" "FALSE"
