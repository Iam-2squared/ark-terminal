param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [ValidateNotNullOrEmpty()][string]$Symbol = "7203.T",
    [ValidateRange(1,2147483647)][int]$Quantity = 100,
    [double]$EstimatedNotional = 300000,
    [string]$ExternalSymbol = "408A",
    [double]$ExternalQuantity = 180
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "phase57_cash_locked_bridge.ps1")

# Capture diagnostic order parameters BEFORE reading broker rows. PowerShell
# variable names are case-insensitive: $symbol would overwrite $Symbol.
$orderRequest = @{
    schemaId = "ARK_CASH_LOCKED_REQUEST_V1"
    snapshotPath = [IO.Path]::GetFullPath($SnapshotPath)
    intent = @{
        symbol = $Symbol.Trim().ToUpperInvariant()
        direction = "LONG"; side = "BUY"; positionEffect = "OPEN"
        quantity = $Quantity; orderType = "MARKET"; limitPrice = $null
        timeInForce = "DAY"
    }
    externalPositions = @(@{symbol=$ExternalSymbol.Trim().ToUpperInvariant(); quantity=$ExternalQuantity})
    estimatedNotional = $EstimatedNotional
}
if ($orderRequest.intent.symbol -notmatch '^[0-9A-Z]{4}\.T$' -or $Quantity % 100 -ne 0 -or
    [double]::IsNaN($EstimatedNotional) -or [double]::IsInfinity($EstimatedNotional) -or $EstimatedNotional -le 0) {
    throw "LOCKED_DIAGNOSTIC_ORDER_INPUT_INVALID"
}

function Set-ArkInspectionText {
    param($Worksheet, [string]$Address, [AllowEmptyString()][string]$Text)
    $cell = $Worksheet.Range($Address)
    $cell.NumberFormat = "@"
    $cell.Value2 = [string]$Text
}

$sheet = $null
$wb = $null
try {
    $excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    $matchingBooks = @($excel.Workbooks | Where-Object { $_.Name -eq $WorkbookName })
    if ($matchingBooks.Count -ne 1) { throw "OPEN_DEDICATED_WORKBOOK_REQUIRED" }
    $wb = $matchingBooks[0]
    $acct = $wb.Worksheets.Item($AccountSheet)
    foreach ($candidateSheet in $wb.Worksheets) {
        if ($candidateSheet.Name -eq $OrderSheet) { $sheet = $candidateSheet; break }
    }
    if ($null -eq $sheet) { $sheet = $wb.Worksheets.Add(); $sheet.Name = $OrderSheet }

    # Invalidate any old preview BEFORE acquiring data or starting Python.
    # Changing NumberFormat alone does not remove an existing formula.
    [void]$sheet.Range("B13").ClearContents()
    $sheet.Range("B13").NumberFormat = "@"
    $sheet.Range("B11").Value2 = 0
    Set-ArkInspectionText $sheet "B3" "LOCKED / NO TRANSMISSION"
    Set-ArkInspectionText $sheet "B18" "CHECK IN PROGRESS - LOCKED"
    foreach ($address in @("B15", "B16", "B17")) { Set-ArkInspectionText $sheet $address "FALSE" }

    # Read the running RSS outputs, without forcing recalculation of unrelated
    # workbook formulas. capturedAt is the oldest read, not a refreshed timestamp.
    $captureStartedAt = (Get-Date).ToString("o")
    $positions = @()
    for ($row = 3; $row -le 200; $row++) {
        $positionSymbol = $acct.Cells.Item($row,38).Text
        $positionName = $acct.Cells.Item($row,39).Text
        $positionAccount = $acct.Cells.Item($row,40).Text
        $positionQuantity = $acct.Cells.Item($row,41).Value2
        if ($positionName -and $positionName -ne "--------" -and $null -ne $positionQuantity) {
            $positions += [PSCustomObject]@{
                symbol=$positionSymbol; name=$positionName; account=$positionAccount; quantity=$positionQuantity
            }
        }
    }
    $orders = @()
    for ($row = 3; $row -le 300; $row++) {
        $orderNumber = $acct.Cells.Item($row,14).Text
        if ($orderNumber -and $orderNumber -ne "--------") {
            $orders += [PSCustomObject]@{
                orderNumber=$orderNumber; status=$acct.Cells.Item($row,15).Text
                symbol=$acct.Cells.Item($row,16).Text; quantity=$acct.Cells.Item($row,22).Value2
                filledQty=$acct.Cells.Item($row,23).Value2
            }
        }
    }
    $executions = @()
    for ($row = 3; $row -le 300; $row++) {
        $executionDate = $acct.Cells.Item($row,27).Text
        if ($executionDate -and $executionDate -ne "--------") {
            $executions += [PSCustomObject]@{
                executionDate=$executionDate; symbol=$acct.Cells.Item($row,28).Text
                account=$acct.Cells.Item($row,30).Text; side=$acct.Cells.Item($row,33).Text
                quantity=$acct.Cells.Item($row,34).Value2; price=$acct.Cells.Item($row,35).Value2
            }
        }
    }
    $buyingPower = $acct.Cells.Item(3,12).Value2
    if ($null -eq $buyingPower) { throw "BUYING_POWER_READ_MISSING" }
    $snapshot = [PSCustomObject]@{
        schemaId="ARK_ACCOUNT_READONLY_SNAPSHOT_V2"; capturedAt=$captureStartedAt
        captureCompletedAt=(Get-Date).ToString("o"); source="MARKETSPEED_II_RSS"; mode="READ_ONLY"
        positions=$positions; orders=$orders; executions=$executions; buyingPower=$buyingPower
        safety=@{executionAllowed=$false;brokerWriteAllowed=$false;excelOrderWriteAllowed=$false;
            rssOrderFunctionAllowed=$false;liveTradingAllowed=$false;paperTradingAllowed=$false;
            automaticPromotionAllowed=$false;productionUpdateAllowed=$false;transmitted=$false}
    }
    $directory = Split-Path -Parent $orderRequest.snapshotPath
    [void](New-Item -ItemType Directory -Force -Path $directory)
    $snapshot | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $orderRequest.snapshotPath -Encoding UTF8
    $pipeline = Invoke-ArkCashLockedPipeline -Request $orderRequest

    Set-ArkInspectionText $sheet "A1" "ARK CASH-ONLY LOCKED DIAGNOSTIC"
    $labels = @{A3="MODE";A4="PRODUCT";A5="MARGIN";A6="SHORT SELLING";A8="SYMBOL";
        A9="SIDE";A10="QUANTITY";A11="TRIGGER";A12="BUYING POWER";A13="RSS FUNCTION DRAFT";
        A15="EXECUTION ALLOWED";A16="TRANSMITTED";A17="EXCEL ORDER WRITE";A18="STATUS"}
    foreach ($address in $labels.Keys) { Set-ArkInspectionText $sheet $address $labels[$address] }
    Set-ArkInspectionText $sheet "B4" "CASH ONLY"
    Set-ArkInspectionText $sheet "B5" "DISABLED"
    Set-ArkInspectionText $sheet "B6" "DISABLED"
    Set-ArkInspectionText $sheet "B8" $orderRequest.intent.symbol
    Set-ArkInspectionText $sheet "B9" $orderRequest.intent.side
    Set-ArkInspectionText $sheet "B10" ([string]$orderRequest.intent.quantity)
    Set-ArkInspectionText $sheet "B12" ([string]$buyingPower)
    if ($pipeline.status -eq "LOCKED_READY") {
        if ($pipeline.interface.formulaEvaluationAllowed -ne $false -or
            $pipeline.interface.transmitted -ne $false) { throw "PIPELINE_INTERFACE_NOT_LOCKED" }
        Set-ArkInspectionText $sheet "B13" ([string]$pipeline.interface.cells.B13)
        Set-ArkInspectionText $sheet "B18" "LOCKED PREVIEW ONLY - NOT LIVE READY"
    }
    else {
        $blockers = @()
        foreach ($component in @($pipeline.candidate, $pipeline.reconciliation, $pipeline.preflight)) {
            if ($null -ne $component -and $component.blockers) { $blockers += $component.blockers }
        }
        if ($blockers.Count -eq 0) { throw "PIPELINE_BLOCK_REASON_MISSING" }
        Set-ArkInspectionText $sheet "B18" ("BLOCKED @ {0}: {1}" -f $pipeline.stage, ($blockers -join ","))
    }
    if ($sheet.Range("B13").HasFormula -ne $false -or $sheet.Range("B11").Value2 -ne 0) {
        throw "LOCKED_TEXT_INTERFACE_VERIFICATION_FAILED"
    }
    [void]$sheet.Columns("A:B").AutoFit()
    [void]$wb.Save()
    Write-Host "ARK_CASH_LOCKED_CHECK_COMPLETE"
    Write-Host "Snapshot    :" $orderRequest.snapshotPath
    Write-Host "OrderSymbol :" $orderRequest.intent.symbol
    Write-Host "Quantity    :" $orderRequest.intent.quantity
    Write-Host "Positions   :" $positions.Count
    Write-Host "Orders      :" $orders.Count
    Write-Host "Executions  :" $executions.Count
    Write-Host "BuyingPower :" $buyingPower
    Write-Host "Pipeline    :" $pipeline.status
    Write-Host "Stage       :" $pipeline.stage
    Write-Host "Trigger     :" $sheet.Range("B11").Value2
    Write-Host "Formula?    :" $sheet.Range("B13").HasFormula
    Write-Host "Execution   :" $sheet.Range("B15").Text
    Write-Host "Transmitted :" $sheet.Range("B16").Text
    Write-Host "Status      :" $sheet.Range("B18").Text
}
catch {
    $failure = $_
    if ($null -ne $sheet) {
        try {
            [void]$sheet.Range("B13").ClearContents()
            $sheet.Range("B11").Value2 = 0
            Set-ArkInspectionText $sheet "B18" "ERROR - LOCKED; SEE POWERSHELL"
            [void]$wb.Save()
        }
        catch { Write-Warning "Could not refresh the locked error display." }
    }
    throw $failure
}
