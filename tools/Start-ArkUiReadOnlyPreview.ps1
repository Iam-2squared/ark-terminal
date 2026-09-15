param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [string]$UiReadModelPath = "C:\Ark\ui-readonly\ark-terminal-ui-read-model.json",
    [string]$OwnershipBaselinePath = "",
    [switch]$SkipSnapshotRefresh
)

$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "Start-ArkCashLocked.ps1"
$exporter = Join-Path $PSScriptRoot "phase57_ui_read_model_cli.mjs"
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "CASH_LOCKED_LAUNCHER_MISSING" }
if (-not (Test-Path -LiteralPath $exporter -PathType Leaf)) { throw "UI_READ_MODEL_EXPORTER_MISSING" }

function Assert-ArkDedicatedWorkbookOpen {
    param(
        [Parameter(Mandatory=$true)][string]$ExpectedWorkbookName,
        [Parameter(Mandatory=$true)][string]$ExpectedAccountSheet
    )

    try {
        $excel = [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    }
    catch {
        throw "EXCEL_APPLICATION_NOT_RUNNING"
    }

    $openNames = @($excel.Workbooks | ForEach-Object { [string]$_.Name })
    $matchingBooks = @($excel.Workbooks | Where-Object { $_.Name -eq $ExpectedWorkbookName })

    if ($matchingBooks.Count -ne 1) {
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
}

$resolvedSnapshot = [IO.Path]::GetFullPath($SnapshotPath)
if (-not $SkipSnapshotRefresh) {
    Assert-ArkDedicatedWorkbookOpen -ExpectedWorkbookName $WorkbookName -ExpectedAccountSheet $AccountSheet
    & $launcher `
        -WorkbookName $WorkbookName `
        -AccountSheet $AccountSheet `
        -OrderSheet $OrderSheet `
        -SnapshotPath $resolvedSnapshot
}
if (-not (Test-Path -LiteralPath $resolvedSnapshot -PathType Leaf)) { throw "ACCOUNT_SNAPSHOT_MISSING" }

$node = Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1
$target = [IO.Path]::GetFullPath($UiReadModelPath)
$targetDirectory = Split-Path -Parent $target
[void](New-Item -ItemType Directory -Force -Path $targetDirectory)

$tempDirectory = Join-Path ([IO.Path]::GetTempPath()) ("ark-ui-readonly-" + [Guid]::NewGuid().ToString("N"))
[void](New-Item -ItemType Directory -Path $tempDirectory -ErrorAction Stop)
$tempOutput = Join-Path $tempDirectory "ui-read-model.json"
try {
    $nativeArgs = @($exporter, "--snapshot", $resolvedSnapshot, "--output", $tempOutput)
    if (-not [string]::IsNullOrWhiteSpace($OwnershipBaselinePath)) {
        $resolvedOwnership = (Resolve-Path -LiteralPath $OwnershipBaselinePath -ErrorAction Stop).Path
        $nativeArgs += @("--ownership", $resolvedOwnership)
    }
    & $node.Source @nativeArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tempOutput -PathType Leaf)) {
        throw "UI_READ_MODEL_EXPORT_FAILED"
    }

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $model = [IO.File]::ReadAllText($tempOutput, $utf8) | ConvertFrom-Json -ErrorAction Stop
    if ($model.schemaId -ne "ARK_TERMINAL_UI_READ_MODEL_V1" -or $model.readOnly -ne $true) {
        throw "UI_READ_MODEL_INVALID"
    }
    foreach ($name in @("orderSubmit","orderCancel","killSwitchChange","strategyEdit","brokerWrite","excelOrderWrite","rssOrderFunction")) {
        if ($model.mutationCapabilities.$name -ne $false) { throw "UI_READ_MODEL_MUTATION_CAPABILITY_NOT_FALSE:$name" }
    }

    [IO.File]::WriteAllText($target, [IO.File]::ReadAllText($tempOutput, $utf8), $utf8)
    Write-Host "ARK_UI_READ_ONLY_PREVIEW_READY"
    Write-Host "Workbook      :" $WorkbookName
    Write-Host "ReadModel     :" $target
    Write-Host "SourceState   :" $model.source.freshness.state
    Write-Host "BuyingPower   :" $model.home.buyingPower
    Write-Host "Positions     :" $model.positions.Count
    Write-Host "Orders        :" $model.orders.Count
    Write-Host "Executions    :" $model.executions.Count
    Write-Host "Ownership     :" $model.system.ownership.state
    Write-Host "RuntimeSafety :" $model.system.runtimeSafety.state
    Write-Host "TradeReadiness:" $model.system.tradeReadiness
    Write-Host "Mutations     : FALSE"
}
finally {
    Remove-Item -LiteralPath $tempDirectory -Recurse -Force -ErrorAction SilentlyContinue
}
