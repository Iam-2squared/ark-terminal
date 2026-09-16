param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [string]$RssXllPath = (Join-Path $env:LOCALAPPDATA "MarketSpeed2\Bin\rss\MarketSpeed2_RSS_64bit.xll"),
    [switch]$DoNotAutoOpenWorkbook,
    [switch]$DoNotAutoLoadRssAddin
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
        if (-not $AutoOpen) { throw "EXCEL_APPLICATION_NOT_RUNNING" }
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

        # Snapshot capture itself stays read-only. One-time sheet provisioning is
        # a separate explicit setup command.
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
        throw ("ACCOUNT_SHEET_SETUP_REQUIRED: expected={0}; workbook={1}; sheets={2}; run=.\tools\Initialize-ArkAccountReadOnlySheet.ps1" -f $ExpectedAccountSheet, $ExpectedWorkbookName, $sheetSummary)
    }

    return [PSCustomObject]@{
        Excel = $excel
        Workbook = $workbook
        AccountSheet = $sheetMatches[0]
        ExcelStartedByLauncher = $excelStartedByLauncher
        WorkbookOpenedByLauncher = $workbookOpenedByLauncher
    }
}

function Assert-ArkAccountSheetLayout {
    param([Parameter(Mandatory=$true)]$Worksheet)

    $requiredFormulas = @{
        "L1"  = "RssCapacityList"
        "N1"  = "RssOrderList"
        "AA1" = "RssExecutionList"
        "AL1" = "RssPositionList"
    }
    foreach ($address in $requiredFormulas.Keys) {
        $cell = $Worksheet.Range($address)
        if ($cell.HasFormula -ne $true -or ([string]$cell.Formula) -notmatch [Regex]::Escape($requiredFormulas[$address])) {
            throw ("ACCOUNT_SHEET_LAYOUT_INVALID:{0}:{1}" -f $address, $requiredFormulas[$address])
        }
    }

    $requiredHeaders = @{
        "L2"="現物買付可能額"
        "N2"="注文番号"; "O2"="通常注文状況"; "P2"="銘柄コード"; "V2"="注文数量"; "W2"="約定数量"
        "AA2"="約定日"; "AB2"="銘柄コード"; "AD2"="口座区分"; "AG2"="売買"; "AH2"="約定数量"; "AI2"="約定単価"
        "AL2"="銘柄コード"; "AM2"="銘柄名称"; "AN2"="口座区分"; "AO2"="保有数量"
        "AQ2"="平均取得価額"; "AR2"="時価"; "AS2"="時価評価額"; "AT2"="評価損益額"; "AU2"="評価損益率"
    }
    foreach ($address in $requiredHeaders.Keys) {
        if ([string]$Worksheet.Range($address).Text -ne $requiredHeaders[$address]) {
            throw ("ACCOUNT_SHEET_HEADER_INVALID:{0}:expected={1}:actual={2}" -f $address, $requiredHeaders[$address], [string]$Worksheet.Range($address).Text)
        }
    }
}

function Get-ArkRssStatusText {
    param([Parameter(Mandatory=$true)]$Worksheet)
    return [ordered]@{
        L1 = ([string]$Worksheet.Range("L1").Text).Trim()
        N1 = ([string]$Worksheet.Range("N1").Text).Trim()
        AA1 = ([string]$Worksheet.Range("AA1").Text).Trim()
        AL1 = ([string]$Worksheet.Range("AL1").Text).Trim()
    }
}

function Ensure-ArkRssAddinLoaded {
    param(
        [Parameter(Mandatory=$true)]$Excel,
        [Parameter(Mandatory=$true)]$Worksheet,
        [Parameter(Mandatory=$true)][string]$ExpectedXllPath,
        [Parameter(Mandatory=$true)][bool]$AutoLoad
    )

    $before = Get-ArkRssStatusText -Worksheet $Worksheet
    $allNameErrors = @($before.Values | Where-Object { $_ -eq "#NAME?" }).Count -eq 4
    if (-not $allNameErrors) {
        return [PSCustomObject]@{ LoadedByLauncher=$false; Path=$null; Status="ALREADY_AVAILABLE" }
    }

    $resolvedXllPath = [IO.Path]::GetFullPath($ExpectedXllPath)
    if (-not $AutoLoad) {
        throw ("RSS_ADDIN_NOT_LOADED: expected={0}" -f $resolvedXllPath)
    }
    if (-not (Test-Path -LiteralPath $resolvedXllPath -PathType Leaf)) {
        throw ("RSS_ADDIN_FILE_MISSING: expected={0}" -f $resolvedXllPath)
    }

    try {
        $registered = $Excel.RegisterXLL($resolvedXllPath)
    }
    catch {
        throw ("RSS_ADDIN_REGISTER_FAILED: path={0}; error={1}" -f $resolvedXllPath, $_.Exception.Message)
    }
    if ($registered -ne $true) {
        throw ("RSS_ADDIN_REGISTER_FAILED: path={0}" -f $resolvedXllPath)
    }

    Start-Sleep -Milliseconds 500
    try { $Excel.CalculateFullRebuild() } catch { try { $Excel.CalculateFull() } catch { } }
    Start-Sleep -Milliseconds 1200

    $after = Get-ArkRssStatusText -Worksheet $Worksheet
    $stillNameErrors = @($after.Values | Where-Object { $_ -eq "#NAME?" }).Count -eq 4
    if ($stillNameErrors) {
        throw ("RSS_ADDIN_LOAD_DID_NOT_RESOLVE_FUNCTIONS: path={0}" -f $resolvedXllPath)
    }

    return [PSCustomObject]@{ LoadedByLauncher=$true; Path=$resolvedXllPath; Status="AUTO_LOADED" }
}

function Wait-ArkReadOnlyRssReady {
    param([Parameter(Mandatory=$true)]$Worksheet)

    $statusAddresses = @("L1", "N1", "AA1", "AL1")
    $last = @{}
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $allReady = $true
        foreach ($address in $statusAddresses) {
            $text = ([string]$Worksheet.Range($address).Text).Trim()
            $last[$address] = $text
            $ready = $text -match "配信中|完了"
            if (-not $ready) { $allReady = $false }
        }
        if ($allReady) { return $last }
        Start-Sleep -Milliseconds 250
        try { $Worksheet.Application.CalculateFull() } catch { }
    }
    throw ("RSS_READ_ONLY_SOURCE_NOT_READY:L1={0};N1={1};AA1={2};AL1={3}" -f $last["L1"], $last["N1"], $last["AA1"], $last["AL1"])
}

$resolved = Resolve-ArkDedicatedWorkbook `
    -ExpectedWorkbookName $WorkbookName `
    -ExpectedWorkbookPath $WorkbookPath `
    -ExpectedAccountSheet $AccountSheet `
    -AutoOpen (-not $DoNotAutoOpenWorkbook)

$acct = $resolved.AccountSheet
Assert-ArkAccountSheetLayout -Worksheet $acct
$rssAddin = Ensure-ArkRssAddinLoaded `
    -Excel $resolved.Excel `
    -Worksheet $acct `
    -ExpectedXllPath $RssXllPath `
    -AutoLoad (-not $DoNotAutoLoadRssAddin)
$rssStatus = Wait-ArkReadOnlyRssReady -Worksheet $acct

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
            orderQuantity=$acct.Cells.Item($row,42).Value2
            averagePrice=$acct.Cells.Item($row,43).Value2
            marketPrice=$acct.Cells.Item($row,44).Value2
            marketValue=$acct.Cells.Item($row,45).Value2
            unrealizedPnl=$acct.Cells.Item($row,46).Value2
            unrealizedPnlPercent=$acct.Cells.Item($row,47).Value2
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
    rssStatus=@{
        capacity=$rssStatus["L1"]
        orders=$rssStatus["N1"]
        executions=$rssStatus["AA1"]
        positions=$rssStatus["AL1"]
    }
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
Write-Host "RSSAddin    :" $rssAddin.Status
if ($rssAddin.Path) { Write-Host "RSSXll      :" $rssAddin.Path }
Write-Host "Snapshot    :" $target
Write-Host "Positions   :" $positions.Count
Write-Host "Orders      :" $orders.Count
Write-Host "Executions  :" $executions.Count
Write-Host "BuyingPower :" $buyingPower
Write-Host "CapacityRSS :" $rssStatus["L1"]
Write-Host "OrdersRSS   :" $rssStatus["N1"]
Write-Host "ExecutionRSS:" $rssStatus["AA1"]
Write-Host "PositionRSS :" $rssStatus["AL1"]
Write-Host "ExcelWrite  : FALSE"
Write-Host "RSSOrderCall:" "FALSE"
Write-Host "Transmitted :" "FALSE"
