param(
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$WorkbookPath = "C:\Ark\Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [string]$UiReadModelPath = "C:\Ark\ui-readonly\ark-terminal-ui-read-model.json",
    [string]$OwnershipBaselinePath = "",
    [switch]$SkipSnapshotRefresh,
    [switch]$DoNotAutoOpenWorkbook
)

$ErrorActionPreference = "Stop"
$snapshotLauncher = Join-Path $PSScriptRoot "Start-ArkAccountReadOnlySnapshot.ps1"
$exporter = Join-Path $PSScriptRoot "phase57_ui_read_model_cli.mjs"
if (-not (Test-Path -LiteralPath $snapshotLauncher -PathType Leaf)) { throw "ACCOUNT_READ_ONLY_SNAPSHOT_LAUNCHER_MISSING" }
if (-not (Test-Path -LiteralPath $exporter -PathType Leaf)) { throw "UI_READ_MODEL_EXPORTER_MISSING" }

$resolvedSnapshot = [IO.Path]::GetFullPath($SnapshotPath)
if (-not $SkipSnapshotRefresh) {
    $snapshotArgs = @{
        WorkbookName = $WorkbookName
        WorkbookPath = $WorkbookPath
        AccountSheet = $AccountSheet
        SnapshotPath = $resolvedSnapshot
        # Do not programmatically RegisterXLL from the UI path. The MarketSpeed
        # XLL is a third-party Excel add-in and has been observed to terminate
        # the Excel COM server on this machine (RPC 0x800706BE). The add-in must
        # be registered through Excel once; after that this path is read-only.
        DoNotAutoLoadRssAddin = $true
    }
    if ($DoNotAutoOpenWorkbook) { $snapshotArgs.DoNotAutoOpenWorkbook = $true }
    & $snapshotLauncher @snapshotArgs
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
