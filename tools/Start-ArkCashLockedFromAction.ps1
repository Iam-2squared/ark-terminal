param(
    [Parameter(Mandatory=$true)][string]$ActionPath,
    [Parameter(Mandatory=$true)][string]$OwnershipBaselinePath,
    [string]$WorkbookName = "Ark_MSII_LiveSource.xlsx",
    [string]$AccountSheet = "ARK_ACCOUNT_READONLY",
    [string]$OrderSheet = "ARK_CASH_ORDER_LOCKED",
    [string]$SnapshotPath = "C:\Ark\account-readonly-20260915\account-snapshot-live.json"
)
$ErrorActionPreference = "Stop"
$action = (Resolve-Path -LiteralPath $ActionPath -ErrorAction Stop).Path
$ownership = (Resolve-Path -LiteralPath $OwnershipBaselinePath -ErrorAction Stop).Path
$builder = Join-Path $PSScriptRoot "phase57_cash_upstream_request.mjs"
if (-not (Test-Path -LiteralPath $builder -PathType Leaf)) { throw "CASH_UPSTREAM_REQUEST_BUILDER_MISSING" }
$node = Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ("ark-cash-upstream-" + [Guid]::NewGuid().ToString("N"))
[void](New-Item -ItemType Directory -Path $tempDir -ErrorAction Stop)
$requestPath = Join-Path $tempDir "locked-request.json"
try {
    & $node.Source $builder --action $action --ownership $ownership --snapshot ([IO.Path]::GetFullPath($SnapshotPath)) --output $requestPath | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $requestPath -PathType Leaf)) {
        throw "CASH_UPSTREAM_REQUEST_BUILD_FAILED"
    }
    & (Join-Path $PSScriptRoot "Start-ArkCashLocked.ps1") `
        -WorkbookName $WorkbookName `
        -AccountSheet $AccountSheet `
        -OrderSheet $OrderSheet `
        -LockedRequestPath $requestPath
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "LOCKED_ACTION_LAUNCHER_FAILED:$LASTEXITCODE" }
}
finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
