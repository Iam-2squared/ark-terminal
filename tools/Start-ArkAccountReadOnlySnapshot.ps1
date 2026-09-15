param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [switch]$DoNotAutoOpenWorkbook
)

$ErrorActionPreference = "Stop"

function Resolve-ArkDedicatedWorkbook {
    param(
        [Parameter(Mandatory=$true)][string]$ExpectedWorkbookName,
        [Parameter(Mandatory=$true)][string]$ExpectedWorkbookPath,
        [Parameter(Mandatory=$true)][string]$ExpectedAccountSheet,
        [Parameter(Mandatory=$true)][bool]$AutoOpen
    )

    $excel = $null
    $excelStartedByLauncher = $false
    $workbookOpenedByLauncher = $false

    try {
        $excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    }
    catch {
        if (-not $AutoOpen) {
            throw "EXCEL_APPLICATION_NOT_RUNNING"
        }
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $true
        $excelStartedByLauncher = $true
    }

    $matchingBooks = @($excel.Workbooks | Where-Object { $_.Name -eq $ExpectedWorkbookName })
    if ($matchingBooks.Count -eq 0 -and $AutoOpen) {
        $resolvedWorkbookPath = [IO.Path]::GetFullPath($ExpectedWorkbookPath)
        if (-not (Test-Path -LiteralPath $resolvedWorkbookPath -PathType Leaf)) {
            $openNames = @($excel.Workbooks | ForEach-Object { [string]$_.Name })
            $openSummary = if ($openNames.Count -gt 0) { $openNames -join "," } else { "NONE" }
            throw ("DEDICATED_WORKBOOK_FILE_MISSING: expected={0}; path={1}; open={2}" -f $ExpectedWorkbookName, $resolvedWorkbookPath, $openSummary)
        }

        # Open read-only. This launcher never writes to workbook cells and never
        # evaluates or transmits an RSS order function.
        $opened = $excel.Workbooks.Open($resolvedWorkbookPath, 0, $true)
        if ($null -eq $opened) { throw "DEDICATED_WORKBOOK_OPEN_FAILED" }
        $workbookOpenedByLauncher = $true
        Start-Sleep -Milliseconds 1200
        try { $excel.CalculateFull() } catch { }
        Start-Sleep -Milliseconds 500
        $matchingBooks = @($excel.Workbooks | Where-Object { $_.Name -eq $ExpectedWorkbookName })
    }

    if ($matchingBooks.Count -ne 1) {
        $openNames = @($excel.Workbooks | ForEach-Object { [string]$_.Name })
        $openSummary = if ($openNames.Count -gt 0) { $openNames -join "," } else { "NONE" }
        throw ("OPEN_DEDICATED_WORKBOOK_REQUIRED: expected={0}; open={1}" -f $ExpectedWorkbookName, $openSummary)
    }

    $workbook = $matchingBooks[0]
    $sheetMatches = @($workbook.Worksheets | Where-Object { $_.Name -eq $ExpectedAccountSheet })
    if ($sheetMatches.Count -ne 1) {
        $sheetNames = @($workbook.Worksheets | ForEach-Object { [string]$_.Name })
        $sheetSummary = if ($sheetNames.Count -gt 0) { $sheetNames -join "," } else { "NONE" }
        throw ("ACCOUNT_SHEET_REQUIRED: expected={0}; workbook={1}; sheets={2}" -f $ExpectedAccountSheet, $ExpectedWorkbookName, $sheetSummary)
    }

    return [PSCustomObject]@{
        Excel = $excel
        Workbook = $workbook
        AccountSheet = $sheetMatches[0]
        ExcelStartedByLauncher = $excelStartedByLauncher
        WorkbookOpenedByLauncher = $workbookOpenedByLauncher
    }
}

$resolved = Resolve-ArkDedicatedWorkbook `
    -ExpectedWorkbookName $WorkbookName `
    -ExpectedWorkbookPath $WorkbookPath `
    -ExpectedAccountSheet $AccountSheet `
    -AutoOpen (-not $DoNotAutoOpenWorkbook)

$acct = $resolved.AccountSheet

$captureStartedAt = (Get-Date).ToString("o")
$positions = @()
for ($row = 3; $row -le 200; $row++) {
    $positionSymbol = $acct.Cells.Item($row,38).Text
    $positionName = $acct.Cells.Item($row,39).Text
    $positionAccount = $acct.Cells.Item($row,40).Text
    $positionQuantity = $acct.Cells.Item($row,41).Value2
    if ($positionName -and $positionName -ne "--------" -and $null -ne $positionQuantity) {
        $positions += [PSCustomObject]@{
            symbol=$positionSymbol
            name=$positionName
            account=$positionAccount
            quantity=$positionQuantity
        }
    }
}

$orders = @()
for ($row = 3; $row -le 300; $row++) {
    $orderNumber = $acct.Cells.Item($row,14).Text
    if ($orderNumber -and $orderNumber -ne "--------") {
        $orders += [PSCustomObject]@{
            orderNumber=$orderNumber
            status=$acct.Cells.Item($row,15).Text
            symbol=$acct.Cells.Item($row,16).Text
            quantity=$acct.Cells.Item($row,22).Value2
            filledQty=$acct.Cells.Item($row,23).Value2
        }
    }
}

$executions = @()
for ($row = 3; $row -le 300; $row++) {
    $executionDate = $acct.Cells.Item($row,27).Text
    if ($executionDate -and $executionDate -ne "--------") {
        $executions += [PSCustomObject]@{
            executionDate=$executionDate
            symbol=$acct.Cells.Item($row,28).Text
            account=$acct.Cells.Item($row,30).Text
            side=$acct.Cells.Item($row,33).Text
            quantity=$acct.Cells.Item($row,34).Value2
            price=$acct.Cells.Item($row,35).Value2
        }
    }
}

$buyingPower = $null
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    $buyingPower = $acct.Cells.Item(3,12).Value2
    if ($null -ne $buyingPower) { break }
    Start-Sleep -Milliseconds 250
}
if ($null -eq $buyingPower) { throw "BUYING_POWER_READ_MISSING" }

$snapshot = [PSCustomObject]@{
    schemaId="ARK_ACCOUNT_READONLY_SNAPSHOT_V2"
    capturedAt=$captureStartedAt
    captureCompletedAt=(Get-Date).ToString("o")
    source="MARKETSPEED_II_RSS"
    mode="READ_ONLY"
    positions=$positions
    orders=$orders
    executions=$executions
    buyingPower=$buyingPower
    safety=@{
        executionAllowed=$false
        brokerWriteAllowed=$false
        excelOrderWriteAllowed=$false
        rssOrderFunctionAllowed=$false
        liveTradingAllowed=$false
        paperTradingAllowed=$false
        automaticPromotionAllowed=$false
        productionUpdateAllowed=$false
        transmitted=$false
    }
}

$target = [IO.Path]::GetFullPath($SnapshotPath)
$directory = Split-Path -Parent $target
[void](New-Item -ItemType Directory -Force -Path $directory)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($target, ($snapshot | ConvertTo-Json -Depth 12), $utf8)

Write-Host "ARK_ACCOUNT_READ_ONLY_SNAPSHOT_READY"
Write-Host "Workbook    :" $WorkbookName
Write-Host "AutoOpened  :" $resolved.WorkbookOpenedByLauncher
Write-Host "Snapshot    :" $target
Write-Host "Positions   :" $positions.Count
Write-Host "Orders      :" $orders.Count
Write-Host "Executions  :" $executions.Count
Write-Host "BuyingPower :" $buyingPower
Write-Host "ExcelWrite  : FALSE"
Write-Host "RSSOrderCall:" "FALSE"
Write-Host "Transmitted :" "FALSE"
