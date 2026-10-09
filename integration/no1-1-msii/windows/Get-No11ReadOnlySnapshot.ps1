param(
    [string]$WorkbookName = "Ark_No11_RSS_ReadOnly.xlsx",
    [string]$WorkbookPath = "C:\Ark\Ark_No11_RSS_ReadOnly.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$SnapshotPath = (Join-Path $env:LOCALAPPDATA "ArkTerminal\No11\snapshot.json"),
    [string]$SourceHealthPath = (Join-Path $env:LOCALAPPDATA "ArkTerminal\No11\source-health.json"),
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
    $expectedFullPath = [IO.Path]::GetFullPath($ExpectedWorkbookPath)
    $actualFullPath = [IO.Path]::GetFullPath([string]$workbook.FullName)
    if ($expectedFullPath -ne $actualFullPath) { throw "DEDICATED_WORKBOOK_PATH_MISMATCH" }
    if (-not (Test-Path -LiteralPath $expectedFullPath -PathType Leaf)) { throw "DEDICATED_WORKBOOK_NOT_ON_DISK" }
    # RSS streaming may mark Excel as unsaved without changing the persisted
    # sheet layout. Verify exact disk path, formulas and headers instead;
    # never save or mutate the live Workbook from a snapshot reader.
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

function Get-No11RssCellStatus {
    param([Parameter(Mandatory=$true)]$Worksheet,[string]$Address)
    $expected = @{
        L1  = @{ formula = "=RssCapacityList(L2:L2)"; state = "完了" }
        N1  = @{ formula = "=RssOrderList(N2:W2,0,1)"; state = "配信中" }
        AA1 = @{ formula = "=RssExecutionList(AA2:AI2,1)"; state = "配信中" }
        AL1 = @{ formula = "=RssPositionList(AL2:AU2)"; state = "配信中" }
    }
    if (-not $expected.ContainsKey($Address)) { throw "RSS_STATUS_ADDRESS_INVALID" }
    $cell = $Worksheet.Range($Address)
    if ($cell.HasFormula -ne $true) { return "RSS_FORMULA_MISSING" }
    $formula = ([string]$cell.Formula) -replace "^=@", "="
    if ($formula -cne $expected[$Address].formula) { return "RSS_FORMULA_MISMATCH" }
    $state = [string]$expected[$Address].state
    foreach ($raw in @([string]$cell.Value2,[string]$cell.Text)) {
        $value = $raw.Trim()
        if ($value -ceq $state -or $value -ceq ($formula + " => " + $state)) {
            return $state
        }
        if ($value -ceq ("=@" + $formula.Substring(1) + " => " + $state)) {
            return $state
        }
    }
    return "RSS_STATUS_UNRECOGNIZED"
}

function Get-ArkRssStatusText {
    param([Parameter(Mandatory=$true)]$Worksheet)
    return [ordered]@{
        L1 = (Get-No11RssCellStatus -Worksheet $Worksheet -Address "L1")
        N1 = (Get-No11RssCellStatus -Worksheet $Worksheet -Address "N1")
        AA1 = (Get-No11RssCellStatus -Worksheet $Worksheet -Address "AA1")
        AL1 = (Get-No11RssCellStatus -Worksheet $Worksheet -Address "AL1")
    }
}

# RSS XLL registration must be done manually inside Excel. No RegisterXLL code
# is allowed in this live-read-only capture script, including fallback paths.
function Assert-No11RssAddinLoaded {
    param([Parameter(Mandatory=$true)]$Worksheet)
    $status = Get-ArkRssStatusText -Worksheet $Worksheet
    if (@($status.Values | Where-Object { $_ -eq '#NAME?' }).Count -gt 0) {
        throw 'RSS_ADDIN_MISSING_MANUAL_EXCEL_ENABLE_REQUIRED'
    }
    return [PSCustomObject]@{ LoadedByLauncher=$false; Path=$null; Status='ALREADY_AVAILABLE' }
}

function Wait-ArkReadOnlyRssReady {
    param([Parameter(Mandatory=$true)]$Worksheet)

    $statusAddresses = @("L1", "N1", "AA1", "AL1")
    $last = @{}
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $allReady = $true
        foreach ($address in $statusAddresses) {
            $text = Get-No11RssCellStatus -Worksheet $Worksheet -Address $address
            $last[$address] = $text
            $ready = if ($address -eq "L1") { $text -eq "完了" } else { $text -eq "配信中" }
            if (-not $ready) { $allReady = $false }
        }
        if ($allReady) { return $last }
        Start-Sleep -Milliseconds 250
        # Never recalculate other open Workbooks from a READ ONLY snapshot.
        try { $Worksheet.Calculate() } catch { }
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
$rssAddin = Assert-No11RssAddinLoaded -Worksheet $acct
$rssStatus = Wait-ArkReadOnlyRssReady -Worksheet $acct

$captureStartedAt = (Get-Date).ToString("o")
$positions = @()
for ($row = 3; $row -le 200; $row++) {
    $positionSymbol = $acct.Cells.Item($row,38).Text
    $positionName = $acct.Cells.Item($row,39).Text
    $positionAccount = $acct.Cells.Item($row,40).Text
    $positionQuantity = $acct.Cells.Item($row,41).Value2
    if ($positionName -and $positionName -ne "--------" -and $null -ne $positionQuantity) {
        $symbolValue = ([string]$acct.Cells.Item($row,38).Value2).Trim().ToUpperInvariant()
        if ([string]::IsNullOrWhiteSpace($symbolValue)) {
            throw ("BROKER_POSITION_SYMBOL_MISSING:ROW_{0}" -f $row)
        }
        if ($symbolValue -notmatch '^[0-9A-Z]{4,5}
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
        productionReady=$false
    }
}

# Status observations are not equivalent to underlying RSS delivery timestamps.
# A later live gate must independently verify actual source age.
$feedObservationTime = (Get-Date).ToString("o")
$sourceHealth = [PSCustomObject]@{
    schemaId = "ARK_MSII_RSS_SOURCE_HEALTH_V1"
    source = "MARKETSPEED_II_RSS"
    readOnly = $true
    addinLoaded = $true
    workbookPersisted = $true
    rssErrors = 0
    healthCapturedAt = $feedObservationTime
    actualFeedTimestampCertified = $false
    feeds = @{
        capacity = @{ state = $rssStatus["L1"]; observedAt = $feedObservationTime }
        orders = @{ state = $rssStatus["N1"]; observedAt = $feedObservationTime }
        executions = @{ state = $rssStatus["AA1"]; observedAt = $feedObservationTime }
        positions = @{ state = $rssStatus["AL1"]; observedAt = $feedObservationTime }
    }
}

$target = [IO.Path]::GetFullPath($SnapshotPath)
$directory = Split-Path -Parent $target
[void](New-Item -ItemType Directory -Force -Path $directory)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($target, ($snapshot | ConvertTo-Json -Depth 12), $utf8)
$healthTarget = [IO.Path]::GetFullPath($SourceHealthPath)
if ($healthTarget -eq $target) { throw "SOURCE_HEALTH_CANNOT_OVERWRITE_SNAPSHOT" }
[void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $healthTarget))
[IO.File]::WriteAllText($healthTarget, ($sourceHealth | ConvertTo-Json -Depth 12), $utf8)

Write-Host "ARK_ACCOUNT_READ_ONLY_SNAPSHOT_READY"
Write-Host "Workbook    :" $WorkbookName
Write-Host "AutoOpened  :" $resolved.WorkbookOpenedByLauncher
Write-Host "RSSAddin    :" $rssAddin.Status
if ($rssAddin.Path) { Write-Host "RSSXll      :" $rssAddin.Path }
Write-Host "Snapshot    :" $target
Write-Host "Health      :" $healthTarget
Write-Host "FeedTimeCertified: FALSE"
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
) {
            throw ("BROKER_POSITION_SYMBOL_UNRESOLVED:ROW_{0}" -f $row)
        }
        if ($positionQuantity -isnot [ValueType] -or [double]$positionQuantity -le 0) {
            throw ("BROKER_POSITION_QUANTITY_INVALID:ROW_{0}" -f $row)
        }
        $positionSymbol = $symbolValue
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
        productionReady=$false
    }
}

# Status observations are not equivalent to underlying RSS delivery timestamps.
# A later live gate must independently verify actual source age.
$feedObservationTime = (Get-Date).ToString("o")
$sourceHealth = [PSCustomObject]@{
    schemaId = "ARK_MSII_RSS_SOURCE_HEALTH_V1"
    source = "MARKETSPEED_II_RSS"
    readOnly = $true
    addinLoaded = $true
    workbookPersisted = $true
    rssErrors = 0
    healthCapturedAt = $feedObservationTime
    actualFeedTimestampCertified = $false
    feeds = @{
        capacity = @{ state = $rssStatus["L1"]; observedAt = $feedObservationTime }
        orders = @{ state = $rssStatus["N1"]; observedAt = $feedObservationTime }
        executions = @{ state = $rssStatus["AA1"]; observedAt = $feedObservationTime }
        positions = @{ state = $rssStatus["AL1"]; observedAt = $feedObservationTime }
    }
}

$target = [IO.Path]::GetFullPath($SnapshotPath)
$directory = Split-Path -Parent $target
[void](New-Item -ItemType Directory -Force -Path $directory)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($target, ($snapshot | ConvertTo-Json -Depth 12), $utf8)
$healthTarget = [IO.Path]::GetFullPath($SourceHealthPath)
if ($healthTarget -eq $target) { throw "SOURCE_HEALTH_CANNOT_OVERWRITE_SNAPSHOT" }
[void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $healthTarget))
[IO.File]::WriteAllText($healthTarget, ($sourceHealth | ConvertTo-Json -Depth 12), $utf8)

Write-Host "ARK_ACCOUNT_READ_ONLY_SNAPSHOT_READY"
Write-Host "Workbook    :" $WorkbookName
Write-Host "AutoOpened  :" $resolved.WorkbookOpenedByLauncher
Write-Host "RSSAddin    :" $rssAddin.Status
if ($rssAddin.Path) { Write-Host "RSSXll      :" $rssAddin.Path }
Write-Host "Snapshot    :" $target
Write-Host "Health      :" $healthTarget
Write-Host "FeedTimeCertified: FALSE"
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
