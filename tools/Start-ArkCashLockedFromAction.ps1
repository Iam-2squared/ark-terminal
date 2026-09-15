param(
    [Parameter(Mandatory=$true)][string]$ActionPath,
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json",
    [string]$ExternalSymbol = "408A",
    [double]$ExternalQuantity = 180
)
$ErrorActionPreference = "Stop"
$resolved = (Resolve-Path -LiteralPath $ActionPath -ErrorAction Stop).Path
$validator = Join-Path $PSScriptRoot "phase57_cash_upstream_action.mjs"
if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) { throw "CASH_UPSTREAM_ACTION_VALIDATOR_MISSING" }
$node = Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ("ark-cash-action-" + [Guid]::NewGuid().ToString("N"))
[void](New-Item -ItemType Directory -Path $tempDir -ErrorAction Stop)
$validatedPath = Join-Path $tempDir "validated.json"
try {
    & $node.Source $validator --mode validate --input $resolved --output $validatedPath | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $validatedPath -PathType Leaf)) {
        throw "CASH_UPSTREAM_ACTION_VALIDATION_FAILED"
    }
    $action = [IO.File]::ReadAllText($validatedPath, [Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
    if ($action.schemaId -ne "ARK_CASH_UPSTREAM_ACTION_V1" -or $action.direction -ne "LONG" -or
        $action.cashOnly -ne $true -or $action.marginAllowed -ne $false -or $action.shortSellingAllowed -ne $false -or
        $action.executable -ne $false -or $action.transmitted -ne $false) {
        throw "CASH_UPSTREAM_ACTION_LOCK_CONTRACT_FAILED"
    }
    if ($action.orderType -ne "MARKET" -or $null -ne $action.limitPrice -or $action.timeInForce -ne "DAY") {
        throw "LOCKED_LAUNCHER_CURRENTLY_REQUIRES_MARKET_DAY_ACTION"
    }
    & (Join-Path $PSScriptRoot "Start-ArkCashLocked.ps1") `
        -WorkbookName $WorkbookName `
        -AccountSheet $AccountSheet `
        -OrderSheet $OrderSheet `
        -SnapshotPath $SnapshotPath `
        -Symbol ([string]$action.symbol) `
        -Side ([string]$action.side) `
        -PositionEffect ([string]$action.positionEffect) `
        -Quantity ([int]$action.quantity) `
        -EstimatedNotional ([double]$action.estimatedNotional) `
        -ExternalSymbol $ExternalSymbol `
        -ExternalQuantity $ExternalQuantity
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "LOCKED_ACTION_LAUNCHER_FAILED:$LASTEXITCODE" }
}
finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
